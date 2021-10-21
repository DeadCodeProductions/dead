#!/usr/bin/env python3.9

import json
import os
import argparse
import logging
import subprocess
import tempfile
import time
import multiprocessing
import shutil

import utils
import parsers
import patcher

from types import SimpleNamespace
from typing import Optional, Union
from tempfile import TemporaryDirectory, NamedTemporaryFile
from pathlib import Path
from os.path import join as pjoin
from contextlib import contextmanager

class BuildException(Exception):
    pass


@contextmanager
def build_context(prefix: Path, success_indicator: Path) -> Path:
    build_dir = tempfile.mkdtemp()
    os.makedirs(prefix, exist_ok=True)

    starting_cwd = os.getcwd()
    os.chdir(build_dir)

    try:
        yield build_dir
    finally:
        shutil.rmtree(build_dir)
        os.chdir(starting_cwd)

        # Build was not successful
        if not success_indicator.exists():
            # remove cache entry
            shutil.rmtree(prefix)
            
class Builder():
    def __init__(self, config: utils.NestedNamespace,
            patchdb,
            cores: Optional[int] = None, force: bool=False):
        self.config = config
        # Do not set cores to 0. For gcc this means all available cores,
        # for llvm this means infinite! You'll only survive this with around 250GB of RAM.
        self.cores = cores if cores is not None else multiprocessing.cpu_count()
        self.patchdb = patchdb
        self.force = force

        self.llvm_versions = config.llvm.releases

        self.gcc_versions = config.gcc.releases

    def build(self, compiler_config, rev: str, cores: Optional[int] = None, additional_patches: Optional[list] = None, force: bool=False) -> Path:

        # Always force 
        force = self.force or force

        if cores is None:
            cores = self.cores

        repo = patcher.Repo(compiler_config.repo, main_branch=compiler_config.main_branch)

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
            symlink_prefix = Path(pjoin(self.config.cachedir, compiler_config.name + "-" + input_rev))
        else:
            prefix = Path(pjoin(os.getcwd(), self.config.cachedir, compiler_config.name + "-" + rev))
            symlink_prefix = Path(pjoin(os.getcwd(), self.config.cachedir, compiler_config.name + "-" + input_rev))
        success_indicator = Path(pjoin(prefix, "DONE"))


        # Super safe caching "lock"/queue
        if prefix.exists() and not success_indicator.exists():
            logging.info(f"{prefix} is currently building; need to wait")
            while not success_indicator.exists():
                # TODO Make this process a bit smarter so if something dies the process will continue eventually
                time.sleep(1)
                if not prefix.exists():
                    raise BuildException(f"Other build attempt failed for {prefix}")

        if prefix.exists() and success_indicator.exists():
            if create_input_rev_symlink:
                self._create_symlink(prefix, symlink_prefix)

            return prefix

        # Collect patches from patchdb
        required_patches = self.patchdb.required_patches(rev, repo)
        if isinstance(additional_patches, list):
            required_patches.extend(additional_patches)

        # Check if combination is a known bad one
        if not force and self.patchdb.is_known_bad(required_patches, rev, repo, compiler_config):
            raise BuildException(f"Known Bad combination {compiler_config.name} {rev} with patches {required_patches}")

        with build_context(prefix, success_indicator) as tmpdir:
            # Getting source code
            worktree_cmd = f"git worktree add {tmpdir} {rev} -f"
            git_output = utils.run_cmd(worktree_cmd, compiler_config.repo)

            tmpdir_repo = patcher.Repo(tmpdir, compiler_config.main_branch)

            # Applying patches
            logging.debug("Checking patches...")
            for patch in required_patches:
                if not tmpdir_repo.apply([patch], check=True):
                    self.patchdb.save_bad(required_patches, rev, repo, compiler_config)
                    raise BuildException(f"Single patch {patch} not applicable to {rev}")
            logging.debug("Applying patches...")
            if len(required_patches) > 0:
                if not tmpdir_repo.apply(required_patches):
                    self.patchdb.save_bad(required_patches, rev, repo, compiler_config)
                    raise BuildException(f"All patches not applicable to {rev}: {required_patches}")


            os.makedirs("build")

            # Debug help
            do_cmd_logging = False#not (logging.getLogger().getEffectiveLevel() <= logging.INFO)
            current_time = time.strftime("%Y%m%d-%H%M%S")
            build_log_path = pjoin(self.config.logdir, f"{current_time}-{compiler_config.name}-{rev}.log")
            
            with open(build_log_path, 'a') as build_log: 
                # Set permissions of logfile 
                shutil.chown(build_log_path, group=self.config.cache_group)
                os.chmod(build_log_path, 0o660)
                logging.info(f"Build log at {build_log_path}")
                try:
                    if compiler_config.name == "gcc":
                        pre_cmd = "./contrib/download_prerequisites"
                        logging.debug("GCC: Starting download_prerequisites")
                        pre_output = utils.run_cmd(pre_cmd, log=do_cmd_logging, log_file=build_log)

                        os.chdir("build")
                        logging.debug("GCC: Starting configure")
                        configure_cmd = f"../configure --disable-multilib --disable-bootstrap --enable-languages=c,c++ --prefix={prefix}"
                        utils.run_cmd(configure_cmd, log=do_cmd_logging, log_file=build_log)

                        logging.debug("GCC: Starting to build...")
                        utils.run_cmd(f"make -j {cores}", log=do_cmd_logging, log_file=build_log)
                        utils.run_cmd("make install", log=do_cmd_logging, log_file=build_log)


                    elif compiler_config.name == "clang":
                        os.chdir("build")
                        logging.debug("LLVM: Starting cmake")
                        cmake_cmd = f"cmake -G Ninja -DCMAKE_BUILD_TYPE=Release -DLLVM_ENABLE_PROJECTS=clang -DLLVM_INCLUDE_BENCHMARKS=OFF -DLLVM_INCLUDE_TESTS=OFF -DLLVM_USE_NEWPM=ON -DLLVM_TARGETS_TO_BUILD=X86 -DCMAKE_INSTALL_PREFIX={prefix} ../llvm"
                        utils.run_cmd(cmake_cmd, 
                                      additional_env = {"CC": "clang", "CXX": "clang++"},
                                      log=do_cmd_logging, log_file=build_log)

                        logging.debug("LLVM: Starting to build...")
                        utils.run_cmd(f"ninja -j {cores} install", log=do_cmd_logging, log_file=build_log)

                    # Build was successful and can be cached
                    success_indicator.touch()

                    # Other cache members should also be able to read the cache
                    subprocess.run(f"chmod -R g+rwX {prefix}".split(" "))


                except subprocess.CalledProcessError as e:
                    self.patchdb.save_bad(required_patches, rev, repo, compiler_config)
                    build_log.close()
                    raise BuildException(f"Couldn't build {compiler_config.name} {rev} with patches {required_patches}. Exception: {e}")

        # Save combination as successful
        for patch in required_patches:
            self.patchdb.save(patch, [rev], repo)
        # Clear bad "bad"-entries for this combo
        self.patchdb.clear_bad(required_patches, rev, repo, compiler_config)

        if create_input_rev_symlink:
            self._create_symlink(prefix, symlink_prefix)


        return prefix

    def build_releases(self):
        for ver in self.llvm_versions:
            print(self.build(self.config.llvm, ver, cores=cores))

        for ver in self.gcc_versions:
            print(self.build(self.config.gcc, ver, cores=cores))
        return
    
    def _create_symlink(self, src: os.PathLike, dst: os.PathLike):
        if dst.exists():
            if dst.is_symlink():
                dst.unlink()
            else:
                dst_symlink_config = Path(os.path.dirname(dst),
                                               "conflict_" + str(os.path.basename(dst)))

                logging.warning(f"Found non-symlink file or directory which should be a symlink: {dst}. Moving to {dst_symlink_config}...")
                shutil.move(dst, dst_symlink_config)

        logging.debug(f"Creating symlink {dst} to {src}")
        os.symlink(src, dst)


if __name__ == "__main__":
    config, args = utils.get_config_and_parser(parsers.builder_parser())

    cores = None if args.cores is None else args.cores[0]

    patchdb = patcher.PatchDB(config.patchdb)
    builder = Builder(config, cores=cores, patchdb=patchdb)

    if args.build_releases:
        builder.build_releases()
        exit(0)

    if args.compiler is None:
        print("Error: Need --compiler and --revision")
        exit(1)

    compiler = args.compiler[0]

    if compiler == "gcc":
        compiler_config = config.gcc
    elif compiler == "llvm" or compiler == "clang":
        compiler_config = config.llvm
    else:
        print(f"Unknown compiler project {compiler}")
        exit(1)

    additional_patches = None
    if args.add_patches is not None:
        additional_patches = [ os.path.abspath(patch) for patch in args.add_patches]
        
    for rev in args.revision:
        print(builder.build(compiler_config, rev, cores=cores,
              additional_patches=additional_patches, force=args.force))
