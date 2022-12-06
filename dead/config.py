""" A globally accessible configuration used throughout dead.

It is stored to get_default_config_path() and is read every time
dead is launched. Tool paths, include paths, etc are stored here, e.g.:
DeadConfig.get_config().csmith is the path to the csmith executable
"""
from __future__ import annotations

import json
from dataclasses import Field, dataclass, fields
from inspect import signature
from pathlib import Path
from shutil import which
from typing import Any

from diopter.compiler import CComp, CompilerExe

__all__ = ["DeadConfig", "update_config", "interactive_init"]


@dataclass(frozen=True, kw_only=True)
class DeadConfig:
    """Global configuration where all the relevant stuff is stored

    DeadConfig stores all the necessary information to run dead.


    Attributes:
        clang (CompilerExe):
            clang executable used for sanitization checks
        gcc (CompilerExe):
            gcc executable used for sanitization checks
        ccomp (CComp | None):
            if present compcert executable used for sanitization checks
        csmith (Path):
            csmith executable used for generating test cases
        csmith_include_path (Path):
            csmith include path used for compiler test cases
        creduce (Path):
            creduce executable used for reducing test cases

    Class Attributes:
        config (DeadConfig):
            the singleton global config
    """

    clang: CompilerExe
    gcc: CompilerExe
    ccomp: CComp | None
    csmith: Path
    csmith_include_path: Path
    creduce: Path

    def __post_init__(self) -> None:
        # TODO: introduce class Exe in diopter that verified the path is executable?
        execs = [self.clang.exe, self.gcc.exe, self.csmith, self.creduce]
        if self.ccomp:
            execs.append(self.ccomp.exe)

        for exe in execs:
            assert which(exe), f"{exe} is not executable"

    @classmethod
    def init(
        cls,
        *,
        clang: CompilerExe,
        gcc: CompilerExe,
        ccomp: CComp | None,
        csmith: Path,
        csmith_include_path: Path,
        creduce: Path,
    ) -> None:
        """Creates an instance of DeadConfig and assings
        it to the class attribute DeadConfig.config

        Args:
            clang (CompilerExe):
                clang executable used for sanitization checks
            gcc (CompilerExe):
                gcc executable used for sanitization checks
            ccomp (CComp | None):
                if present compcert executable used for sanitization checks
            csmith (Path):
                csmith executable used for generating test cases
            csmith_include_path (Path):
                csmith include path used for compiler test cases
            creduce (Path):
                creduce executable used for reducing test cases
        """
        config = DeadConfig(
            clang=clang,
            gcc=gcc,
            ccomp=ccomp,
            csmith=csmith,
            csmith_include_path=csmith_include_path,
            creduce=creduce,
        )
        setattr(cls, "config", config)

    @classmethod
    def reset(cls, config: DeadConfig) -> None:
        """Resets the global DeadConfig.config with config.

        Args:
            config (DeadConfig):
                the new global configuration
        """
        setattr(cls, "config", config)

    @classmethod
    def get_config(cls) -> DeadConfig:
        """Returns the global DeadConfig instance (can be
        initialized with DeadDeadConfig.init(...))

        DeadConfig.config must have been initialized before
        calling this method.

        Returns:
            DeadConfig:
                the global configuration
        """
        assert hasattr(cls, "config"), "DeadConfig is not initialized"
        config = getattr(cls, "config")
        assert type(config) is DeadConfig
        return config

    def to_jsonable_dict(self) -> dict[str, str]:
        """Conversion to a dictionary.

        Returns:
            dict[str, str]:
                A dictionary holding the configuration's entries.
        """

        d = {
            "clang": str(self.clang.exe),
            "gcc": str(self.gcc.exe),
            "ccomp": "None" if not self.ccomp else str(self.ccomp.exe),
            "csmith": str(self.csmith),
            "csmith_include_path": str(self.csmith_include_path),
            "creduce": str(self.creduce),
        }
        assert set(d.keys()) == set(
            f.name for f in fields(DeadConfig)
        ), "DeadConfig.to_jsonable_dict is missing one or more fields"
        return d


def __handle_field(
    stored_value: str, field: Field[Any]
) -> CompilerExe | CComp | None | Path:
    """Parses a string into a DeadConfig entry with type field.

    Args:
        stored_value (str):
            the input to be parsed
        field (Field[Any]):
            the type of field to parse to

    Returns:
        (CompilerExe | CComp | None | Path):
            the parsed field
    """
    match field.type:
        case "CompilerExe":
            return CompilerExe.from_path(Path(stored_value))
        case "Path":
            return Path(stored_value)
        case "CComp | None":
            if stored_value != "None":
                return CComp(exe=Path(stored_value))
            return None
        case _:
            print(
                f"config: Unknown field {field.name} with "
                f"unknown type: {field.type}. Exiting..."
            )
            exit(1)
    # Make mypy happy
    exit(1)


class MissingEntryError(Exception):
    def __init__(self, missing_field: str) -> None:
        self.missing_field = missing_field


def __parse_config_from_dict(entries: dict[str, str]) -> DeadConfig:
    """Reads the configuration from json_file

    Args:
        json_file (Path):
            path to the json file where the config is stored

    Returns:
        DeadConfig:
            the parsed config
    """

    # Programatically parse all fields
    config_fields = fields(DeadConfig)
    loaded_fields = {}
    for field in config_fields:
        if field.name not in entries:
            raise MissingEntryError(f"{field}")

        loaded_fields[field.name] = __handle_field(entries[field.name], field)
    return DeadConfig(**loaded_fields)  # type: ignore


def init_config_from_file(json_file: Path) -> None:
    """Reads the configuration from json_file and initializes the global DeadConfig.

    Args:
        json_file (Path):
            path to the json file where the config is stored
    """
    json_file = get_default_config_path()
    with open(str(json_file), "r") as jf:
        stored_config = json.load(jf)
    try:
        DeadConfig.reset(__parse_config_from_dict(stored_config))
    except MissingEntryError as e:
        print(
            f"{json_file} does not contain {e.missing_field}, "
            "either update it (check the --update-config flag) "
            "or delete it. Exiting..."
        )
        exit(1)


def get_default_config_path() -> Path:
    return Path.home() / ".config" / "dead" / "config.json"


def dump_config(json_file: Path = get_default_config_path()) -> None:
    """Write the global DeadConfig to a json file.

    Args:
        json_file (Path):
            where to write the config
    """
    json_file.parent.mkdir(parents=True, exist_ok=True)
    with open(str(json_file), "w") as f:
        json.dump(DeadConfig.get_config().to_jsonable_dict(), f)


def update_config(
    clang: CompilerExe | None,
    gcc: CompilerExe | None,
    ccomp: CComp | None,
    csmith: Path | None,
    csmith_include_path: Path | None,
    creduce: Path | None,
) -> None:
    """Update the global DeadConfig with the non-None arguments.

    The arguments that are None are ignored.

    Args:
        clang (CompilerExe | None):
            new clang to use for sanitization checks
        gcc (CompilerExe | None):
            new gcc to use for sanitization checks
        ccomp (CComp | None):
            new compcert to use for sanitization checks
        csmith (Path | None):
            new csmith to use for test case generation
        csmith_include_path (Path | None):
            new csmith include path to use for test case compilation
        creduce (Path | None):
            new csmith to use for test case reduction
    """

    # Check that the arguments of this function are
    # in sync with the attributes of DeadConfig
    assert set(signature(update_config).parameters.keys()) == set(
        f.name for f in fields(DeadConfig)
    ), (
        "Parameter mismatch between config.update_stored_config "
        "and config.DeadConfig, this should not happen"
    )

    config = DeadConfig.get_config()

    DeadConfig.init(
        clang=clang if clang else config.clang,
        gcc=gcc if gcc else config.gcc,
        ccomp=ccomp if ccomp else config.ccomp,
        csmith=csmith if csmith else config.csmith,
        csmith_include_path=csmith_include_path
        if csmith_include_path
        else config.csmith_include_path,
        creduce=creduce if creduce else config.creduce,
    )


def __ask_yes_no(question: str) -> bool:
    answer = None
    while answer not in ["y", "Y", "n", "N"]:
        answer = input(question + " [Y/n] ")
        if not answer:
            answer = "y"
    return answer in ("y", "Y")


def find_csmith_include_path() -> Path | None:
    # TODO: move this to diopter
    # TODO: what other default paths exist?
    for p in (
        Path("/usr/include/csmith-2.3.0"),
        Path("/usr/local/include/csmith-2.3.0"),
        Path("/usr/include/csmith"),
        Path("/usr/local/include/csmith"),
    ):
        if p.exists():
            return p
    return None


def interactive_init(
    clang: CompilerExe | None,
    gcc: CompilerExe | None,
    ccomp: CComp | None,
    csmith: Path | None,
    csmith_include_path: Path | None,
    creduce: Path | None,
) -> None:
    """Initialize the global DeadConfig with the non-None arguments.

    The user is prompted for all arguments that are None. Defaults are
    looked up, the user can dismiss them and provide different values.

    The initialized config is stored to get_default_config_path().

    Args:
        clang (CompilerExe | None):
            clang to use for sanitization checks
        gcc (CompilerExe | None):
            gcc to use for sanitization checks
        ccomp (CComp | None):
            compcert to use for sanitization checks
        csmith (Path | None):
            csmith to use for test case generation
        csmith_include_path (Path | None):
            csmith include path to use for test case compilation
        creduce (Path | None):
            csmith to use for test case reduction
    """

    # Check that the arguments of this function are
    # in sync with the attributes of DeadConfig
    assert set(signature(update_config).parameters.keys()) == set(
        f.name for f in fields(DeadConfig)
    ), (
        "Parameter mismatch between config.interactive_init "
        "and config.DeadConfig, this should not happen"
    )

    # XXX: most entries could become optional and specific functionalities can
    # be disabled and print the appropriate messages, i.e., prompt the user to
    # update config

    p = get_default_config_path()
    if p.exists():
        init_config_from_file(p)
        update_config(clang, gcc, ccomp, csmith, csmith_include_path, creduce)
        return
    print(f"{p} does not exist.")
    if not __ask_yes_no("Should I create it?"):
        print("Aborting")
        exit(0)

    if clang:
        print(f"Using the provided clang: {clang.exe}")
    else:
        clang = CompilerExe.get_system_clang()
        if not __ask_yes_no(f"I found {clang.exe}, should I use it?"):
            # TODO: do some error checking here
            clang = CompilerExe.from_path(Path(input("Type the path to clang: ")))
    if gcc:
        print(f"Using the provided gcc: {gcc.exe}")
    else:
        gcc = CompilerExe.get_system_gcc()
        if not __ask_yes_no(f"I found {gcc.exe} should I use it?"):
            # TODO: do some error checking here
            gcc = CompilerExe.from_path(Path(input("Type the path to gcc: ")))
    if ccomp:
        print(f"Using the provided ccomp: {ccomp.exe}")
    else:
        ccomp_ = CComp.get_system_ccomp()
        if ccomp_ and __ask_yes_no(f"I found {ccomp_.exe}, should I use it?"):
            ccomp = ccomp_
        elif __ask_yes_no(
            "Do you want to specify a CompCert executable to use for testing?"
        ):
            # TODO: do some error checking here
            ccomp = CComp(exe=Path(input("Type the path to gcc: ")))

    if csmith:
        print(f"Using the provided csmith: {csmith}")
    else:
        csmith_ = which("csmith")
        if csmith_ and __ask_yes_no(f"I found {csmith_} should I use it?"):
            csmith = Path(csmith_)
        else:
            csmith = Path(input("Type the path to csmith: "))

    if csmith_include_path:
        print(f"Using the provided csmith include path: {csmith_include_path}")
    else:
        inc_path = find_csmith_include_path()
        if inc_path and __ask_yes_no(f"I found {inc_path} should I use it?"):
            csmith_include_path = inc_path
        else:
            csmith_include_path = Path(input("Type csmith include path: "))

    if creduce:
        print(f"Using the provided creduce: {creduce}")
    else:
        creduce_ = which("creduce")
        if creduce_ and __ask_yes_no(f"I found {creduce_} should I use it?"):
            creduce = Path(creduce_)
        else:
            creduce = Path(input("Type the path to creduce: "))

    DeadConfig.init(
        clang=clang,
        gcc=gcc,
        ccomp=ccomp,
        csmith=csmith,
        csmith_include_path=csmith_include_path,
        creduce=creduce,
    )
    dump_config(get_default_config_path())
