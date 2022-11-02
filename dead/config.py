from __future__ import annotations

import json
from shutil import which
from typing import Optional, Any
from dataclasses import dataclass, fields, Field
from pathlib import Path
from inspect import signature

from diopter.compiler import CompilerExe, CComp
from ccbuilder import Repo, DEFAULT_REPOS_DIR  # should Repo really be in ccbuilder?

# TODO: add documentation

# XXX: introduce class Exe in diopter that verified the path is executable?


@dataclass(frozen=True, kw_only=True)
class DeadConfig:
    llvm: CompilerExe
    llvm_repo: Repo
    gcc: CompilerExe
    gcc_repo: Repo
    ccomp: Optional[CComp]
    csmith: Path
    csmith_include_path: Path
    creduce: Path

    @classmethod
    def init(
        cls,
        *,
        llvm: CompilerExe,
        llvm_repo: Repo,
        gcc: CompilerExe,
        gcc_repo: Repo,
        ccomp: Optional[CComp],
        csmith: Path,
        csmith_include_path: Path,
        creduce: Path,
    ) -> None:
        setattr(
            cls,
            "config",
            DeadConfig(
                llvm=llvm,
                llvm_repo=llvm_repo,
                gcc=gcc,
                gcc_repo=gcc_repo,
                ccomp=ccomp,
                csmith=csmith,
                csmith_include_path=csmith_include_path,
                creduce=creduce,
            ),
        )

    @classmethod
    def get_config(cls) -> DeadConfig:
        assert hasattr(cls, "config"), "DeadConfig is not initialized"
        config = getattr(cls, "config")
        assert type(config) is DeadConfig
        return config

    def to_jsonable_dict(self) -> dict[str, str]:
        d = {
            "llvm": str(self.llvm.exe),
            "llvm_repo": str(self.llvm_repo.path),
            "gcc": str(self.gcc.exe),
            "gcc_repo": str(self.gcc_repo.path),
            "ccomp": "None" if not self.ccomp else str(self.ccomp.exe),
            "csmith": str(self.csmith),
            "csmith_include_path": str(self.csmith_include_path),
            "creduce": str(self.creduce),
        }
        assert set(d.keys()) == set(
            f.name for f in fields(DeadConfig)
        ), "DeadConfig.to_jsonable_dict is missing one or more fields"
        return d


def handle_field(
    stored_value: str, field: Field[Any]
) -> CompilerExe | Repo | Optional[CComp] | Path:
    match field.type:
        case t if t is CompilerExe:
            return CompilerExe.from_path(Path(stored_value))
        case t if t is Repo:
            match stored_value.split(","):
                case ("llvm", p):
                    return Repo.llvm_repo(p)
                case ("gcc", p):
                    return Repo.gcc_repo(p)
                case _:
                    print(
                        "config: repo entry with invalid format, "
                        "it should be (llvm|gcc, path_to_repo). Exiting..."
                    )
                    exit(1)
        case t if t is Path:
            return Path(stored_value)
        case t if t is Optional[CComp]:
            if stored_value != "None":
                return CComp(exe=Path(stored_value))
            return None
        case _:
            print(
                f"config: Unknown field {field.name} with "
                "unknown type: {field.type}. Exiting..."
            )
            exit(1)
    # Make mypy happy
    exit(1)


def init_config_from_file(json_file: Path) -> None:
    json_file = get_default_config_path()
    with open(str(json_file), "r") as jf:
        stored_config = json.load(jf)

    config_fields = fields(DeadConfig)
    loaded_fields = {}
    for field in config_fields:
        if field.name not in stored_config:
            print(
                f"{json_file} does not contain {field}, "
                "either update it (check the --update-config flag) "
                "or delete it. Exiting..."
            )
            exit(1)
        loaded_fields[field.name] = handle_field(stored_config[field.name], field)
        assert loaded_fields[field.name] is field.type  # type: ignore
    DeadConfig.init(**loaded_fields)  # type: ignore


def dump_config(json_file: Path) -> None:
    json_file.parent.mkdir(parents=True, exist_ok=True)
    with open(str(json_file), "w") as f:
        json.dump(DeadConfig.get_config().to_jsonable_dict(), f)


def get_default_config_path() -> Path:
    return Path.home() / ".config" / "dead" / "config.json"


def update_config(
    llvm: Optional[CompilerExe] = None,
    llvm_repo: Optional[Repo] = None,
    gcc: Optional[CompilerExe] = None,
    gcc_repo: Optional[Repo] = None,
    ccomp: Optional[CComp] = None,
    csmith: Optional[Path] = None,
    csmith_include_path: Optional[Path] = None,
    creduce: Optional[Path] = None,
) -> None:
    assert set(signature(update_config).parameters.keys()) == set(
        f.name for f in fields(DeadConfig)
    ), (
        "Parameter mismatch between config.update_stored_config "
        "and config.DeadConfig, this should not happen"
    )

    config = DeadConfig.get_config()

    DeadConfig.init(
        llvm=llvm if llvm else config.llvm,
        llvm_repo=llvm_repo if llvm_repo else config.llvm_repo,
        gcc=gcc if gcc else config.gcc,
        gcc_repo=gcc_repo if gcc_repo else config.gcc_repo,
        ccomp=ccomp if ccomp else config.ccomp,
        csmith=csmith if csmith else config.csmith,
        csmith_include_path=csmith_include_path
        if csmith_include_path
        else config.csmith_include_path,
        creduce=creduce if creduce else config.creduce,
    )


def ask_yes_no(question: str) -> bool:
    answer = None
    while answer not in ["y", "Y", "n", "N"]:
        answer = input(question + " [Y/n] ")
        if not answer:
            answer = "y"
    return answer == "y"


def find_cmith_include_path() -> Optional[Path]:
    # TODO: move this to diopter
    # TODO: what other default paths exist?
    p = Path("/usr/include/csmith-2.3.0")
    if p.exists():
        return p
    return None


def interactive_init(
    llvm: Optional[CompilerExe] = None,
    llvm_repo: Optional[Repo] = None,
    gcc: Optional[CompilerExe] = None,
    gcc_repo: Optional[Repo] = None,
    ccomp: Optional[CComp] = None,
    csmith: Optional[Path] = None,
    csmith_include_path: Optional[Path] = None,
    creduce: Optional[Path] = None,
) -> None:
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
        return
    print(f"{p} does not exist.")
    if not ask_yes_no("Should I create it?"):
        print("Aborting")
        exit(0)

    if not llvm_repo:
        llvm_repo_dir = DEFAULT_REPOS_DIR / "llvm-project"
        if not ask_yes_no(f"Should I use {llvm_repo_dir} for the LLVM git repo?"):
            llvm_repo_dir = Path(
                input("Type the LLVM repo path (will be cloned if it doesn't exist: ")
            )
        llvm_repo = Repo.llvm_repo(llvm_repo_dir)
    if not gcc_repo:
        gcc_repo_dir = DEFAULT_REPOS_DIR / "gcc"
        if not ask_yes_no(f"Should I use {gcc_repo_dir} for the GCC git repo?"):
            gcc_repo_dir = Path(
                input("Type the GCC repo path (will be cloned if it doesn't exist: ")
            )
        gcc_repo = Repo.gcc_repo(gcc_repo_dir)

    if llvm:
        print(f"Using the provided clang: {llvm.exe}")
    else:
        llvm = CompilerExe.get_system_clang()
        if not ask_yes_no(f"I found {llvm.exe}, should I use it?"):
            # TODO: do some error checking here
            llvm = CompilerExe.from_path(Path(input("Type the path to clang: ")))
    if gcc:
        print(f"Using the provided gcc: {gcc.exe}")
    else:
        gcc = CompilerExe.get_system_gcc()
        if not ask_yes_no(f"I found {gcc.exe} should I use it?"):
            # TODO: do some error checking here
            gcc = CompilerExe.from_path(Path(input("Type the path to gcc: ")))
    if ccomp:
        print(f"Using the provided ccomp: {ccomp.exe}")
    else:
        ccomp_ = CComp.get_system_ccomp()
        if ccomp_ and ask_yes_no(f"I found {ccomp_.exe}, should I use it?"):
            ccomp = ccomp_
        elif ask_yes_no(
            "Do you want to specify a CompCert executable to use for testing?"
        ):
            # TODO: do some error checking here
            ccomp = CComp(exe=Path(input("Type the path to gcc: ")))

    if csmith:
        print(f"Using the provided csmith: {csmith}")
    else:
        csmith_ = which("csmith")
        if csmith_ and ask_yes_no(f"I found {csmith_} should I use it?"):
            csmith = Path(csmith_)
        else:
            csmith = Path(input("Type the path to csmith: "))

    if csmith_include_path:
        print(f"Using the provided csmith include path: {csmith_include_path}")
    else:
        inc_path = find_cmith_include_path()
        if inc_path and ask_yes_no(f"I found {inc_path} should I use it?"):
            csmith_include_path = inc_path
        else:
            csmith_include_path = Path(input("Type csmith include path: "))

    if creduce:
        print(f"Using the provided creduce: {creduce}")
    else:
        creduce_ = which("creduce")
        if creduce_ and ask_yes_no(f"I found {creduce_} should I use it?"):
            creduce = Path(creduce_)
        else:
            creduce = Path(input("Type the path to creduce: "))

    DeadConfig.init(
        llvm=llvm,
        llvm_repo=llvm_repo,
        gcc=gcc,
        gcc_repo=gcc_repo,
        ccomp=ccomp,
        csmith=csmith,
        csmith_include_path=csmith_include_path,
        creduce=creduce,
    )
    dump_config(get_default_config_path())
