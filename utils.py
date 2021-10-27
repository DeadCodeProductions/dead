import argparse
import grp
import io
import json
import logging
import os
import shutil
import stat
import subprocess
import sys

import parsers

from dataclasses import dataclass
from functools import reduce
from os.path import join as pjoin
from pathlib import Path
from types import SimpleNamespace
from typing import Hashable, Optional, Tuple, Union

import parsers


class Executable(object):
    pass


# fmt: off
EXPECTED_ENTRIES = [
    # Type      Path in config              Description
    (str,       ("gcc", "name"),            "Prefix for the gcc cache directory"),
    (str,       ("gcc", "main_branch"),     "Name of main/trunk/master branch"),
    (Path,      ("gcc", "repo"),            "Path to gcc repository"),
    (list,      ("gcc", "patches"),         "List of names of patches for gcc that can be found in ./patches" ),
    (Executable,("gcc", "sane_version",),   "Path to executable or name in PATH for a sane gcc" ),
    (list,      ("gcc", "releases",),       "GCC releases of interest"),

    (str,       ("llvm", "name"),           "Prefix for the llvm cache directory"),
    (str,       ("llvm", "main_branch"),    "Name of main/trunk/master branch"),
    (Path,      ("llvm", "repo"),           "Path to llvm-project repository"),
    (list,      ("llvm", "patches"),        "List of names of patches for gcc that can be found in ./patches" ),
    (Executable,("llvm", "sane_version",),  "Path to executable or name in PATH for a sane clang" ),
    (list,      ("llvm", "releases",),      "LLVM releases of interest"),

    (Path,      ("cachedir", ),             "Path where the cache should be"),
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
]
# fmt: on


class NestedNamespace(SimpleNamespace):
    # https://stackoverflow.com/a/54332748
    # Class to make a dict into something that dot-notation
    # can be used on.
    def __init__(self, dictionary, **kwargs):
        super().__init__(**kwargs)
        for key, value in dictionary.items():
            if isinstance(value, dict):
                self.__setattr__(key, NestedNamespace(value))
            else:
                self.__setattr__(key, value)

    def __getitem__(self, key: Union[Hashable, list[Hashable], Tuple[Hashable]]):
        if isinstance(key, tuple) or isinstance(key, list):
            if len(key) > 1:
                tmp = reduce(lambda x, y: x[y].__dict__, key[:-1], self.__dict__)
                tmp = tmp[key[-1]]
                return tmp
            else:
                return self.__dict__[key[0]]
        else:
            return self.__dict__[key]

    def __setitem__(self, key: Union[Hashable, list[Hashable], Tuple[Hashable]], value):
        if isinstance(key, tuple) or isinstance(key, list):
            if len(key) > 1:
                tmp = reduce(lambda x, y: x[y].__dict__, key[:-1], self.__dict__)
                tmp[key[-1]] = value
            else:
                self.__dict__[key[0]] = value

        else:
            self.__dict__[key] = value

    def __contains__(self, key: Union[Hashable, list[Hashable], Tuple[Hashable]]):
        if isinstance(key, tuple) or isinstance(key, list):
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
        else:
            return key in self.__dict__


def validate_config(config: dict):
    # TODO: Also check if there are fields that are not supposed to be there
    missing_keys = False
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
                missing_keys = True
                s = ".".join(pos)
                key_problems.add(f"Missing entry for '{s}' in config")
            else:
                tmpconfig = tmpconfig[key]
        if exists:
            # At this point, tmpconfig should be the value in the config
            s = ".".join(pos)
            if key_type is str:
                if tmpconfig == "":
                    key_problems.add(f"{s} should be a non-empty string, but is empty.")
                    missing_keys = True
            elif key_type is Path:
                if tmpconfig == "":
                    key_problems.add(f"{s} should be a non-empty Path, but is empty.")
                    missing_keys = True
                elif not Path(tmpconfig).exists():
                    key_problems.add(f"Path {tmpconfig} at {s} doesn't exist.")
                    missing_keys = True
            elif key_type is Executable:
                if shutil.which(tmpconfig) is None:
                    key_problems.add(
                        f"Executable {tmpconfig} in {s} doesn't exist or is not executable."
                    )
                    missing_keys = True
            elif key_type is list:
                if type(tmpconfig) is not list:
                    key_problems.add(
                        f"{s} should be a list but is not. It contains {tmpconfig} instead."
                    )
                    missing_keys = True

                if exkeys[1][-1] == "patches":
                    for patch in tmpconfig:
                        if not Path(pjoin("patches", patch)).exists():
                            key_problems.add(f"Patch at {patch} in {s} doesn't exist")
                            missing_keys = True

    if key_problems:
        print("The config has problems:")
        for problem in sorted(list(key_problems)):
            print(" - " + problem)
        exit(1)


def import_config(
    config_path: Optional[Union[os.PathLike[str], Path]] = None, validate: bool = True
):
    if config_path is None:
        p = pjoin(Path.home(), ".config/dce/config.json")
        if Path(p).exists():
            config_path = p
        elif Path("./config.json").exists():
            config_path = "./config.json"
        else:
            raise Exception("Found no config.json file at {p} or ./config.json!")
        logging.debug(f"Using config found at {config_path}")

    with open(config_path, "r") as f:
        config = json.load(f)

    if validate:
        validate_config(config)

    config = NestedNamespace(config)
    # Make sure the cache dir exists
    cache_path = Path(config.cachedir)
    if not cache_path.exists():
        os.makedirs(config.cachedir, exist_ok=True)
        shutil.chown(config.cachedir, group=config.cache_group)
        os.chmod(config.cachedir, 0o770 | stat.S_ISGID)
    elif cache_path.is_dir() or cache_path.is_symlink():
        followed_links = []
        while cache_path.is_symlink():
            cache_path = Path(os.readlink(cache_path))
            if cache_path in followed_links:
                raise Exception(
                    f"Symlink-cycle found for {config.cachedir}. (If you actually encountered this error, drop me an email)"
                )
            if cache_path.group() != config.cache_group:
                raise Exception(
                    f"Link {cache_path} in the symlink-chain to the cache directory is not owned by {config.cache_group}"
                )

        if cache_path.group() != config.cache_group:
            raise Exception(
                f"Cache {config.cachdir} is not owned by {config.cache_group}"
            )

        if cache_path.stat().st_mode != 17912:
            raise Exception(
                f"Cache {config.cachdir} seems to have the wrong permissions. Please run `chmod g+rwxs {config.cachedir}`."
            )

    else:
        raise Exception(
            f"config.cachedir {config.cachedir} already exists but is not a path or a symlink"
        )

    # Make patch paths full paths to avoid confusion
    # when working in different directories
    config.gcc.patches = [
        pjoin(os.getcwd(), "patches", patch) for patch in config.gcc.patches
    ]
    config.llvm.patches = [
        pjoin(os.getcwd(), "patches", patch) for patch in config.llvm.patches
    ]

    return config


def get_config_and_parser(own_parser: Optional[argparse.ArgumentParser] = None):
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

    for _, path, _ in EXPECTED_ENTRIES:
        arg_val = args_parser.__dict__[".".join(path)]
        if arg_val is not None:
            config[path] = arg_val

    validate_config(config)

    return config, args_parser


def create_symlink(src: os.PathLike, dst: os.PathLike):
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

@dataclass
class CompilerSetting():
    compiler_config: NestedNamespace
    rev: str
    opt_level: Optional[str] = None
    additional_flags: Optional[list[str]] = None

    def __str__(self):
        if self.additional_flags is None:
            return f"{self.compiler_config.name} {self.rev} {self.opt_level}"
        else:
            return f"{self.compiler_config.name} {self.rev} {self.opt_level} " + " ".join(self.additional_flags)

    @staticmethod
    def from_str(s: str, config: NestedNamespace):
        s = s.strip()
        parts = s.split(" ")

        compiler = parts[0]
        rev = parts[1]
        opt_level = parts[2]
        additional_flags = parts[2:]
        if compiler == "gcc":
            compiler_config = config.gcc
        elif compiler == "llvm" or compiler == "clang":
            compiler_config = config.llvm
        else:
            raise Exception(f"Unknown compiler project {compiler}")

        return CompilerSetting(compiler_config, rev, opt_level, additional_flags)


def run_cmd(
    cmd: Union[str, list[str]],
    working_dir: Optional[os.PathLike] = None,
    additional_env: dict = {},
    log: bool = True,
    log_file: Optional[io.TextIOWrapper] = None,
) -> Optional[str]:

    if working_dir is None:
        working_dir = os.getcwd()
    env = os.environ.copy()
    env.update(additional_env)

    if isinstance(cmd, str):
        cmd = cmd.strip().split(" ")
    if log:
        output = subprocess.run(
            cmd, cwd=working_dir, check=True, env=env, capture_output=True
        )

        logging.debug(output.stdout.decode("utf-8").strip())
        logging.debug(output.stderr.decode("utf-8").strip())
        return output.stdout.decode("utf-8").strip()
    else:
        if log_file is not None:
            output = subprocess.run(
                cmd,
                cwd=working_dir,
                check=True,
                stdout=log_file,
                stderr=subprocess.STDOUT,
                env=env,
                capture_output=False,
            )
        else:
            output = subprocess.run(
                cmd, cwd=working_dir, check=True, env=env, capture_output=False
            )
