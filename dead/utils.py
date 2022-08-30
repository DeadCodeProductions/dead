from __future__ import annotations

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


from diopter import compiler

import utils as old_utils


@dataclass
class DeadConfig:
    llvm: compiler.CompilerExe
    gcc: compiler.CompilerExe
    ccc: compiler.ClangTool
    ccomp: Optional[str]
    csmith_include_path: str

    @classmethod
    def init(
        cls,
        llvm: compiler.CompilerExe,
        gcc: compiler.CompilerExe,
        ccc: compiler.ClangTool,
        ccomp: Optional[str],
        csmith_include_path: str,
    ) -> None:
        setattr(cls, "config", DeadConfig(llvm, gcc, ccc, ccomp, csmith_include_path))

    @classmethod
    def get_config(cls) -> DeadConfig:
        assert hasattr(cls, "config"), "DeadConfig is not initialized"
        config = getattr(cls, "config")
        assert type(config) is DeadConfig
        return config


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


# def get_latest_compiler_setting_from_list(
# repo: Repo, l: list[CompilerSetting]
# ) -> CompilerSetting:
# """Finds and returns newest compiler setting wrt main branch
# in the list. Assumes all compilers to be of the same 'type' i.e. gcc, clang,...

# Args:
# repo (repository.Repo): Repositiory of compiler type
# l (list[CompilerSetting]): List of compilers to sort

# Returns:
# CompilerSetting: Compiler closest to main
# """

# def cmp_func(a: CompilerSetting, b: CompilerSetting) -> int:
# if a.rev == b.rev:
# return 0
# if repo.is_branch_point_ancestor_wrt_master(a.rev, b.rev):
# return -1
# else:
# return 1

# return max(l, key=functools.cmp_to_key(cmp_func))


# =================== Builder Helper ====================
class CompileError(Exception):
    """Exception raised when the compiler fails to compile something.

    There are two common reasons for this to appear:
    - Easy: The code file has is not present/disappeard.
    - Hard: Internal compiler errors.
    """

    pass


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


class Scenario:
    def __init__(
        self,
        target_settings: list[compiler.CompilationSetting],
        attacker_settings: list[compiler.CompilationSetting],
    ):
        self.target_settings = target_settings
        self.attacker_settings = attacker_settings


def old_compiler_setting_to_new_compilation_setting(
    compiler_setting_old: old_utils.CompilerSetting, builder: Builder
) -> compiler.CompilationSetting:
    project = compiler_setting_old.compiler_project
    exe = compiler.CompilerExe(
        project,
        builder.build(project, compiler_setting_old.rev, True),
        compiler_setting_old.repo.rev_to_commit(compiler_setting_old.rev),
    )
    match compiler_setting_old.opt_level:
        case "0":
            opt_level = compiler.OptLevel.O0
        case "1":
            opt_level = compiler.OptLevel.O1
        case "2":
            opt_level = compiler.OptLevel.O2
        case "3":
            opt_level = compiler.OptLevel.O3
        case "s":
            opt_level = compiler.OptLevel.Os
        case "z":
            opt_level = compiler.OptLevel.Oz
        case _:
            assert (
                False
            ), f"Unknown optimization level: {compiler_setting_old.opt_level}"
    return compiler.CompilationSetting(
        exe, opt_level, [], [], [DeadConfig.get_config().csmith_include_path]
    )


def compilation_setting_to_old_compiler_setting(
    setting: compiler.CompilationSetting, gcc_repo: Repo, llvm_repo: Repo
) -> old_utils.CompilerSetting:

    repo = gcc_repo if setting.compiler.project == CompilerProject.GCC else llvm_repo

    match setting.opt_level:
        case compiler.OptLevel.O0:
            opt_level = "0"
        case compiler.OptLevel.O1:
            opt_level = "1"
        case compiler.OptLevel.O2:
            opt_level = "2"
        case compiler.OptLevel.O3:
            opt_level = "3"
        case compiler.OptLevel.Os:
            opt_level = "s"
        case compiler.OptLevel.Oz:
            opt_level = "z"
        case _:
            assert False, f"Unknown optimization level: {setting.opt_level}"

    return old_utils.CompilerSetting(
        setting.compiler.project,
        repo,
        setting.compiler.revision,
        opt_level,
        [f"-I{inc}" for inc in setting.include_paths]
        + [f"-isystem{inc}" for inc in setting.system_include_paths],
    )


def old_scenario_to_new_scenario(
    scenario_old: old_utils.Scenario, builder: Builder
) -> Scenario:
    return Scenario(
        [
            old_compiler_setting_to_new_compilation_setting(setting, builder)
            for setting in scenario_old.target_settings
        ],
        [
            old_compiler_setting_to_new_compilation_setting(setting, builder)
            for setting in scenario_old.attacker_settings
        ],
    )


@dataclass
class Case:
    code: str
    marker: str
    bad_setting: compiler.CompilationSetting
    good_settings: list[compiler.CompilationSetting]
    scenario: Scenario

    reduced_code: Optional[str]
    bisection: Optional[str]
    timestamp: float

    path: Optional[Path]

    def __init__(
        self,
        code: str,
        marker: str,
        bad_setting: compiler.CompilationSetting,
        good_settings: list[compiler.CompilationSetting],
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
