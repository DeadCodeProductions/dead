#!/usr/bin/env python3

from __future__ import annotations

import logging
import multiprocessing
import os
import re
import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass
from os.path import join as pjoin
from pathlib import Path
from types import TracebackType
from typing import TYPE_CHECKING, Optional, TextIO

if TYPE_CHECKING:
    from utils import NestedNamespace

import parsers
import utils
from patchdatabase import PatchDB
from repository import Repo


# =================== Builder ====================
class BuildException(Exception):
    pass


@dataclass
class BuildContext:
    cache_prefix: Path
    success_indicator: Path
    compiler_config: NestedNamespace
    rev: str
    logdir: os.PathLike[str]
    cache_group: str

    def __enter__(self) -> tuple[Path, TextIO]:
        self.build_dir = tempfile.mkdtemp()
        os.makedirs(self.cache_prefix, exist_ok=True)

        self.starting_cwd = os.getcwd()
        os.chdir(self.build_dir)

        # Build log file
        current_time = time.strftime("%Y%m%d-%H%M%S")
        build_log_path = pjoin(
            self.logdir, f"{current_time}-{self.compiler_config.name}-{self.rev}.log"
        )
        self.build_log = open(build_log_path, "a")
        # Set permissions of logfile
        shutil.chown(build_log_path, group=self.cache_group)
        os.chmod(build_log_path, 0o660)
        logging.info(f"Build log at {build_log_path}")

        return (Path(self.build_dir), self.build_log)

    def __exit__(
        self,
        exc_type: Optional[type[BaseException]],
        exc_value: Optional[BaseException],
        exc_traceback: Optional[TracebackType],
    ) -> None:
        self.build_log.close()
        shutil.rmtree(self.build_dir)
        os.chdir(self.starting_cwd)

        # Build was not successful
        if not self.success_indicator.exists():
            # remove cache entry
            shutil.rmtree(self.cache_prefix)


class Builder:
    """Class to build different compilers."""

    def __init__(
        self,
        config: utils.NestedNamespace,
        patchdb: PatchDB,
        cores: Optional[int] = None,
        force: bool = False,
    ):
        """
        Args:
            config (utils.NestedNamespace): THE config.
            patchdb (PatchDB): The PatchDB instance to consult for which patches to use.
            cores (Optional[int]): How many jobs the builder should use.
            force (bool): Whether or not to force all builds.
        """
        self.config = config
        # Do not set cores to 0. For gcc this means all available cores,
        # for llvm this means infinite! You'll only survive this with around 250GB of RAM.
        self.cores = cores if cores else multiprocessing.cpu_count()
        self.patchdb = patchdb
        self.force = force

        self.llvm_versions = config.llvm.releases

        self.gcc_versions = config.gcc.releases

    def build(
        self,
        compiler_config: NestedNamespace,
        rev: str,
        additional_patches: Optional[list[Path]] = None,
        force: bool = False,
    ) -> Path:
        """Build the compiler specified.

        Args:
            compiler_config: What project to build (config.llvm/config.gcc).
            rev (str): Which revision/commit to build.
            additional_patches (Optional[list]): Which patches to apply *additionally*
                to the ones reported by the PatchDB.
            force (bool): Force to build a compiler, even if it is known to be bad.

        Returns:
            Path: Path to the compiler directory.
        """

        force = self.force or force
        repo = Repo(compiler_config.repo, main_branch=compiler_config.main_branch)
        prefix, symlink_prefix, rev = self._get_cache_prefix(rev, repo, compiler_config)
        success_indicator = Path(pjoin(prefix, "DONE"))

        if self._is_in_cache(prefix, success_indicator):
            if symlink_prefix:
                utils.create_symlink(prefix, symlink_prefix)
            return prefix

        required_patches = self._collect_patches(
            compiler_config, rev, repo, force, additional_patches
        )
        with BuildContext(
            prefix,
            success_indicator,
            compiler_config,
            rev,
            self.config.logdir,
            self.config.cache_group,
        ) as (tmpdir, build_log):
            utils.run_cmd(f"git worktree add {tmpdir} {rev} -f", compiler_config.repo)
            tmpdir_repo = Repo(Path(tmpdir), compiler_config.main_branch)
            self._apply_patches(tmpdir_repo, required_patches, compiler_config, rev)
            try:
                Builder._run_build(compiler_config, prefix, self.cores, build_log)
                # Build was successful and can be cached
                success_indicator.touch()
                # Other cache members should also be able to read the cache
                subprocess.run(f"chmod -R g+rwX {prefix}".split(" "))
            except subprocess.CalledProcessError as e:
                self.patchdb.save_bad(required_patches, rev, repo, compiler_config)
                raise BuildException(
                    f"Couldn't build {compiler_config.name} {rev} with patches {required_patches}. Exception: {e}"
                )

        self._update_patchdb(required_patches, rev, repo, compiler_config)

        if symlink_prefix:
            utils.create_symlink(prefix, symlink_prefix)

        return prefix

    def _get_cache_prefix(
        self, rev: str, repo: Repo, compiler_config: NestedNamespace
    ) -> tuple[Path, Optional[Path], str]:
        """Create the prefix path where the compiler is or will be installed.

        Args:
            rev (str): Which revision or commit.
            repo (Repo): The repository of the target compiler
            compiler_config: Which compiler to build (config.llvm/config.gcc).

        Returns:
            Path: Path to the prefix.
        """
        input_rev = rev
        rev = repo.rev_to_commit(rev)

        # For maximum caching efficiency, the cache should always work with the
        # full commit hash. However, to not confuse human operators, we will create a symlink
        # from $COMPILER_NAME-$INPUT_REV to $COMPILER_NAME-$FULL_COMMIT_HASH
        create_input_rev_symlink = input_rev != rev

        # Sanitize input rev
        input_rev = input_rev.replace("/", "-")

        # Installation prefix: [$PWD]/$CACHEDIR/$COMPILER-$REV
        prefix = Path(pjoin(self.config.cachedir, compiler_config.name + "-" + rev))
        symlink_prefix = Path(
            pjoin(self.config.cachedir, compiler_config.name + "-" + input_rev)
        )
        if not os.path.isabs(self.config.cachedir):
            prefix = os.getcwd() / prefix
            symlink_prefix = os.getcwd() / symlink_prefix

        return (prefix, symlink_prefix if create_input_rev_symlink else None, rev)

    @staticmethod
    def _run_build(
        compiler_config: NestedNamespace, prefix: Path, cores: int, build_log: TextIO
    ) -> None:
        os.makedirs("build")
        if compiler_config.name == "gcc":
            Builder._run_gcc_build(prefix, cores, build_log)
        elif compiler_config.name == "clang":
            Builder._run_clang_build(prefix, cores, build_log)

    @staticmethod
    def _run_gcc_build(prefix: Path, cores: int, build_log: TextIO) -> None:
        pre_cmd = "./contrib/download_prerequisites"
        logging.debug("GCC: Starting download_prerequisites")
        utils.run_cmd_to_logfile(pre_cmd, log_file=build_log)

        os.chdir("build")
        logging.debug("GCC: Starting configure")
        configure_cmd = f"../configure --disable-multilib --disable-bootstrap --enable-languages=c,c++ --prefix={prefix}"
        utils.run_cmd_to_logfile(configure_cmd, log_file=build_log)

        logging.debug("GCC: Starting to build...")
        utils.run_cmd_to_logfile(f"make -j {cores}", log_file=build_log)
        utils.run_cmd_to_logfile("make install", log_file=build_log)

    @staticmethod
    def _run_clang_build(prefix: Path, cores: int, build_log: TextIO) -> None:
        os.chdir("build")
        logging.debug("LLVM: Starting cmake")
        cmake_cmd = f"cmake -G Ninja -DCMAKE_BUILD_TYPE=Release -DLLVM_ENABLE_PROJECTS=clang -DLLVM_INCLUDE_BENCHMARKS=OFF -DLLVM_INCLUDE_TESTS=OFF -DLLVM_USE_NEWPM=ON -DLLVM_TARGETS_TO_BUILD=X86 -DCMAKE_INSTALL_PREFIX={prefix} ../llvm"
        utils.run_cmd_to_logfile(
            cmake_cmd,
            additional_env={"CC": "clang", "CXX": "clang++"},
            log_file=build_log,
        )

        logging.debug("LLVM: Starting to build...")
        utils.run_cmd_to_logfile(
            f"ninja -j {cores} install",
            log_file=build_log,
        )

    def _collect_patches(
        self,
        compiler_config: NestedNamespace,
        rev: str,
        repo: Repo,
        force: bool,
        additional_patches: Optional[list[Path]],
    ) -> list[Path]:
        """Collect the necessary (known) patches for the target build from the
        patch database.

        Args:
            compiler_config: The target compiler project (config.llvm/config.gcc).
            rev (str): Which revision/commit to build.
            repo (Repo): The repository of the target compiler
            force (bool): Force to build a compiler, even if it is known to be bad.
            additional_patches (Optional[list]): Which patches to apply *additionally*
                to the ones reported by the PatchDB.

        Returns:
            Path: Path to the compiler directory.
        """
        required_patches = self.patchdb.required_patches(rev, repo)
        if additional_patches:
            required_patches.extend(additional_patches)

        # Check if combination is a known bad one
        if not force and self.patchdb.is_known_bad(
            required_patches, rev, repo, compiler_config
        ):
            raise BuildException(
                f"Known Bad combination {compiler_config.name} {rev} with patches {required_patches}"
            )
        return required_patches

    def _is_in_cache(self, prefix: Path, success_indicator: Path) -> bool:
        # Super safe caching "lock"/queue /s
        if prefix.exists() and not success_indicator.exists():
            logging.info(f"{prefix} is currently building; need to wait")
            while not success_indicator.exists():
                # TODO Make this process a bit smarter so if something dies the process will continue eventually
                time.sleep(1)
                if not prefix.exists():
                    raise BuildException(f"Other build attempt failed for {prefix}")

        return prefix.exists() and success_indicator.exists()

    def _apply_patches(
        self,
        repo: Repo,
        patches: list[Path],
        compiler_config: NestedNamespace,
        rev: str,
    ) -> None:
        logging.debug("Checking patches...")
        for patch in patches:
            if not repo.apply([patch], check=True):
                self.patchdb.save_bad(patches, rev, repo, compiler_config)
                raise BuildException(f"Single patch {patch} not applicable to {rev}")
        logging.debug("Applying patches...")
        if len(patches) > 0:
            if not repo.apply(patches):
                self.patchdb.save_bad(patches, rev, repo, compiler_config)
                raise BuildException(
                    f"Not all patches are applicable to {rev}: {patches}"
                )

    def _update_patchdb(
        self,
        required_patches: list[Path],
        rev: str,
        repo: Repo,
        compiler_config: NestedNamespace,
    ) -> None:
        # Save combination as successful
        for patch in required_patches:
            self.patchdb.save(patch, [rev], repo)
        # Clear bad "bad"-entries for this combo
        self.patchdb.clear_bad(required_patches, rev, repo, compiler_config)

    def build_releases(self) -> None:
        for ver in self.llvm_versions:
            print(self.build(self.config.llvm, ver))

        for ver in self.gcc_versions:
            print(self.build(self.config.gcc, ver))
        return


# =================== Helper ====================
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


def get_compiler_executable(
    compiler_setting: utils.CompilerSetting, bldr: Builder
) -> Path:
    """Get the path to the compiler *binary* i.e. [...]/bin/clang

    Args:
        compiler_setting (utils.CompilerSetting): Compiler to get the binary of
        bldr (Builder): Builder to get/build the requested compiler.

    Returns:
        Path: Path to compiler binary
    """
    compiler_path = bldr.build(compiler_setting.compiler_config, compiler_setting.rev)
    compiler_exe = pjoin(compiler_path, "bin", compiler_setting.compiler_config.name)
    return Path(compiler_exe)


def get_verbose_compiler_info(
    compiler_setting: utils.CompilerSetting, bldr: Builder
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


def get_asm_str(
    code: str, compiler_setting: utils.CompilerSetting, bldr: Builder
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
            utils.run_cmd(cmd)
        except subprocess.CalledProcessError:
            raise CompileError()

        with open(asm_file, "r") as f:
            return f.read()


def get_llvm_IR(
    code: str, compiler_setting: utils.CompilerSetting, bldr: Builder
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
            utils.run_cmd(cmd)
        except subprocess.CalledProcessError:
            raise CompileError()

        with open(asm_file, "r") as f:
            return f.read()


def find_alive_markers(
    code: str,
    compiler_setting: utils.CompilerSetting,
    marker_prefix: str,
    bldr: Builder,
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


if __name__ == "__main__":
    config, args = utils.get_config_and_parser(parsers.builder_parser())

    cores = args.cores

    patchdb = PatchDB(config.patchdb)
    builder = Builder(config, cores=cores, patchdb=patchdb)

    if args.build_releases:
        builder.build_releases()
        exit(0)

    if args.compiler is None or args.revision is None:
        print("Error: Need --compiler and --revision")
        exit(1)

    compiler_config = utils.get_compiler_config(config, args.compiler)

    additional_patches = []
    if args.add_patches is not None:
        additional_patches = [
            Path(os.path.abspath(patch)) for patch in args.add_patches
        ]

    for rev in args.revision:
        print(
            builder.build(
                compiler_config,
                rev,
                additional_patches=additional_patches,
                force=args.force,
            )
        )
