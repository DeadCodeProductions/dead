import tempfile
from collections import defaultdict
from multiprocessing import cpu_count
from concurrent.futures import ProcessPoolExecutor, as_completed, Future, wait
from pathlib import Path

from dead.utils import Scenario, RegressionCase, DeadConfig
from dead.checker import Checker

from dead_instrumenter.instrumenter import instrument_program
from diopter.generator import CSmithGenerator
from diopter.compiler import CompilationSetting

from tqdm import tqdm  # type:ignore


class DeadCodeGenerator(CSmithGenerator):
    def generate_code(self) -> str:
        csmith_code = super().generate_code()
        with tempfile.NamedTemporaryFile(suffix=".c") as tfile:
            with open(tfile.name, "w") as f:
                f.write(csmith_code)
            instrument_program(
                Path(tfile.name),
                flags=[f"-I{DeadConfig.get_config().csmith_include_path}"],
            )
            with open(tfile.name, "r") as f:
                return f.read()


# TODO: Fold this into the generator, check PR#42
def extract_interesting_cases_from_generated(
    checker: Checker, candidate: str, scenario: Scenario
) -> list[RegressionCase]:
    # TODO:the Checker should check against a scenario, this is suboptimal
    cases: list[RegressionCase] = []
    for bad_setting in scenario.target_settings:
        for marker, good_settings in checker.find_interesting_markers(
            candidate, bad_setting, scenario.attacker_settings
        ):
            for good_setting in good_settings:
                if (
                    bad_setting.compiler.project == good_setting.compiler.project
                    and bad_setting.opt_level == good_setting.opt_level
                ):
                    cases.append(
                        RegressionCase(
                            candidate,
                            marker,
                            bad_setting,
                            good_setting,
                            None,
                            None,
                        )
                    )
    return cases


def generate_interesting_cases(
    scenario: Scenario, jobs: int = cpu_count(), chunk: int = 256
) -> list[RegressionCase]:
    config = DeadConfig.get_config()
    checker = Checker(config.llvm, config.gcc, config.ccc, config.ccomp)
    gnrtr = DeadCodeGenerator()
    interesting_candidates: list[RegressionCase] = []

    while len(interesting_candidates) == 0:
        interesting_candidate_futures = []
        with ProcessPoolExecutor(jobs) as p:
            for candidate in tqdm(
                gnrtr.generate_code_parallel(chunk, p),
                desc="Generating candidates",
                total=chunk,
                dynamic_ncols=True,
            ):
                interesting_candidate_futures.append(
                    p.submit(
                        extract_interesting_cases_from_generated,
                        checker,
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
