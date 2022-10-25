import tempfile
from collections import defaultdict
from multiprocessing import cpu_count
from concurrent.futures import ProcessPoolExecutor, as_completed, Future, wait
from pathlib import Path

from dead.utils import Scenario, RegressionCase, DeadConfig
from dead.checker import find_interesting_markers

from dead_instrumenter.instrumenter import instrument_program

from diopter.generator import CSmithGenerator
from diopter.compiler import CompilationSetting, SourceProgram
from diopter.sanitizer import Sanitizer

from tqdm import tqdm  # type:ignore


def extract_regression_cases_from_candidate(
    candidate: SourceProgram, scenario: Scenario
) -> list[RegressionCase]:
    # XXX: we need a RegressionScenario that is guaranteed to have attackers
    # and targets with the same opt_level

    # TODO:the Checker should check against a scenario, this is suboptimal
    # TODO: error checking and exception handling
    icandidate = instrument_program(candidate)
    cases: list[RegressionCase] = []
    for bad_setting in scenario.target_settings:
        for good_setting in scenario.attacker_settings:
            if bad_setting.opt_level != good_setting.opt_level:
                continue
            for marker in find_interesting_markers(
                icandidate, bad_setting, good_setting
            ):
                cases.append(
                    RegressionCase(icandidate, marker, bad_setting, good_setting)
                )
    return cases


def generate_regression_cases(
    scenario: Scenario, jobs: int = cpu_count(), chunk: int = 256
) -> list[RegressionCase]:
    config = DeadConfig.get_config()
    sanitizer = Sanitizer(ccomp=config.ccomp, gcc=config.gcc, clang=config.llvm)
    gnrtr = CSmithGenerator(sanitizer, include_path=config.csmith_include_path)
    interesting_candidates: list[RegressionCase] = []

    while len(interesting_candidates) == 0:
        interesting_candidate_futures = []
        with ProcessPoolExecutor(jobs) as p:
            for candidate in tqdm(
                gnrtr.generate_programs_parallel(chunk, p),
                desc="Generating candidates",
                total=chunk,
                dynamic_ncols=True,
            ):
                interesting_candidate_futures.append(
                    p.submit(
                        extract_regression_cases_from_candidate,
                        candidate,
                        scenario,
                    )
                )

            print("Filtering for interesting candidates")
            for fut in tqdm(
                as_completed(interesting_candidate_futures),
                desc="Filtering candidates",
                total=chunk,
                dynamic_ncols=True,
            ):
                r = fut.result()
                if not r:
                    continue
                interesting_candidates.extend(r)
    return interesting_candidates
