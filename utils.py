from __future__ import annotations

import argparse
import copy
import functools
import json
import logging
import os
import re
import shutil
import stat
import subprocess
import tarfile
import tempfile
import time
from dataclasses import dataclass
from functools import reduce
from os.path import join as pjoin
from pathlib import Path
from types import SimpleNamespace, TracebackType
from typing import IO, Any, Optional, Sequence, TextIO, Union, cast

import ccbuilder
from ccbuilder import (
    Builder,
    BuildException,
    CompilerProject,
    Repo,
    get_compiler_project,
)

import parsers
import VERSIONS

from dead.utils import Scenario


class Executable(object):
    pass


# fmt: off
# When adding new options, don't forget to also put them in the init script!
EXPECTED_ENTRIES = [
    # Type      Path in config              Description
    (str,       ("gcc", "name"),            "Prefix for the gcc cache directory"),
    (str,       ("gcc", "main_branch"),     "Name of main/trunk/master branch"),
    (Path,      ("gcc", "repo"),            "Path to gcc repository"),
    (Executable,("gcc", "sane_version",),   "Path to executable or name in PATH for a sane gcc" ),
    (list,      ("gcc", "releases",),       "GCC releases of interest"),

    (str,       ("llvm", "name"),           "Prefix for the llvm cache directory"),
    (str,       ("llvm", "main_branch"),    "Name of main/trunk/master branch"),
    (Path,      ("llvm", "repo"),           "Path to llvm-project repository"),
    (Executable,("llvm", "sane_version",),  "Path to executable or name in PATH for a sane clang" ),
    (list,      ("llvm", "releases",),      "LLVM releases of interest"),

    (Path,      ("cachedir", ),             "Path where the cache should be"),
    (Path,      ("repodir", ),              "Path where the repos should be"),
    (Executable,("csmith", "executable"),   "Path to executable or name in PATH for csmith"),
    (Path,      ("csmith", "include_path"), "Path to include directory of csmith"),
    (int,       ("csmith", "max_size"),     "Maximum size of csmith-generated candidate"),
    (int,       ("csmith", "min_size"),     "Minimum size of csmith-generated candidate"),
    (Executable,("dcei",),                  "Path to executable or name in PATH for dcei" ),
    (Executable,("creduce", ),              "Path to executable or name in PATH for creduce" ),
    (Executable,("ccomp", ),                "Path to executable or name in PATH for ccomp" ),
    (Path,      ("patchdb", ),              "Path where the patchDB file is"),
    (Path,      ("logdir", ),               "Where build log files should be saved to"),
    (str,       ("cache_group", ),          "Name of group owning the cache"),
    (Executable,("ccc",),                   "Path to executable or name in PATH for the callchain checker"),
    (Path,      ("casedb", ),               "Path to the database holding the cases."),
]
# fmt: on


class NestedNamespace(SimpleNamespace):
    # https://stackoverflow.com/a/54332748
    # Class to make a dict into something that dot-notation
    # can be used on.
    def __init__(self, dictionary: dict[str, Any], **kwargs: Any):
        super().__init__(**kwargs)
        for key, value in dictionary.items():
            if isinstance(value, dict):
                self.__setattr__(key, NestedNamespace(value))
            else:
                self.__setattr__(key, value)

    def __getitem__(self, key: Union[str, Sequence[str]]) -> Any:
        if isinstance(key, str):
            return self.__dict__[key]
        assert isinstance(key, Sequence)
        if len(key) > 1:
            tmp = reduce(lambda x, y: x[y].__dict__, key[:-1], cast(Any, self.__dict__))
            return tmp[key[-1]]
        else:
            return self.__dict__[key[0]]

    def __setitem__(self, key: Union[str, Sequence[str]], value: Any) -> None:
        if isinstance(key, str):
            self.__dict__[key] = value
        assert isinstance(key, Sequence)
        if len(key) > 1:
            tmp = reduce(lambda x, y: x[y].__dict__, key[:-1], cast(Any, self.__dict__))
            tmp[key[-1]] = value
        else:
            self.__dict__[key[0]] = value

    def __contains__(self, key: Union[str, Sequence[str]]) -> bool:
        if isinstance(key, str):
            return key in self.__dict__
        assert isinstance(key, Sequence)
        if len(key) > 1:
            tmp = self.__dict__
            for k in key[:-1]:
                if k not in tmp:
                    return False
                else:
                    tmp = tmp[k].__dict__

            return key[-1] in tmp
        else:
            return key[0] in self.__dict__

    def __asdict(self) -> dict[Any, Any]:
        d = {}
        for key, value in self.__dict__.items():
            if isinstance(value, NestedNamespace):
                dvalue = value.__asdict()
            else:
                dvalue = copy.deepcopy(value)
            d[key] = dvalue
        return d

    def __deepcopy__(self, memo: dict[Any, Any]) -> NestedNamespace:
        return type(self)(self.__asdict())


def validate_config(config: Union[dict[str, Any], NestedNamespace]) -> None:
    """Given a config, check if the fields are of the correct type.
    Exit if it is not the case.

    Args:
        config (Union[dict[str, Any], NestedNamespace]): config

    Returns:
        None:
    """
    key_problems = set()

    for exkeys in EXPECTED_ENTRIES:
        pos = []
        key_type = exkeys[0]
        tmpconfig = config
        exists = True
        for key in exkeys[1]:
            pos.append(key)
            if key not in tmpconfig:
                exists = False
                s = ".".join(pos)
                key_problems.add(f"Missing entry for '{s}' in config")
            else:
                tmpconfig = tmpconfig[key]
        if exists:
            # At this point, tmpconfig should be the value in the config
            s = ".".join(pos)
            if key_type is str:
                if tmpconfig == "":  # type: ignore
                    key_problems.add(f"{s} should be a non-empty string, but is empty.")
            elif key_type is Path:
                if not isinstance(tmpconfig, str) or tmpconfig == "":
                    key_problems.add(f"{s} should be a non-empty Path, but is empty.")
                elif not Path(tmpconfig).exists():
                    key_problems.add(f"Path {tmpconfig} at {s} doesn't exist.")
            elif key_type is Executable:
                if shutil.which(tmpconfig) is None:  # type: ignore
                    key_problems.add(
                        f"Executable {tmpconfig} in {s} doesn't exist or is not executable."
                    )
            elif key_type is list:
                if type(tmpconfig) is not list:  # type: ignore
                    key_problems.add(
                        f"{s} should be a list but is not. It contains {tmpconfig} instead."
                    )

                if exkeys[1][-1] == "patches":
                    for patch in tmpconfig:  # type: ignore
                        if not Path(pjoin("patches", patch)).exists():
                            key_problems.add(f"Patch at {patch} in {s} doesn't exist")

    if key_problems:
        print("The config has problems:")
        for problem in sorted(list(key_problems)):
            print(" - " + problem)
        exit(1)


def to_absolute_paths(config: NestedNamespace) -> None:
    """
    Convert relative paths for `Path`, `Executable` and `patches` found in config
    into absolute paths with prefix dirname __file__.
    """
    project_dir = Path(__file__).parent
    for typ, path_in_config, _ in EXPECTED_ENTRIES:
        if typ is Path and not Path(config[path_in_config]).is_absolute():
            config[path_in_config] = str(project_dir / config[path_in_config])
        elif typ is list and "patches" in path_in_config:
            patches = [str(project_dir / patch) for patch in config[path_in_config]]
            config[path_in_config] = patches
        elif typ is Executable:
            exe = config[path_in_config]
            if "/" in exe and not Path(exe).is_absolute():
                config[path_in_config] = str(project_dir / config[path_in_config])


def import_config(
    config_path: Optional[Path] = None, validate: bool = True
) -> NestedNamespace:
    """Read and potentially verify the specified config.

    Args:
        config_path (Optional[Path]): Path to config. Defaults to ~/.config/dead/config.json.
        validate (bool): Whether or not to validate the config.

    Returns:
        NestedNamespace: The config
    """
    if config_path is None:

        p = Path.home() / ".config/dead/config.json"
        if p.exists():
            config_path = p
        else:
            raise Exception("Found no config.json file at {p}!")
        logging.debug(f"Using config found at {config_path}")
    else:
        if not Path(config_path).is_file():
            raise Exception("Found no config.json file at {p}!")

    with open(config_path, "r") as f:
        config_dict = json.load(f)

    config_dict["config_path"] = str(Path(config_path).absolute())

    config = NestedNamespace(config_dict)
    to_absolute_paths(config)

    if validate:
        validate_config(config)

    # Make sure the cache dir exists
    cache_path = Path(config.cachedir)
    if not cache_path.exists():
        os.makedirs(config.cachedir, exist_ok=True)
        shutil.chown(config.cachedir, group=config.cache_group)
        os.chmod(config.cachedir, 0o770 | stat.S_ISGID)
    elif cache_path.is_dir() or cache_path.is_symlink():
        while cache_path.is_symlink():
            cache_path = Path(os.readlink(cache_path))
            if cache_path.group() != config.cache_group:
                raise Exception(
                    f"Link {cache_path} in the symlink-chain to the cache directory is not owned by {config.cache_group}"
                )

        if cache_path.group() != config.cache_group:
            raise Exception(
                f"Cache {config.cachedir} is not owned by {config.cache_group}"
            )

        if cache_path.stat().st_mode != 17912:
            raise Exception(
                f"Cache {config.cachedir} seems to have the wrong permissions. Please run `chmod g+rwxs {config.cachedir}`."
            )

    else:
        raise Exception(
            f"config.cachedir {config.cachedir} already exists but is not a path or a symlink"
        )

    return config


def get_config_and_parser(
    own_parser: Optional[argparse.ArgumentParser] = None,
) -> tuple[NestedNamespace, argparse.Namespace]:
    """Get the config object and its parser.
    You can specify other parsers which will be incorporated into the config parser.
    Will also parse the CLI.

    Args:
        own_parser (Optional[argparse.ArgumentParser]): Parsers to be incorporated into the config parser.

    Returns:
        tuple[NestedNamespace, argparse.Namespace]: The config and the parsed arguments.
    """
    if own_parser is not None:

        parser_list = [own_parser, parsers.config_parser(EXPECTED_ENTRIES)]
    else:
        parser_list = [parsers.config_parser(EXPECTED_ENTRIES)]

    parser = argparse.ArgumentParser(parents=parser_list)
    args_parser = parser.parse_args()

    # Log level
    if args_parser.log_level is not None:
        try:
            num_lvl = getattr(logging, args_parser.log_level.upper())
            logging.basicConfig(level=num_lvl)
        except AttributeError:
            print(f"No such log level {args_parser.log_level.upper()}")
            exit(1)

    # Get config file
    config = import_config(args_parser.config, validate=False)

    # Read values from CLI and override them in config
    for _, path, _ in EXPECTED_ENTRIES:
        arg_val = args_parser.__dict__[".".join(path)]
        if arg_val is not None:
            config[path] = arg_val

    validate_config(config)

    return config, args_parser


def create_symlink(src: Path, dst: Path) -> None:
    if dst.exists():
        if dst.is_symlink():
            dst.unlink()
        else:
            dst_symlink_config = Path(
                os.path.dirname(dst), "conflict_" + str(os.path.basename(dst))
            )

            logging.warning(
                f"Found non-symlink file or directory which should be a symlink: {dst}. Moving to {dst_symlink_config}..."
            )
            shutil.move(dst, dst_symlink_config)

    logging.debug(f"Creating symlink {dst} to {src}")
    os.symlink(src, dst)


def get_marker_prefix(marker: str) -> str:
    # Markers are of the form [a-Z]+[0-9]+_
    return marker.rstrip("_").rstrip("0123456789")


def save_to_tmp_file(content: str) -> IO[bytes]:
    ntf = tempfile.NamedTemporaryFile()
    with open(ntf.name, "w") as f:
        f.write(content)

    return ntf


def save_to_file(path: Path, content: str) -> None:
    with open(path, "w") as f:
        f.write(content)


def check_and_get(tf: tarfile.TarFile, member: str) -> str:
    try:
        f = tf.extractfile(member)
    except KeyError:
        raise FileExistsError(f"File does not include member {member}!")
    if not f:
        raise FileExistsError(f"File does not include member {member}!")
    res = f.read().decode("utf-8").strip()

    return res
