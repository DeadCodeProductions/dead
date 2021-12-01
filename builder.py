#!/usr/bin/env python3

import logging
import multiprocessing
import os
import re
import shutil
import subprocess
import tempfile
import time
from contextlib import contextmanager
from os.path import join as pjoin
from pathlib import Path
from typing import Optional, TextIO, Union

import parsers
import utils
from patchdatabase import PatchDB
from repository import Repo


# =================== Builder ====================
class BuildException(Exception):
    pass


@contextmanager
def build_context(
    prefix: Path,
    success_indicator: Path,
    compiler_config,
    rev,
    logdir: os.PathLike,
    cache_group: str,
) -> tuple[Path, TextIO]:
    build_dir = tempfile.mkdtemp()
    os.makedirs(prefix, exist_ok=True)

    starting_cwd = os.getcwd()
    os.chdir(build_dir)

    # Build log file
    current_time = time.strftime("%Y%m%d-%H%M%S")
    build_log_path = pjoin(logdir, f"{current_time}-{compiler_config.name}-{rev}.log")
    build_log = open(build_log_path, "a")
    # Set permissions of logfile
    shutil.chown(build_log_path, group=cache_group)
    os.chmod(build_log_path, 0o660)
    logging.info(f"Build log at {build_log_path}")

    try:
        yield (Path(build_dir), build_log)
    finally:
        build_log.close()
        shutil.rmtree(build_dir)
        os.chdir(starting_cwd)

        # Build was not successful
        if not success_indicator.exists():
            # remove cache entry
            shutil.rmtree(prefix)


class Builder:
    """Class to build different compilers."""

    def __init__(
        self,
        config: utils.NestedNamespace,
        patchdb,
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
        self.cores = cores if cores is not None else multiprocessing.cpu_count()
        self.patchdb = patchdb
        self.force = force

        self.llvm_versions = config.llvm.releases

        self.gcc_versions = config.gcc.releases

    def build(
        self,
        compiler_config,
        rev: str,
        cores: Optional[int] = None,
        additional_patches: Optional[list] = None,
        force: bool = False,
    ) -> Path:
        """Build the compiler specified.

        Args:
            compiler_config: What project to build (config.llvm/config.gcc).
            rev (str): Which revision/commit to build.
            cores (Optional[int]): How many cores to use.
                Builder.cores is used when not defined.
            additional_patches (Optional[list]): Which patches to apply *additionally*
                to the ones reported by the PatchDB.
            force (bool): Force to build a compiler, even if it is known to be bad.

        Returns:
            Path: Path to the compiler directory.
        """

        # Always force
        force = self.force or force

        if cores is None:
            cores = self.cores

        repo = Repo(compiler_config.repo, main_branch=compiler_config.main_branch)

        input_rev = rev
        rev = repo.rev_to_commit(rev)

        # For maximum caching efficiency, the cache should always work with the
        # full commit hash. However, to not confuse human operators, we will create a symlink
        # from $COMPILER_NAME-$INPUT_REV to $COMPILER_NAME-$FULL_COMMIT_HASH
        create_input_rev_symlink = False
        if input_rev != rev:
            create_input_rev_symlink = True

        # Sanitize input rev
        input_rev = input_rev.replace("/", "-")

        # Installation prefix: [$PWD]/$CACHEDIR/$COMPILER-$REV
        if os.path.isabs(self.config.cachedir):
            prefix = Path(pjoin(self.config.cachedir, compiler_config.name + "-" + rev))
            symlink_prefix = Path(
                pjoin(self.config.cachedir, compiler_config.name + "-" + input_rev)
            )
        else:
            prefix = Path(
                pjoin(
                    os.getcwd(), self.config.cachedir, compiler_config.name + "-" + rev
                )
            )
            symlink_prefix = Path(
                pjoin(
                    os.getcwd(),
                    self.config.cachedir,
                    compiler_config.name + "-" + input_rev,
                )
            )
        success_indicator = Path(pjoin(prefix, "DONE"))

        # Check cache
        if self._is_in_cache(prefix, success_indicator):
            if create_input_rev_symlink:
                utils.create_symlink(prefix, symlink_prefix)

            return prefix

        # Collect patches from patchdb
        required_patches = self.patchdb.required_patches(rev, repo)
        if isinstance(additional_patches, list):
            required_patches.extend(additional_patches)

        # Check if combination is a known bad one
        if not force and self.patchdb.is_known_bad(
            required_patches, rev, repo, compiler_config
        ):
            raise BuildException(
                f"Known Bad combination {compiler_config.name} {rev} with patches {required_patches}"
            )

        with build_context(
            prefix,
            success_indicator,
            compiler_config,
            rev,
            self.config.logdir,
            self.config.cache_group,
        ) as ctxt:
            tmpdir, build_log = ctxt
            # Getting source code
            worktree_cmd = f"git worktree add {tmpdir} {rev} -f"
            utils.run_cmd(worktree_cmd, compiler_config.repo)

            tmpdir_repo = Repo(Path(tmpdir), compiler_config.main_branch)

            # Apply patches
            self._apply_patches(tmpdir_repo, required_patches, compiler_config, rev)

            os.makedirs("build")

            # Compiling
            try:
                if compiler_config.name == "gcc":
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

                elif compiler_config.name == "clang":
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

                # Build was successful and can be cached
                success_indicator.touch()

                # Other cache members should also be able to read the cache
                subprocess.run(f"chmod -R g+rwX {prefix}".split(" "))

            except subprocess.CalledProcessError as e:
                self.patchdb.save_bad(required_patches, rev, repo, compiler_config)
                raise BuildException(
                    f"Couldn't build {compiler_config.name} {rev} with patches {required_patches}. Exception: {e}"
                )

        # Save combination as successful
        for patch in required_patches:
            self.patchdb.save(patch, [rev], repo)
        # Clear bad "bad"-entries for this combo
        self.patchdb.clear_bad(required_patches, rev, repo, compiler_config)

        if create_input_rev_symlink:
            utils.create_symlink(prefix, symlink_prefix)

        return prefix

    def _is_in_cache(self, prefix: Path, success_indicator: Path) -> bool:
        # Super safe caching "lock"/queue
        if prefix.exists() and not success_indicator.exists():
            logging.info(f"{prefix} is currently building; need to wait")
            while not success_indicator.exists():
                # TODO Make this process a bit smarter so if something dies the process will continue eventually
                time.sleep(1)
                if not prefix.exists():
                    raise BuildException(f"Other build attempt failed for {prefix}")

        return prefix.exists() and success_indicator.exists()

    def _apply_patches(
        self, repo, patches: list[os.PathLike], compiler_config, rev: str
    ):
        logging.debug("Checking patches...")
        for patch in patches:
            if not repo.apply([patch], check=True):
                self.patchdb.save_bad(patches, rev, repo, compiler_config)
                raise BuildException(f"Single patch {patch} not applicable to {rev}")
        logging.debug("Applying patches...")
        if len(patches) > 0:
            if not repo.apply(patches):
                self.patchdb.save_bad(patches, rev, repo, compiler_config)
                raise BuildException(f"All patches not applicable to {rev}: {patches}")

    def build_releases(self):
        for ver in self.llvm_versions:
            print(self.build(self.config.llvm, ver, cores=cores))

        for ver in self.gcc_versions:
            print(self.build(self.config.gcc, ver, cores=cores))
        return


# =================== Helper ====================
class CompileError(Exception):
    """Exception raised when the compiler fails to compile something.

    There are two common reasons for this to appear:
    - Easy: The code file has is not present/disappeard.
    - Hard: Internal compiler errors.
    """

    pass


@contextmanager
def compile_context(code: str):
    fd_code, code_file = tempfile.mkstemp(suffix=".c")
    fd_asm, asm_file = tempfile.mkstemp(suffix=".s")

    with open(code_file, "w") as f:
        f.write(code)

    try:
        yield (code_file, asm_file)
    finally:
        os.remove(code_file)
        os.close(fd_code)
        # In case of a CompileError,
        # the file itself might not exist.
        if Path(asm_file).exists():
            os.remove(asm_file)
        os.close(fd_asm)


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

    with compile_context(code) as context_res:
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

    additional_patches = None
    if args.add_patches is not None:
        additional_patches = [os.path.abspath(patch) for patch in args.add_patches]

    for rev in args.revision:
        print(
            builder.build(
                compiler_config,
                rev,
                cores=cores,
                additional_patches=additional_patches,
                force=args.force,
            )
        )
