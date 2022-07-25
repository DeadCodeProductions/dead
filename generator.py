#!/usr/bin/env python3

from __future__ import annotations

import json
import logging
import os
import signal
import subprocess
from multiprocessing import Process, Queue
from os.path import join as pjoin
from pathlib import Path
from random import randint
from tempfile import NamedTemporaryFile
from typing import TYPE_CHECKING, Generator, Optional, Union

from ccbuilder import Builder, BuildException, PatchDB, Repo
from dead_instrumenter.instrumenter import instrument_program
from diopter import generator, sanitizer

import checker
import parsers
import utils


class CSmithCaseGenerator(generator.CSmithGenerator):
    def __init__(
        self,
        config: utils.NestedNamespace,
        patchdb: PatchDB,
        cores: Optional[int] = None,
    ):
        super().__init__(
            csmith=config.csmith.executable,
            include_path=config.csmith.include_path,
            minimum_length=config.csmith.min_size,
            maximum_length=config.csmith.max_size,
            clang=config.llvm.sane_version,
            gcc=config.gcc.sane_version,
            ccomp=config.ccomp,
        )
        self.config: utils.NestedNamespace = config

        gcc_repo = Repo.gcc_repo(config.gcc.repo)
        llvm_repo = Repo.llvm_repo(config.llvm.repo)
        self.builder = Builder(
            cache_prefix=Path(config.cachedir),
            gcc_repo=gcc_repo,
            llvm_repo=llvm_repo,
            patchdb=patchdb,
            jobs=cores,
            logdir=Path(config.logdir),
        )
        self.chkr: checker.Checker = checker.Checker(config, self.builder)
        self.procs: list[Process] = []
        self.try_counter: int = 0

    def generate_code(self, additional_flags: str = "") -> str:
        additional_flags += f" -I {self.config.csmith.include_path}"
        while True:
            uninstrumented_code = super().generate_code()
            with NamedTemporaryFile(suffix=".c") as ntf:
                with open(ntf.name, "w") as f:
                    print(uninstrumented_code, file=f)
                logging.debug("Checking if program is sane...")
                if not sanitizer.sanitize_file(
                    self.config.gcc.sane_version,
                    self.config.llvm.sane_version,
                    self.config.ccomp,
                    Path(ntf.name),
                    additional_flags,
                ):
                    continue
                logging.debug("Instrumenting candidate...")
                _ = instrument_program(
                    Path(ntf.name), [f"-I{self.config.csmith.include_path}"]
                )
                with open(ntf.name, "r") as f:
                    return f.read()

    def generate_interesting_case(self, scenario: utils.Scenario) -> utils.Case:
        """Generate a case which is interesting i.e. has one compiler which does
        not eliminate a marker (from the target settings) a and at least one from
        the attacker settings.

        Args:
            scenario (utils.Scenario): Which compiler to compare.

        Returns:
            utils.Case: Intersting case.
        """
        # Because the resulting code will be of csmith origin, we have to add
        # the csmith include path to all settings
        csmith_include_flag = f"-I{self.config.csmith.include_path}"
        scenario.add_flags([csmith_include_flag])

        self.try_counter = 0
        while True:
            self.try_counter += 1
            logging.debug("Generating new candidate...")
            marker_prefix = "DCEMarker"
            candidate_code = self.generate_code()

            # Find alive markers
            logging.debug("Getting alive markers...")
            try:
                target_alive_marker_list = [
                    (
                        tt,
                        utils.find_alive_markers(
                            candidate_code, tt, marker_prefix, self.builder
                        ),
                    )
                    for tt in scenario.target_settings
                ]

                tester_alive_marker_list = [
                    (
                        tt,
                        utils.find_alive_markers(
                            candidate_code, tt, marker_prefix, self.builder
                        ),
                    )
                    for tt in scenario.attacker_settings
                ]
            except utils.CompileError:
                continue

            target_alive_markers = set()
            for _, marker_set in target_alive_marker_list:
                target_alive_markers.update(marker_set)

            # Extract reduce cases
            logging.debug("Extracting reduce cases...")
            for marker in target_alive_markers:
                good: list[utils.CompilerSetting] = []
                for good_setting, good_alive_markers in tester_alive_marker_list:
                    if (
                        marker not in good_alive_markers
                    ):  # i.e. the setting eliminated the call
                        good.append(good_setting)

                # Find bad cases
                if len(good) > 0:
                    good_opt_levels = [gs.opt_level for gs in good]
                    for bad_setting, bad_alive_markers in target_alive_marker_list:
                        # XXX: Here you can enable inter-opt_level comparison!
                        if (
                            marker in bad_alive_markers
                            and bad_setting.opt_level in good_opt_levels
                        ):  # i.e. the setting didn't eliminate the call
                            # Create reduce case
                            case = utils.Case(
                                code=candidate_code,
                                marker=marker,
                                bad_setting=bad_setting,
                                good_settings=good,
                                scenario=scenario,
                                reduced_code=None,
                                bisection=None,
                                path=None,
                            )
                            # TODO: Optimize interestingness test and document behaviour
                            try:
                                if self.chkr.is_interesting(case):
                                    logging.info(
                                        f"Try {self.try_counter}: Found case! LENGTH: {len(candidate_code)}"
                                    )
                                    return case
                            except utils.CompileError:
                                continue
            else:
                logging.debug(
                    f"Try {self.try_counter}: Found no case. Onto the next one!"
                )

    def _wrapper_interesting(self, queue: Queue[str], scenario: utils.Scenario) -> None:
        """Wrapper for generate_interesting_case for easier use
        with python multiprocessing.

        Args:
            queue (Queue): The multiprocessing queue to do IPC with.
            scenario (utils.Scenario): Scenario
        """
        logging.info("Starting worker...")
        while True:
            case = self.generate_interesting_case(scenario)
            queue.put(json.dumps(case.to_jsonable_dict()))

    def parallel_interesting_case_file(
        self,
        config: utils.NestedNamespace,
        scenario: utils.Scenario,
        processes: int,
        output_dir: os.PathLike[str],
        start_stop: Optional[bool] = False,
    ) -> Generator[Path, None, None]:
        """Generate interesting cases in parallel
        WARNING: If you use this method, you have to call `terminate_processes`

        Args:
            config (utils.NestedNamespace): THE config.
            scenario (utils.Scenario): Scenario.
            processes (int): Amount of jobs.
            output_dir (os.PathLike): Directory where to output the found cases.
            start_stop (Optional[bool]): Whether or not stop the processes when
                finding a case. This is useful when running a pipeline and thus
                the processing power is needed somewhere else.

        Returns:
            Generator[Path, None, None]: Interesting case generator giving paths.
        """
        gen = self.parallel_interesting_case(config, scenario, processes, start_stop)

        counter = 0
        while True:
            case = next(gen)
            h = hash(str(case))
            h = max(h, -h)
            path = Path(pjoin(output_dir, f"case_{counter:08}-{h:019}.tar"))
            logging.debug("Writing case to {path}...")
            case.to_file(path)
            yield path
            counter += 1

    def parallel_interesting_case(
        self,
        config: utils.NestedNamespace,
        scenario: utils.Scenario,
        processes: int,
        start_stop: Optional[bool] = False,
    ) -> Generator[utils.Case, None, None]:
        """Generate interesting cases in parallel
        WARNING: If you use this method, you have to call `terminate_processes`

        Args:
            config (utils.NestedNamespace): THE config.
            scenario (utils.Scenario): Scenario.
            processes (int): Amount of jobs.
            output_dir (os.PathLike): Directory where to output the found cases.
            start_stop (Optional[bool]): Whether or not stop the processes when
                finding a case. This is useful when running a pipeline and thus
                the processing power is needed somewhere else.

        Returns:
            Generator[utils.Case, None, None]: Interesting case generator giving Cases.
        """

        queue: Queue[str] = Queue()

        # Create processes
        self.procs = [
            Process(
                target=self._wrapper_interesting,
                args=(queue, scenario),
            )
            for _ in range(processes)
        ]

        # Start processes
        for p in self.procs:
            p.daemon = True
            p.start()

        # read queue
        while True:
            # TODO: handle process failure
            case_str: str = queue.get()

            case = utils.Case.from_jsonable_dict(config, json.loads(case_str))

            if start_stop:
                # Send processes to "sleep"
                logging.debug("Stopping workers...")
                for p in self.procs:
                    if p.pid is None:
                        continue
                    os.kill(p.pid, signal.SIGSTOP)
            yield case
            if start_stop:
                logging.debug("Restarting workers...")
                # Awake processes again for further search
                for p in self.procs:
                    if p.pid is None:
                        continue
                    os.kill(p.pid, signal.SIGCONT)

    def terminate_processes(self) -> None:
        for p in self.procs:
            if p.pid is None:
                continue
            # This is so cruel
            os.kill(p.pid, signal.SIGCONT)
            p.terminate()


if __name__ == "__main__":
    config, args = utils.get_config_and_parser(parsers.generator_parser())

    cores = args.cores

    patchdb = PatchDB(Path(config.patchdb))
    case_generator = CSmithCaseGenerator(config, patchdb, cores)

    if args.interesting:
        scenario = utils.Scenario([], [])
        if args.scenario:
            scenario = utils.Scenario.from_file(config, Path(args.scenario))

        if not args.scenario and args.targets is None:
            print(
                "--targets is required for --interesting if you don't specify a scenario"
            )
            exit(1)
        elif args.targets:
            target_settings = utils.get_compiler_settings(
                config, args.targets, default_opt_levels=args.targets_default_opt_levels
            )
            scenario.target_settings = target_settings

        if not args.scenario and args.additional_compilers is None:
            print(
                "--additional-compilers is required for --interesting if you don't specify a scenario"
            )
            exit(1)
        elif args.additional_compilers:
            additional_compilers = utils.get_compiler_settings(
                config,
                args.additional_compilers,
                default_opt_levels=args.additional_compilers_default_opt_levels,
            )

            scenario.attacker_settings = additional_compilers

        if args.output_directory is None:
            print("Missing output directory!")
            exit(1)
        else:
            output_dir = os.path.abspath(args.output_directory)
            os.makedirs(output_dir, exist_ok=True)

        if args.parallel is not None:
            amount_cases = args.amount if args.amount is not None else 0
            amount_processes = max(1, args.parallel)
            gen = case_generator.parallel_interesting_case_file(
                config=config,
                scenario=scenario,
                processes=amount_processes,
                output_dir=output_dir,
                start_stop=False,
            )
            if amount_cases == 0:
                while True:
                    print(next(gen))
            else:
                for i in range(amount_cases):
                    print(next(gen))

        else:
            print(case_generator.generate_interesting_case(scenario))
    else:
        # TODO
        print("Not implemented yet")

    # This is not needed here but I don't know why.
    case_generator.terminate_processes()
