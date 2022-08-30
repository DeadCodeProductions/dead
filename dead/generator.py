import tempfile
from collections import defaultdict
from multiprocessing import cpu_count
from concurrent.futures import ProcessPoolExecutor, as_completed, Future, wait
from pathlib import Path

from dead.utils import Scenario, Case, DeadConfig
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
) -> list[Case]:
    # TODO:the Checker should check against a scenario, this is suboptimal
    cases: list[Case] = []
    for bad_setting in scenario.target_settings:
        markers = checker.find_interesting_markers(
            candidate, bad_setting, scenario.attacker_settings
        )
        # TODO: the result is a single good and single bad setting, both should be multiple ones, a subset of the scenario
        marker_to_settings = defaultdict(list)
        for marker, good_setting in markers:
            marker_to_settings[marker].extend(good_setting)
        for case_marker, good_settings in marker_to_settings.items():
            good_opt_levels = [setting.opt_level for setting in good_settings]
            if not bad_setting.opt_level in good_opt_levels:
                continue
            cases.append(
                Case(
                    candidate,
                    case_marker,
                    bad_setting,
                    good_settings,
                    scenario,
                    None,
                    None,
                )
            )
            # XXX: here instead of dropping we could look for primary markers
            break

    return cases


def generate_interesting_cases(
    scenario: Scenario, jobs: int = cpu_count(), chunk: int = 256
) -> list[Case]:
    config = DeadConfig.get_config()
    checker = Checker(config.llvm, config.gcc, config.ccc, config.ccomp)
    gnrtr = DeadCodeGenerator()
    interesting_candidates: list[Case] = []

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
