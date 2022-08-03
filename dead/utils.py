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


class Executable(object):
    pass


# @dataclass
# class CompilerSetting:
    # compiler_project: CompilerProject
    # compiler_exe: str
    # repo: Repo
    # rev: str
    # opt_level: str
    # additional_flags: Optional[list[str]] = None

    # def __str__(self) -> str:
        # #FIXME: dump everything that is needed to rebuild this
        # if self.additional_flags is None:
            # return f"{self.compiler_project.name} {self.compiler_exe} {self.rev} {self.opt_level}"
        # else:
            # return (
                # f"{self.compiler_project.name} {self.compiler_exe} {self.rev} {self.opt_level} "
                # + " ".join(self.additional_flags)
            # )

    # def report_string(self) -> str:
        # """String to use in the report generation

        # Args:

        # Returns:
            # str: String to use in the report
        # """

        # return f"{self.compiler_project.name}-{self.rev} -O{self.opt_level}"

    # def add_flag(self, flag: str) -> None:
        # if not self.additional_flags:
            # self.additional_flags = [flag]
        # elif flag not in self.additional_flags:
            # self.additional_flags.append(flag)

    # def get_flag_str(self) -> str:
        # if self.additional_flags:
            # return " ".join(self.additional_flags)
        # else:
            # return ""

    # def get_flag_cmd(self) -> list[str]:
        # s = self.get_flag_str()
        # if s == "":
            # return []
        # else:
            # return s.split(" ")

    # @staticmethod
    # def from_str(s: str) -> CompilerSetting:
        # #FIXME: update with fixed __str__
        # s = s.strip()
        # parts = s.split(" ")

        # compiler = parts[0]
        # exe = parts[1]
        # rev = parts[2]
        # opt_level = parts[3]
        # additional_flags = parts[4:]
        # project, repo = ccbuilder.get_compiler_info(compiler, Path(repodir))  # type: ignore
        # return CompilerSetting(project, repo, rev, opt_level, additional_flags)


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


# def get_asm_str(code: str, compiler_setting: CompilerSetting) -> str:
    # """Get assembly of `code` compiled by `compiler_setting`.

    # Args:
        # code (str): Code to compile to assembly
        # compiler_setting (utils.CompilerSetting): Compiler to use

    # Returns:
        # str: Assembly of `code`

    # Raises:
        # CompileError: Is raised when compilation failes i.e. has a non-zero exit code.
    # """
    # # Get the assembly output of `code` compiled with `compiler_setting` as str

    # with CompileContext(code) as context_res:
        # code_file, asm_file = context_res

        # cmd = f"{compiler_setting.compiler_exe} -S {code_file} -o{asm_file} -O{compiler_setting.opt_level}".split(
            # " "
        # )
        # cmd += compiler_setting.get_flag_cmd()
        # try:
            # run_cmd(cmd)
        # except subprocess.CalledProcessError:
            # raise CompileError()

        # with open(asm_file, "r") as f:
            # return f.read()


# def get_compiler_executable(compiler_setting: CompilerSetting, bldr: Builder) -> Path:
    # """Get the path to the compiler *binary* i.e. [...]/bin/clang

    # Args:
        # compiler_setting (utils.CompilerSetting): Compiler to get the binary of
        # bldr (Builder): Builder to get/build the requested compiler.

    # Returns:
        # Path: Path to compiler binary
    # """
    # return bldr.build(
        # project=compiler_setting.compiler_project,
        # rev=compiler_setting.rev,
        # get_executable=True,
    # )


# def get_verbose_compiler_info(compiler_setting: CompilerSetting) -> str:
    # cpath = compiler_setting.compiler_exe

    # return (
        # subprocess.run(
            # f"{cpath} -v".split(),
            # stderr=subprocess.STDOUT,
            # stdout=subprocess.PIPE,
        # )
        # .stdout.decode("utf-8")
        # .strip()
    # )


# def get_llvm_IR(code: str, compiler_setting: CompilerSetting) -> str:
    # if (
        # compiler_setting.compiler_project.name != "clang"
        # and compiler_setting.compiler_project.name != "llvm"
    # ):
        # raise CompileError("Requesting LLVM IR from non-clang compiler!")

    # compiler_exe = compiler_setting.compiler_exe

    # with CompileContext(code) as context_res:
        # code_file, asm_file = context_res

        # cmd = f"{compiler_exe} -emit-llvm -S {code_file} -o{asm_file} -O{compiler_setting.opt_level}".split(
            # " "
        # )
        # cmd += compiler_setting.get_flag_cmd()
        # try:
            # run_cmd(cmd)
        # except subprocess.CalledProcessError:
            # raise CompileError()

        # with open(asm_file, "r") as f:
            # return f.read()
