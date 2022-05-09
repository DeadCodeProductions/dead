from __future__ import annotations

import re
import argparse
import copy
import functools
import json
import logging
import os
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
from types import SimpleNamespace
from typing import IO, Any, Optional, Sequence, TextIO, Union, cast
from types import TracebackType

from ccbuildercached import Repo, BuilderWithCache, BuildException, CompilerConfig, get_compiler_config

import parsers
import VERSIONS



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


@dataclass
class CompilerSetting:
    compiler_config: CompilerConfig
    rev: str
    opt_level: str
    additional_flags: Optional[list[str]] = None

    def __str__(self) -> str:
        if self.additional_flags is None:
            return f"{self.compiler_config.name} {self.rev} {self.opt_level}"
        else:
            return (
                f"{self.compiler_config.name} {self.rev} {self.opt_level} "
                + " ".join(self.additional_flags)
            )

    def report_string(self) -> str:
        """String to use in the report generation

        Args:

        Returns:
            str: String to use in the report
        """

        return f"{self.compiler_config.name}-{self.rev} -O{self.opt_level}"

    def to_jsonable_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {}
        d["compiler_config"] = self.compiler_config.name
        d["rev"] = self.rev
        d["opt_level"] = self.opt_level
        d["additional_flags"] = (
            self.additional_flags if self.additional_flags is not None else []
        )

        return d

    @staticmethod
    def from_jsonable_dict(
        config: NestedNamespace, d: dict[str, Any]
    ) -> CompilerSetting:
        return CompilerSetting(
            get_compiler_config(d["compiler_config"], config.repodir),
            d["rev"],
            d["opt_level"],
            d["additional_flags"],
        )

    def add_flag(self, flag: str) -> None:
        if not self.additional_flags:
            self.additional_flags = [flag]
        elif flag not in self.additional_flags:
            self.additional_flags.append(flag)

    def get_flag_str(self) -> str:
        if self.additional_flags:
            return " ".join(self.additional_flags)
        else:
            return ""

    def get_flag_cmd(self) -> list[str]:
        s = self.get_flag_str()
        if s == "":
            return []
        else:
            return s.split(" ")

    @staticmethod
    def from_str(s: str, config: NestedNamespace) -> CompilerSetting:
        s = s.strip()
        parts = s.split(" ")

        compiler = parts[0]
        rev = parts[1]
        opt_level = parts[2]
        additional_flags = parts[3:]
        if compiler == "gcc":
            compiler_config = config.gcc
        elif compiler == "llvm" or compiler == "clang":
            compiler_config = config.llvm
        else:
            raise Exception(f"Unknown compiler project {compiler}")

        return CompilerSetting(compiler_config, rev, opt_level, additional_flags)


class Scenario:
    def __init__(
        self,
        target_settings: list[CompilerSetting],
        attacker_settings: list[CompilerSetting],
    ):
        self.target_settings = target_settings
        self.attacker_settings = attacker_settings

        self.instrumenter_version = VERSIONS.instrumenter_version
        self.generator_version = VERSIONS.generator_version
        self.bisector_version = VERSIONS.bisector_version
        self.reducer_version = VERSIONS.reducer_version

    def add_flags(self, new_flags: list[str]) -> None:
        for f in new_flags:
            for s in self.target_settings:
                s.add_flag(f)
            for s in self.attacker_settings:
                s.add_flag(f)

    def to_jsonable_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {}
        d["target_settings"] = [s.to_jsonable_dict() for s in self.target_settings]
        d["attacker_settings"] = [s.to_jsonable_dict() for s in self.attacker_settings]

        d["instrumenter_version"] = self.instrumenter_version
        d["generator_versio"] = self.generator_version
        d["bisector_version"] = self.bisector_version
        d["reducer_version"] = self.reducer_version
        return d

    @staticmethod
    def from_jsonable_dict(config: NestedNamespace, d: dict[str, Any]) -> Scenario:

        target_settings = [
            CompilerSetting.from_jsonable_dict(config, cs)
            for cs in d["target_settings"]
        ]
        attacker_settings = [
            CompilerSetting.from_jsonable_dict(config, cs)
            for cs in d["attacker_settings"]
        ]

        s = Scenario(target_settings, attacker_settings)

        if "instrumenter_version" in d:
            s.instrumenter_version = d["instrumenter_version"]
            s.generator_version = d["generator_versio"]
            s.bisector_version = d["bisector_version"]
            s.reducer_version = d["reducer_version"]
        else:
            s.instrumenter_version = 0
            s.generator_version = 0
            s.bisector_version = 0
            s.reducer_version = 0

        return s

    @staticmethod
    def from_file(config: NestedNamespace, file: Path) -> Scenario:
        with open(file, "r") as f:
            js = json.load(f)
            return Scenario.from_jsonable_dict(config, js)


def run_cmd(
    cmd: Union[str, list[str]],
    working_dir: Optional[Path] = None,
    additional_env: dict[str, str] = {},
    **kwargs: Any,  # https://github.com/python/mypy/issues/8772
) -> str:

    if working_dir is None:
        working_dir = Path(os.getcwd())
    env = os.environ.copy()
    env.update(additional_env)

    if isinstance(cmd, str):
        cmd = cmd.strip().split(" ")
    output = subprocess.run(
        cmd, cwd=str(working_dir), check=True, env=env, capture_output=True, **kwargs
    )

    #logging.debug(output.stdout.decode("utf-8").strip())
    #logging.debug(output.stderr.decode("utf-8").strip())
    res: str = output.stdout.decode("utf-8").strip()
    return res


def run_cmd_to_logfile(
    cmd: Union[str, list[str]],
    log_file: Optional[TextIO] = None,
    working_dir: Optional[Path] = None,
    additional_env: dict[str, str] = {},
) -> None:

    if working_dir is None:
        working_dir = Path(os.getcwd())
    env = os.environ.copy()
    env.update(additional_env)

    if isinstance(cmd, str):
        cmd = cmd.strip().split(" ")

    subprocess.run(
        cmd,
        cwd=working_dir,
        check=True,
        stdout=log_file,
        stderr=subprocess.STDOUT,
        env=env,
        capture_output=False,
    )


def find_include_paths(clang: str, file: str, flags: str) -> list[str]:
    cmd = [clang, file, "-c", "-o/dev/null", "-v"]
    if flags:
        cmd.extend(flags.split())
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    assert result.returncode == 0
    output = result.stdout.decode("utf-8").split("\n")
    start = (
        next(
            i
            for i, line in enumerate(output)
            if "#include <...> search starts here:" in line
        )
        + 1
    )
    end = next(i for i, line in enumerate(output) if "End of search list." in line)
    return [output[i].strip() for i in range(start, end)]


def get_scenario(config: NestedNamespace, args: argparse.Namespace) -> Scenario:
    """Extract the scenario from the parser and config.
    This function the following options be part of the parser.
    args.scenario
    args.targets
    args.targets-default_opt_levels and
    args.additional_compilers
    args.additional_compilers_default_opt_levels

    Args:
        config (NestedNamespace): config
        args (argparse.Namespace): parsed arguments.

    Returns:
        Scenario:
    """

    scenario = Scenario([], [])

    if args.scenario:
        scenario = Scenario.from_file(config, Path(args.scenario))

    if args.targets:
        target_settings = get_compiler_settings(
            config, args.targets, default_opt_levels=args.targets_default_opt_levels
        )
        scenario.target_settings = target_settings

    if args.additional_compilers:
        additional_compilers = get_compiler_settings(
            config,
            args.additional_compilers,
            default_opt_levels=args.additional_compilers_default_opt_levels,
        )
        scenario.attacker_settings = additional_compilers

    return scenario


def get_marker_prefix(marker: str) -> str:
    # Markers are of the form [a-Z]+[0-9]+_
    return marker.rstrip("_").rstrip("0123456789")


def get_compiler_settings(
    config: NestedNamespace, args: list[str], default_opt_levels: list[str]
) -> list[CompilerSetting]:
    settings: list[CompilerSetting] = []

    possible_opt_levels = ["1", "2", "3", "s", "z"]

    pos = 0
    while len(args[pos:]) > 1:
        compiler_config = get_compiler_config(args[pos], Path(config.repodir))
        repo = compiler_config.repo
        rev = repo.rev_to_commit(args[pos + 1])
        pos += 2

        opt_levels: set[str] = set(default_opt_levels)
        while pos < len(args) and args[pos] in possible_opt_levels:
            opt_levels.add(args[pos])
            pos += 1

        settings.extend(
            [CompilerSetting(compiler_config, rev, lvl) for lvl in opt_levels]
        )

    if len(args[pos:]) != 0:
        raise Exception(
            f"Couldn't completely parse compiler settings. Parsed {args[:pos]}; missed {args[pos:]}"
        )

    return settings


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


def get_interesting_settings(
    config: NestedNamespace, file: Path
) -> tuple[list[CompilerSetting], list[CompilerSetting]]:
    with open(file, "r") as f:
        d = json.load(f)
        bad_settings = [
            CompilerSetting.from_jsonable_dict(config, bs) for bs in d["bad_settings"]
        ]
        good_settings = [
            CompilerSetting.from_jsonable_dict(config, gs) for gs in d["good_settings"]
        ]

        return bad_settings, good_settings


@dataclass
class Case:
    code: str
    marker: str
    bad_setting: CompilerSetting
    good_settings: list[CompilerSetting]
    scenario: Scenario

    reduced_code: Optional[str]
    bisection: Optional[str]
    timestamp: float

    path: Optional[Path]

    def __init__(
        self,
        code: str,
        marker: str,
        bad_setting: CompilerSetting,
        good_settings: list[CompilerSetting],
        scenario: Scenario,
        reduced_code: Optional[str],
        bisection: Optional[str],
        path: Optional[Path] = None,
        timestamp: Optional[float] = None,
    ):

        self.code = code
        self.marker = marker
        self.bad_setting = bad_setting
        self.good_settings = good_settings
        self.scenario = scenario
        self.reduced_code = reduced_code
        self.bisection = bisection
        self.path = path

        self.timestamp = timestamp if timestamp else time.time()

    def add_flags(self, flags: list[str]) -> None:
        for f in flags:
            self.bad_setting.add_flag(f)
            for gs in self.good_settings:
                gs.add_flag(f)

        self.scenario.add_flags(flags)

    @staticmethod
    def from_file(config: NestedNamespace, file: Path) -> Case:
        with tarfile.open(file, "r") as tf:

            names = tf.getnames()

            code = check_and_get(tf, "code.c")
            marker = check_and_get(tf, "marker.txt")
            int_settings = json.loads(check_and_get(tf, "interesting_settings.json"))
            bad_setting = CompilerSetting.from_jsonable_dict(
                config, int_settings["bad_setting"]
            )
            good_settings = [
                CompilerSetting.from_jsonable_dict(config, jgs)
                for jgs in int_settings["good_settings"]
            ]

            scenario = Scenario.from_jsonable_dict(
                config, json.loads(check_and_get(tf, "scenario.json"))
            )
            reduced_code = None
            if "reduced_code_0.c" in names:
                reduced_code = check_and_get(tf, "reduced_code_0.c")

            bisection = None
            if "bisection_0.txt" in names:
                bisection = check_and_get(tf, "bisection_0.txt")

            # "Legacy support"
            try:
                timestamp = float(check_and_get(tf, "timestamp.txt"))
            except FileExistsError:
                timestamp = file.stat().st_mtime

            return Case(
                code,
                marker,
                bad_setting,
                good_settings,
                scenario,
                reduced_code,
                bisection,
                file.absolute(),
                timestamp,
            )

    def to_file(self, file: Path) -> None:
        with tarfile.open(file, "w") as tf:
            ntf = save_to_tmp_file(self.code)

            tf.add(ntf.name, "code.c")

            ntf = save_to_tmp_file(self.marker)
            tf.add(ntf.name, "marker.txt")

            int_settings: dict[str, Any] = {}
            int_settings["bad_setting"] = self.bad_setting.to_jsonable_dict()
            int_settings["good_settings"] = [
                gs.to_jsonable_dict() for gs in self.good_settings
            ]
            ntf = save_to_tmp_file(json.dumps(int_settings))
            tf.add(ntf.name, "interesting_settings.json")

            scenario_str = json.dumps(self.scenario.to_jsonable_dict())
            ntf = save_to_tmp_file(scenario_str)
            tf.add(ntf.name, "scenario.json")

            ntf = save_to_tmp_file(str(self.timestamp))
            tf.add(ntf.name, "timestamp.txt")

            if self.reduced_code:
                ntf = save_to_tmp_file(self.reduced_code)
                tf.add(ntf.name, "reduced_code_0.c")

            if self.bisection:
                ntf = save_to_tmp_file(self.bisection)
                tf.add(ntf.name, "bisection_0.txt")

    def to_jsonable_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {}
        d["code"] = self.code
        d["marker"] = self.marker
        d["bad_setting"] = self.bad_setting.to_jsonable_dict()
        d["good_settings"] = [gs.to_jsonable_dict() for gs in self.good_settings]
        d["scenario"] = self.scenario.to_jsonable_dict()

        d["reduced_code"] = self.reduced_code
        d["bisection"] = self.bisection

        d["timestamp"] = self.timestamp

        d["path"] = self.path
        return d

    @staticmethod
    def from_jsonable_dict(config: NestedNamespace, d: dict[str, Any]) -> Case:
        bad_setting = CompilerSetting.from_jsonable_dict(config, d["bad_setting"])
        good_settings = [
            CompilerSetting.from_jsonable_dict(config, dgs)
            for dgs in d["good_settings"]
        ]

        scenario = Scenario.from_jsonable_dict(config, d["scenario"])
        path = None
        if d["path"]:
            path = Path(d["path"])
        return Case(
            d["code"],
            d["marker"],
            bad_setting,
            good_settings,
            scenario,
            d["reduced_code"],
            d["bisection"],
            path,
            timestamp=d["timestamp"],
        )


def get_latest_compiler_setting_from_list(
    repo: Repo, l: list[CompilerSetting]
) -> CompilerSetting:
    """Finds and returns newest compiler setting wrt main branch
    in the list. Assumes all compilers to be of the same 'type' i.e. gcc, clang,...

    Args:
        repo (repository.Repo): Repositiory of compiler type
        l (list[CompilerSetting]): List of compilers to sort

    Returns:
        CompilerSetting: Compiler closest to main
    """

    def cmp_func(a: CompilerSetting, b: CompilerSetting) -> int:
        if a.rev == b.rev:
            return 0
        if repo.is_branch_point_ancestor_wrt_master(a.rev, b.rev):
            return -1
        else:
            return 1

    return max(l, key=functools.cmp_to_key(cmp_func))

# =================== Builder Helper ====================
class CompileError(Exception):
    """Exception raised when the compiler fails to compile something.

    There are two common reasons for this to appear:
    - Easy: The code file has is not present/disappeard.
    - Hard: Internal compiler errors.
    """

    pass

def find_alive_markers(
    code: str,
    compiler_setting: CompilerSetting,
    marker_prefix: str,
    bldr: BuilderWithCache,
) -> set[str]:
    """Return set of markers which are found in the assembly.

    Args:
        code (str): Code with markers
        compiler_setting (utils.CompilerSetting): Compiler to use
        marker_prefix (str): Prefix of markers (utils.get_marker_prefix)
        bldr (Builder): Builder to get the compiler

    Returns:
        set[str]: Set of markers found in the assembly i.e. alive markers

    Raises:
        CompileError: Raised when code can't be compiled.
    """
    alive_markers = set()

    # Extract alive markers
    alive_regex = re.compile(f".*[call|jmp].*{marker_prefix}([0-9]+)_.*")

    asm = get_asm_str(code, compiler_setting, bldr)

    for line in asm.split("\n"):
        line = line.strip()
        m = alive_regex.match(line)
        if m:
            alive_markers.add(f"{marker_prefix}{m.group(1)}_")

    return alive_markers

class CompileContext:
    def __init__(self, code: str):
        self.code = code
        self.fd_code: Optional[int] = None
        self.fd_asm: Optional[int] = None
        self.code_file: Optional[str] = None
        self.asm_file: Optional[str] = None

    def __enter__(self) -> tuple[str, str]:
        self.fd_code, self.code_file = tempfile.mkstemp(suffix=".c")
        self.fd_asm, self.asm_file = tempfile.mkstemp(suffix=".s")

        with open(self.code_file, "w") as f:
            f.write(self.code)

        return (self.code_file, self.asm_file)

    def __exit__(
        self,
        exc_type: Optional[type[BaseException]],
        exc_value: Optional[BaseException],
        exc_traceback: Optional[TracebackType],
    ) -> None:
        if self.code_file and self.fd_code and self.asm_file and self.fd_asm:
            os.remove(self.code_file)
            os.close(self.fd_code)
            # In case of a CompileError,
            # the file itself might not exist.
            if Path(self.asm_file).exists():
                os.remove(self.asm_file)
            os.close(self.fd_asm)
        else:
            raise BuildException("Compier context exited but was not entered")


def get_asm_str(
    code: str, compiler_setting: CompilerSetting, bldr: BuilderWithCache
) -> str:
    """Get assembly of `code` compiled by `compiler_setting`.

    Args:
        code (str): Code to compile to assembly
        compiler_setting (utils.CompilerSetting): Compiler to use
        bldr (Builder): Builder to get the compiler

    Returns:
        str: Assembly of `code`

    Raises:
        CompileError: Is raised when compilation failes i.e. has a non-zero exit code.
    """
    # Get the assembly output of `code` compiled with `compiler_setting` as str

    compiler_exe = get_compiler_executable(compiler_setting, bldr)

    with CompileContext(code) as context_res:
        code_file, asm_file = context_res

        cmd = f"{compiler_exe} -S {code_file} -o{asm_file} -O{compiler_setting.opt_level}".split(
            " "
        )
        cmd += compiler_setting.get_flag_cmd()
        try:
            run_cmd(cmd)
        except subprocess.CalledProcessError:
            raise CompileError()

        with open(asm_file, "r") as f:
            return f.read()

def get_compiler_executable(
    compiler_setting: CompilerSetting, bldr: BuilderWithCache
) -> Path:
    """Get the path to the compiler *binary* i.e. [...]/bin/clang

    Args:
        compiler_setting (utils.CompilerSetting): Compiler to get the binary of
        bldr (Builder): Builder to get/build the requested compiler.

    Returns:
        Path: Path to compiler binary
    """
    compiler_path = bldr.build_rev_with_config(compiler_setting.compiler_config, compiler_setting.rev)
    compiler_exe = pjoin(compiler_path, "bin", compiler_setting.compiler_config.name)
    return Path(compiler_exe)


def get_verbose_compiler_info(
    compiler_setting: CompilerSetting, bldr: BuilderWithCache
) -> str:
    cpath = get_compiler_executable(compiler_setting, bldr)

    return (
        subprocess.run(
            f"{cpath} -v".split(),
            stderr=subprocess.STDOUT,
            stdout=subprocess.PIPE,
        )
        .stdout.decode("utf-8")
        .strip()
    )




def get_llvm_IR(
    code: str, compiler_setting: CompilerSetting, bldr: BuilderWithCache
) -> str:
    if compiler_setting.compiler_config.name != "clang":
        raise CompileError("Requesting LLVM IR from non-clang compiler!")

    compiler_exe = get_compiler_executable(compiler_setting, bldr)

    with CompileContext(code) as context_res:
        code_file, asm_file = context_res

        cmd = f"{compiler_exe} -emit-llvm -S {code_file} -o{asm_file} -O{compiler_setting.opt_level}".split(
            " "
        )
        cmd += compiler_setting.get_flag_cmd()
        try:
            run_cmd(cmd)
        except subprocess.CalledProcessError:
            raise CompileError()

        with open(asm_file, "r") as f:
            return f.read()


