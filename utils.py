import argparse
import copy
import json
import logging
import os
import shutil
import stat
import subprocess
import tarfile
import tempfile
from dataclasses import dataclass
from functools import reduce
from os.path import join as pjoin
from pathlib import Path
from types import SimpleNamespace
from typing import Optional, TextIO, Union, Sequence, Any

import parsers
import repository


class Executable(object):
    pass


# fmt: off
# When adding new options, don't forget to also put them in the init script!
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
    (Executable,("ccc",),                   "Path to executable or name in PATH for the callchain checker"),
    (Executable,("static_annotator",),      "Path to executable or name in PATH for the static annotator"),
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
            tmp = reduce(lambda x, y: x[y].__dict__, key[:-1], self.__dict__)
            return tmp[key[-1]]
        else:
            return self.__dict__[key[0]]

    def __setitem__(self, key: Union[str, Sequence[str]], value: Any) -> None:
        if isinstance(key, str):
            self.__dict__[key] = value
        assert isinstance(key, Sequence)
        if len(key) > 1:
            tmp = reduce(lambda x, y: x[y].__dict__, key[:-1], self.__dict__)
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

    def __asdict(self) -> dict:
        d = {}
        for key, value in self.__dict__.items():
            if isinstance(value, NestedNamespace):
                dvalue = value.__asdict()
            else:
                dvalue = copy.deepcopy(value)
            d[key] = dvalue
        return d

    def __deepcopy__(self, memo):
        return type(self)(self.__asdict())


def validate_config(config: Union[dict[str, Any], NestedNamespace]):
    # TODO: Also check if there are fields that are not supposed to be there
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
                if tmpconfig == "":
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
                if type(tmpconfig) is not list:
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


def to_absolute_paths(config: NestedNamespace):
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
    config_path: Optional[Union[os.PathLike[str], Path]] = None, validate: bool = True
):
    if config_path is None:
        p = Path.home() / ".config/dce/config.json"
        if p.exists():
            config_path = p
        else:
            raise Exception("Found no config.json file at {p}!")
        logging.debug(f"Using config found at {config_path}")
    else:
        if not Path(config_path).is_file():
            raise Exception("Found no config.json file at {p}!")

    with open(config_path, "r") as f:
        config = json.load(f)

    config["config_path"] = str(Path(config_path).absolute())

    config = NestedNamespace(config)
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

    # Read values from CLI and override them in config
    for _, path, _ in EXPECTED_ENTRIES:
        arg_val = args_parser.__dict__[".".join(path)]
        if arg_val is not None:
            config[path] = arg_val

    validate_config(config)

    return config, args_parser


def create_symlink(src: Path, dst: Path):
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
    compiler_config: NestedNamespace
    rev: str
    opt_level: Optional[str] = None
    additional_flags: Optional[list[str]] = None

    def __str__(self):
        if self.additional_flags is None:
            return f"{self.compiler_config.name} {self.rev} {self.opt_level}"
        else:
            return (
                f"{self.compiler_config.name} {self.rev} {self.opt_level} "
                + " ".join(self.additional_flags)
            )

    def to_jsonable_dict(self):
        d = {}
        d["compiler_config"] = self.compiler_config.name
        d["rev"] = self.rev
        d["opt_level"] = self.opt_level
        d["additional_flags"] = (
            self.additional_flags if self.additional_flags is not None else []
        )

        return d

    @staticmethod
    def from_jsonable_dict(config: NestedNamespace, d: dict):
        return CompilerSetting(
            get_compiler_config(config, d["compiler_config"]),
            d["rev"],
            d["opt_level"],
            d["additional_flags"],
        )

    def add_flag(self, flag: str):
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
    def from_str(s: str, config: NestedNamespace):
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


@dataclass
class Scenario:
    target_settings: list[CompilerSetting]
    attacker_settings: list[CompilerSetting]

    def add_flags(self, new_flags: list[str]):
        for f in new_flags:
            for s in self.target_settings:
                s.add_flag(f)
            for s in self.attacker_settings:
                s.add_flag(f)

    def to_jsonable_dict(self) -> dict:
        d = {}
        d["target_settings"] = [s.to_jsonable_dict() for s in self.target_settings]
        d["attacker_settings"] = [s.to_jsonable_dict() for s in self.attacker_settings]

        return d

    @staticmethod
    def from_jsonable_dict(config: NestedNamespace, d: dict):

        target_settings = [
            CompilerSetting.from_jsonable_dict(config, cs)
            for cs in d["target_settings"]
        ]
        attacker_settings = [
            CompilerSetting.from_jsonable_dict(config, cs)
            for cs in d["attacker_settings"]
        ]

        return Scenario(target_settings, attacker_settings)

    @staticmethod
    def from_file(config: NestedNamespace, file: Path):
        with open(file, "r") as f:
            js = json.load(f)
            return Scenario.from_jsonable_dict(config, js)


def run_cmd(
    cmd: Union[str, list[str]],
    working_dir: Optional[os.PathLike] = None,
    additional_env: dict = {},
    **kwargs,
) -> str:

    if working_dir is None:
        working_dir = Path(os.getcwd())
    env = os.environ.copy()
    env.update(additional_env)

    if isinstance(cmd, str):
        cmd = cmd.strip().split(" ")
    output = subprocess.run(
        cmd, cwd=working_dir, check=True, env=env, capture_output=True, **kwargs
    )

    logging.debug(output.stdout.decode("utf-8").strip())
    logging.debug(output.stderr.decode("utf-8").strip())
    return output.stdout.decode("utf-8").strip()


def run_cmd_to_logfile(
    cmd: Union[str, list[str]],
    log_file: TextIO = None,
    working_dir: Optional[os.PathLike[str]] = None,
    additional_env: dict = {},
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


def find_include_paths(clang, file, flags):
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


def get_compiler_config(config: NestedNamespace, arg: Union[list[str], str]):
    if isinstance(arg, list):
        compiler = arg[0]
    else:
        compiler = arg

    if compiler == "gcc":
        compiler_config = config.gcc
    elif compiler == "llvm" or compiler == "clang":
        compiler_config = config.llvm
    else:
        print(f"Unknown compiler project {compiler}")
        exit(1)
    return compiler_config


def get_scenario(config: NestedNamespace, args: argparse.Namespace) -> Scenario:
    # This function requires
    # args.scenario
    # args.targets
    # args.targets-default_opt_levels and
    # args.additional_compilers
    # args.additional_compilers_default_opt_levels

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
        compiler_config = get_compiler_config(config, args[pos:])
        repo = repository.Repo(compiler_config.repo, compiler_config.main_branch)
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


def save_to_tmp_file(content: str):
    ntf = tempfile.NamedTemporaryFile()
    with open(ntf.name, "w") as f:
        f.write(content)

    return ntf


def check_and_get(tf: tarfile.TarFile, member: str) -> str:
    f = tf.extractfile(member)
    if not f:
        raise Exception(f"File does not include member {member}!")
    res = f.read().decode("utf-8").strip()

    return res


def get_interesting_settings(
    config: NestedNamespace, file: Path
) -> tuple[CompilerSetting, list[CompilerSetting]]:
    with open(file, "r") as f:
        d = json.load(f)
        bad_setting = CompilerSetting.from_jsonable_dict(config, d["bad_setting"])
        good_settings = [
            CompilerSetting.from_jsonable_dict(config, gs) for gs in d["good_settings"]
        ]

        return bad_setting, good_settings


@dataclass
class Case:
    code: str
    marker: str
    bad_setting: CompilerSetting
    good_settings: list[CompilerSetting]
    scenario: Scenario

    reduced_code: list[str]
    bisections: list[str]

    path: Optional[Path]

    def add_flags(self, flags: list[str]):
        for f in flags:
            self.bad_setting.add_flag(f)
            for gs in self.good_settings:
                gs.add_flag(f)

        self.scenario.add_flags(flags)

    @staticmethod
    def from_file(config: NestedNamespace, file: Path):
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
            reduced_code = []
            counter = 0
            red_n = f"reduced_code_{counter}.c"
            while red_n in names:
                reduced_code.append(check_and_get(tf, red_n))
                counter += 1
                red_n = f"reduced_code_{counter}.c"

            bisections = []
            counter = 0
            bis_n = f"bisection_{counter}.txt"
            while bis_n in names:
                bisections.append(check_and_get(tf, bis_n))
                counter += 1
                bis_n = f"bisection_{counter}.txt"

            return Case(
                code,
                marker,
                bad_setting,
                good_settings,
                scenario,
                reduced_code,
                bisections,
                file.absolute(),
            )

    def to_file(self, file: Path):
        with tarfile.open(file, "w") as tf:
            ntf = save_to_tmp_file(self.code)

            tf.add(ntf.name, "code.c")

            ntf = save_to_tmp_file(self.marker)
            tf.add(ntf.name, "marker.txt")

            int_settings = {}
            int_settings["bad_setting"] = self.bad_setting.to_jsonable_dict()
            int_settings["good_settings"] = [
                gs.to_jsonable_dict() for gs in self.good_settings
            ]
            ntf = save_to_tmp_file(json.dumps(int_settings))
            tf.add(ntf.name, "interesting_settings.json")

            scenario_str = json.dumps(self.scenario.to_jsonable_dict())
            ntf = save_to_tmp_file(scenario_str)
            tf.add(ntf.name, "scenario.json")

            for i, rcode in enumerate(self.reduced_code):
                ntf = save_to_tmp_file(rcode)
                tf.add(ntf.name, f"reduced_code_{i}.c")

            for i, bisection_rev in enumerate(self.bisections):
                ntf = save_to_tmp_file(bisection_rev)
                tf.add(ntf.name, f"bisection_{i}.txt")

    def to_jsonable_dict(self) -> dict:
        d: dict[str, Any] = {}
        d["code"] = self.code
        d["marker"] = self.marker
        d["bad_setting"] = self.bad_setting.to_jsonable_dict()
        d["good_settings"] = [gs.to_jsonable_dict() for gs in self.good_settings]
        d["scenario"] = self.scenario.to_jsonable_dict()

        d["reduced_code"] = self.reduced_code
        d["bisections"] = self.bisections

        d["path"] = self.path
        return d

    @staticmethod
    def from_jsonable_dict(config: NestedNamespace, d: dict):
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
            d["bisections"],
            path,
        )
