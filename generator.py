#!/usr/bin/env python3

import dataclasses
import logging
import os
import re
import signal
import subprocess
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass
from multiprocessing import Process, Queue
from os.path import join as pjoin
from pathlib import Path
from random import randint
from tempfile import NamedTemporaryFile
from typing import Optional, Union

import builder
import checker
import parsers
import patcher
import repository
import utils
from sanitize import sanitize


def run_csmith(csmith):
    tries = 0
    while True:
        options = [
            "arrays",
            "bitfields",
            "checksum",
            "comma-operators",
            "compound-assignment",
            "consts",
            "divs",
            "embedded-assigns",
            "jumps",
            "longlong",
            "force-non-uniform-arrays",
            "math64",
            "muls",
            "packed-struct",
            "paranoid",
            "pointers",
            "structs",
            "inline-function",
            "return-structs",
            "arg-structs",
            "dangling-global-pointers",
        ]

        cmd = [
            csmith,
            "--no-unions",
            "--safe-math",
            "--no-argc",
            "--no-volatiles",
            "--no-volatile-pointers",
        ]
        for option in options:
            if randint(0, 1):
                cmd.append(f"--{option}")
            else:
                cmd.append(f"--no-{option}")
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        if result.returncode == 0:
            return result.stdout.decode("utf-8")
        else:
            tries += 1
            if tries > 10:
                raise Exception("CSmith failed 10 times in a row!")


def instrument_program(dcei: Path, file: Path, include_paths: list[str]):
    cmd = [str(dcei), str(file)]
    for path in include_paths:
        cmd.append(f"--extra-arg=-isystem{str(path)}")
    utils.run_cmd(cmd)
    return "DCEMarker"


def generate_file(config: utils.NestedNamespace, additional_flags: str):
    additional_flags += f" -I {config.csmith.include_path}"
    while True:
        try:
            logging.debug("Generating new candidate...")
            candidate = run_csmith(config.csmith.executable)
            if len(candidate) > config.csmith.max_size:
                continue
            if len(candidate) < config.csmith.min_size:
                continue
            with NamedTemporaryFile(suffix=".c") as ntf:
                with open(ntf.name, "w") as f:
                    print(candidate, file=f)
                logging.debug("Checking if program is sane...")
                if not sanitize(
                    config.gcc.sane_version,
                    config.llvm.sane_version,
                    config.ccomp,
                    ntf.name,
                    additional_flags,
                ):
                    continue
                include_paths = utils.find_include_paths(
                    config.llvm.sane_version, ntf.name, additional_flags
                )
                include_paths.append(config.csmith.include_path)
                logging.debug("Instrumenting candidate...")
                marker_prefix = instrument_program(
                    config.dcei, Path(ntf.name), include_paths
                )
                with open(ntf.name, "r") as f:
                    return marker_prefix, f.read()

            return marker_prefix, candidate
        except subprocess.TimeoutExpired:
            pass


class CSmithCaseGenerator:
    def __init__(
        self, config: utils.NestedNamespace, patchdb, cores: Optional[int] = None
    ):
        self.config = config
        self.builder = builder.Builder(config, patchdb, cores)
        self.chkr = checker.Checker(config, self.builder)

    def generate_interesting_case(
        self,
        target_compiler: utils.CompilerSetting,
        target_opt_levels: list[str],
        additional_compiler: list[utils.CompilerSetting],
    ):
        # Because the resulting code will be of csmith origin, we have to add
        # the csmith include path to all settings
        csmith_include_flag = f"-I{self.config.csmith.include_path}"
        target_compiler.add_flag(csmith_include_flag)
        for acs in additional_compiler:
            acs.add_flag(csmith_include_flag)

        all_opt_levels = ["1", "2", "s", "z", "3"]

        target_tests = []
        for opt in target_opt_levels:
            cp = dataclasses.replace(target_compiler)
            cp.opt_level = opt
            target_tests.append(cp)

        tests = []
        for opt in all_opt_levels:
            for setting in additional_compiler + [target_compiler]:
                cp = dataclasses.replace(setting)
                cp.opt_level = opt
                tests.append(cp)

        try_counter = 0
        while True:
            logging.debug("Generating new candidate...")
            marker_prefix, candidate_code = generate_file(self.config, "")

            # Find alive markers
            logging.debug("Getting alive markers...")
            target_alive_marker_list = [
                (
                    tt,
                    builder.find_alive_markers(
                        candidate_code, tt, marker_prefix, self.builder
                    ),
                )
                for tt in target_tests
            ]

            tester_alive_marker_list = [
                (
                    tt,
                    builder.find_alive_markers(
                        candidate_code, tt, marker_prefix, self.builder
                    ),
                )
                for tt in tests
            ]

            target_alive_markers = set()
            for _, marker_set in target_alive_marker_list:
                target_alive_markers.update(marker_set)

            # Extract reduce cases
            logging.debug("Extracting reduce cases...")
            for marker in target_alive_markers:
                good = []
                for good_setting, good_alive_markers in tester_alive_marker_list:
                    if (
                        marker not in good_alive_markers
                    ):  # i.e. the setting eliminated the call
                        good.append(good_setting)

                # Find bad cases
                if len(good) > 0:
                    for bad_setting, bad_alive_markers in target_alive_marker_list:
                        if (
                            marker in bad_alive_markers
                        ):  # i.e. the setting didn't eliminate the call
                            # Create reduce case
                            case = utils.ReduceCase(
                                code=candidate_code,
                                marker=marker,
                                bad_setting=bad_setting,
                                good_settings=good,
                            )
                            # We already know that the case is_interesting_wrt_marker
                            # and because csmith have static globals, we also don't need
                            # is_interesting_with_static_globals
                            if self.chkr.is_interesting_wrt_ccc(
                                case
                            ) and self.chkr.is_interesting_with_empty_marker_bodies(
                                case
                            ):
                                logging.info(
                                    f"Try {try_counter}: Found case! LENGTH: {len(candidate_code)}"
                                )
                                return case
            else:
                logging.info(f"Try {try_counter}: Found no case. Onto the next one!")
                try_counter += 1

    def _wrapper_interesting(
        self,
        queue: Queue,
        target_compiler: utils.CompilerSetting,
        target_opt_levels: list[str],
        additional_compiler: list[utils.CompilerSetting],
    ):
        logging.info("Starting worker...")
        while True:
            case = self.generate_interesting_case(
                target_compiler, target_opt_levels, additional_compiler
            )
            queue.put(str(case))

    def parallel_interesting_case(
        self,
        target_compiler: utils.CompilerSetting,
        target_opt_levels: list[str],
        additional_compiler: list[utils.CompilerSetting],
        processes: int,
        output_dir: os.PathLike,
        start_stop: Optional[bool] = False,
    ):
        queue = Queue()

        # Create processes
        procs = [
            Process(
                target=self._wrapper_interesting,
                args=(queue, target_compiler, target_opt_levels, additional_compiler),
            )
            for _ in range(processes)
        ]

        # Start processes
        for p in procs:
            p.daemon = True
            p.start()

        # read queue
        counter = 0
        while True:
            # TODO: handle process failure
            case: str = queue.get()

            h = hash(case)
            h = max(h, -h)
            path = pjoin(output_dir, f"case_{counter:08}-{h:019}.c")
            with open(path, "w") as f:
                logging.debug("Writing case to {path}...")
                f.write(case)
                f.flush()

            counter += 1
            if start_stop:
                # Send processes to "sleep"
                logging.debug("Stopping workers...")
                for p in procs:
                    if p.pid is None:
                        continue
                    os.kill(p.pid, signal.SIGSTOP)
            yield path
            if start_stop:
                logging.debug("Restarting workers...")
                # Awake processes again for further search
                for p in procs:
                    if p.pid is None:
                        continue
                    os.kill(p.pid, signal.SIGCONT)


if __name__ == "__main__":
    config, args = utils.get_config_and_parser(parsers.generator_parser())

    cores = args.cores

    patchdb = patcher.PatchDB(config.patchdb)
    case_generator = CSmithCaseGenerator(config, patchdb, cores)

    if args.interesting:
        if args.target is None:
            print("--target is required for --interesting")
            exit(1)
        else:
            compiler = args.target[0]
            if compiler == "gcc":
                compiler_config = config.gcc
            elif compiler == "llvm" or compiler == "clang":
                compiler_config = config.llvm
            else:
                print(f"Unknown compiler project {compiler}")
                exit(1)
            # Use full hash to avoid ambiguity
            repo = repository.Repo(compiler_config.repo, compiler_config.main_branch)
            rev = repo.rev_to_commit(args.target[1])
            target_setting = utils.CompilerSetting(compiler_config, rev)

        additional_compiler = []
        if args.additional_compiler is not None:
            len_addcomp = len(args.additional_compiler)
            if len_addcomp % 2 == 1:
                print(
                    f"Odd number of arguments for --additional-compiler; must be of form [PROJECT REV]*"
                )
                exit(1)
            else:
                for i in range(0, len_addcomp, 2):
                    compiler = args.additional_compiler[i]
                    if compiler == "gcc":
                        compiler_config = config.gcc
                    elif compiler == "llvm" or compiler == "clang":
                        compiler_config = config.llvm
                    else:
                        print(f"Unknown compiler project {compiler}")
                        exit(1)
                    # Use full hash to avoid ambiguity
                    repo = repository.Repo(
                        compiler_config.repo, compiler_config.main_branch
                    )
                    rev = repo.rev_to_commit(args.additional_compiler[i + 1])
                    setting = utils.CompilerSetting(compiler_config, rev)
                    additional_compiler.append(setting)

        target_opt_levels = args.target_opt_levels

        if args.output_directory is None:
            print("Missing output directory!")
            exit(1)
        else:
            output_dir = os.path.abspath(args.output_directory)
            os.makedirs(output_dir, exist_ok=True)

        if args.parallel is not None:
            amount_cases = args.amount if args.amount is not None else 0
            amount_processes = max(1, args.parallel)
            gen = case_generator.parallel_interesting_case(
                target_compiler=target_setting,
                target_opt_levels=target_opt_levels,
                additional_compiler=additional_compiler,
                processes=amount_processes,
                output_dir=output_dir,
                start_stop=False,
            )
            for i in range(amount_cases):
                print(next(gen))
        else:
            print(
                case_generator.generate_interesting_case(
                    target_compiler=target_setting,
                    target_opt_levels=target_opt_levels,
                    additional_compiler=additional_compiler,
                )
            )
    else:
        # TODO
        print("Not implemented yet")
