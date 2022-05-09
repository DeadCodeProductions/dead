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
from dead_instrumenter.instrumenter import instrument_program

import checker
import parsers
import utils

from ccbuildercached import Repo, BuilderWithCache, BuildException, CompilerConfig, get_compiler_config, PatchDB

def run_csmith(csmith: str) -> str:
    """Generate random code with csmith.

    Args:
        csmith (str): Path to executable or name in $PATH to csmith.

    Returns:
        str: csmith generated program.
    """
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


def generate_file(
    config: utils.NestedNamespace, additional_flags: str
) -> tuple[str, str]:
    """Generate an instrumented csmith program.

    Args:
        config (utils.NestedNamespace): THE config
        additional_flags (str): Additional flags to use when
            compiling the program when checking.

    Returns:
        tuple[str, str]: Marker prefix and instrumented code.
    """
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
                if not checker.sanitize(
                    config.gcc.sane_version,
                    config.llvm.sane_version,
                    config.ccomp,
                    Path(ntf.name),
                    additional_flags,
                ):
                    continue
                logging.debug("Instrumenting candidate...")
                marker_prefix = instrument_program(
                    Path(ntf.name), [f"-I{config.csmith.include_path}"]
                )
                with open(ntf.name, "r") as f:
                    return marker_prefix, f.read()

            return marker_prefix, candidate
        except subprocess.TimeoutExpired:
            pass


class CSmithCaseGenerator:
    def __init__(
        self,
        config: utils.NestedNamespace,
        patchdb: PatchDB,
        cores: Optional[int] = None,
    ):
        self.config: utils.NestedNamespace = config
        self.builder: BuilderWithCache = BuilderWithCache(Path(config.cachedir), patchdb, cores)
        self.chkr: checker.Checker = checker.Checker(config, self.builder)
        self.procs: list[Process] = []
        self.try_counter: int = 0

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
            marker_prefix, candidate_code = generate_file(self.config, "")

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

    patchdb = PatchDB(config.patchdb)
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
