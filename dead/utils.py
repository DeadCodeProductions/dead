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


from diopter import compiler
from diopter.utils import run_cmd

from dead_instrumenter.instrumenter import InstrumentedProgram


@dataclass
class DeadConfig:
    llvm: compiler.CompilerExe
    llvm_repo: Repo
    gcc: compiler.CompilerExe
    gcc_repo: Repo
    ccomp: Optional[compiler.CComp]
    csmith_include_path: str

    @classmethod
    def init(
        cls,
        llvm: compiler.CompilerExe,
        llvm_repo: Repo,
        gcc: compiler.CompilerExe,
        gcc_repo: Repo,
        ccomp: Optional[compiler.CComp],
        csmith_include_path: str,
    ) -> None:
        setattr(
            cls,
            "config",
            DeadConfig(llvm, llvm_repo, gcc, gcc_repo, ccomp, csmith_include_path),
        )

    @classmethod
    def get_config(cls) -> DeadConfig:
        assert hasattr(cls, "config"), "DeadConfig is not initialized"
        config = getattr(cls, "config")
        assert type(config) is DeadConfig
        return config


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


# def get_scenario(
    # config: old_utils.NestedNamespace, args: argparse.Namespace, builder: Builder
# ) -> Scenario:
    # """Extract the scenario from the parser and config.
    # This function the following options be part of the parser.
    # args.targets
    # args.targets-default_opt_levels and
    # args.additional_compilers
    # args.additional_compilers_default_opt_levels

    # Args:
        # config (NestedNamespace): config
        # args (argparse.Namespace): parsed arguments.

    # Returns:
        # Scenario:
    # """

    # scenario = Scenario([], [])

    # target_settings = get_compilation_settings(
        # config,
        # args.targets,
        # default_opt_levels=args.targets_default_opt_levels,
        # builder=builder,
    # )
    # scenario.target_settings = target_settings

    # additional_compilers = get_compilation_settings(
        # config,
        # args.additional_compilers,
        # default_opt_levels=args.additional_compilers_default_opt_levels,
        # builder=builder,
    # )
    # scenario.attacker_settings = additional_compilers

    # assert scenario.attacker_settings, "No attacker compilers specified"
    # assert scenario.target_settings, "No target compilers specified"

    # return scenario


# def get_compilation_settings(
    # config: old_utils.NestedNamespace,
    # args: list[str],
    # default_opt_levels: list[str],
    # builder: Builder,
# ) -> list[compiler.CompilationSetting]:
    # settings: list[compiler.CompilationSetting] = []

    # possible_opt_levels = ["1", "2", "3", "s", "z"]

    # pos = 0
    # while len(args[pos:]) > 1:
        # project, repo = ccbuilder.get_compiler_info(args[pos], Path(config.repodir))  # type: ignore
        # rev = repo.rev_to_commit(args[pos + 1])
        # pos += 2

        # opt_levels: set[compiler.OptLevel] = set(
            # compiler.OptLevel.from_str(ol) for ol in default_opt_levels
        # )
        # while pos < len(args) and args[pos] in possible_opt_levels:
            # opt_levels.add(compiler.OptLevel.from_str(args[pos]))
            # pos += 1

        # settings.extend(
            # compiler.CompilationSetting(
                # compiler=compiler.CompilerExe(
                    # project, builder.build(project, rev, True), rev
                # ),
                # opt_level=lvl,
                # system_include_paths=(DeadConfig.get_config().csmith_include_path,),
            # )
            # for lvl in opt_levels
        # )

    # if len(args[pos:]) != 0:
        # raise Exception(
            # f"Couldn't completely parse compiler settings. Parsed {args[:pos]}; missed {args[pos:]}"
        # )

    # return settings


@dataclass
class RegressionCase:
    program: InstrumentedProgram
    marker: str
    bad_setting: compiler.CompilationSetting
    good_setting: compiler.CompilationSetting

    reduced_code: Optional[str]
    bisection: Optional[str]
    timestamp: float

    def __init__(
        self,
        program: InstrumentedProgram,
        marker: str,
        bad_setting: compiler.CompilationSetting,
        good_setting: compiler.CompilationSetting,
        reduced_code: Optional[str] = None,
        bisection: Optional[str] = None,
        timestamp: Optional[float] = None,
    ):
        self.program = program
        self.marker = marker
        self.bad_setting = bad_setting
        self.good_setting = good_setting
        self.reduced_code = reduced_code
        self.bisection = bisection
        self.timestamp = timestamp if timestamp else time.time()

    # def to_file(self, file: Path) -> None:
        # print("RegressionCase.to_file: NYI")
        # exit(1)

    # @staticmethod
    # def from_file(config: old_utils.NestedNamespace, file: Path) -> RegressionCase:
        # print("RegressionCase.from_file: NYI")
        # exit(1)


def repo_from_setting(setting: compiler.CompilationSetting) -> Repo:
    match setting.compiler.project:
        case ccbuilder.CompilerProject.GCC:
            return DeadConfig.get_config().gcc_repo
        case ccbuilder.CompilerProject.LLVM:
            return DeadConfig.get_config().llvm_repo
        case _:
            assert False, f"Unknown compiler project {setting.compiler.project}"


def setting_report_str(setting: compiler.CompilationSetting) -> str:
    return f"{setting.compiler.project.name}-{setting.compiler.revision} -O{setting.opt_level.name}"
