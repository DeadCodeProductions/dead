"""
Implements the core logic of Dead Code Elimination based Differential Testing

e.g., given a diopter.SourceProgram and two diopter.CompilationSettings

if case:= differential_test(program, setting1, setting2):
    #an interesting case has been found
"""

from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass
from enum import Enum

from dead_instrumenter.instrumenter import (
    DCEMarker,
    InstrumentedProgram,
    VRMarker,
    instrument_program,
)
from diopter.compiler import CompilationSetting, SourceProgram
from diopter.generator import CSmithGenerator
from diopter.sanitizer import Sanitizer

from dead.config import DeadConfig
from dead.progressbar import progressbar


@dataclass(frozen=True, kw_only=True)
class DifferentialTestingCase:
    """
    An instrumented program and two compilation settings, one of which cannot
    eliminate one or more markers that the other can (and vice versa).

    Attributes:
        program (InstrumentedProgram):
            the instrumented program whose markers are missed
            by one setting and eliminated by the other
        setting1 (CompilationSetting):
            the first compilation setting
        setting2 (CompilationSetting):
            the second compilation setting
        markers_only_eliminated_by_setting1 (tuple[DCEMarker | VRMarker, ...]):
            markers eliminated by setting1 and missed by setting2
        markers_only_eliminated_by_setting2 (tuple[DCEMarker | VRMarker, ...]):
            markers eliminated by setting2 and missed by setting1
    """

    program: InstrumentedProgram
    setting1: CompilationSetting
    setting2: CompilationSetting
    markers_only_eliminated_by_setting1: tuple[DCEMarker | VRMarker, ...]
    markers_only_eliminated_by_setting2: tuple[DCEMarker | VRMarker, ...]


class DifferentialTestingMode(Enum):
    """
    - Unidirectional: a marker is interesting only if the first
      compilation setting missed it and the second eliminated
    - Bidirectional: a marker is interesting if any of the compilation settings
      missed it and the other found it
    """

    Unidirectional = 0
    Bidirectional = 1


def differential_test(
    program: SourceProgram,
    setting1: CompilationSetting,
    setting2: CompilationSetting,
    testing_mode: DifferentialTestingMode = DifferentialTestingMode.Bidirectional,
) -> DifferentialTestingCase | None:
    """Instrument `program`, compile it with `setting1` and `setting2` and
    check if the set of eliminated markers differ.

    The program is instrumented with `dead_instrumenter.instrument` and compiled
    to assembly code using `setting1` and `setting2`. If different sets of
    markers are eliminated (and depending on `testing_direction`) a
    DifferentialTestingCase is found.

    Args:
        program (SourceProgram):
            the program that will be instrumented and tested
        setting1 (CompilationSetting):
            the first compilation setting with which to
            compile the instrumented program
        setting2 (CompilationSetting):
            the second compilation setting with which to
            compile the instrumented program
        testing_direction (DifferentialTestingDirection):
            whether to accept cases whether where any of the two settings miss
            at least one marker (Bidirectional), or cases where markers are
            eliminated by `setting1` and eliminated by `setting2`

    Returns:
        (DifferentialTestingCase | None):
            interesting case if found
    """

    # TODO: here we can add additional functionality, e.g.,
    # - Use VR Markers as well
    # - Disable markers, iter

    # Instrument program
    try:
        instr_program = instrument_program(program)
    except AssertionError:
        return None

    # Find markers exclusively eliminated by each case
    dead_markers1 = set(instr_program.find_dead_markers(setting1))
    dead_markers2 = set(instr_program.find_dead_markers(setting2))
    only_eliminated_by_setting1 = tuple(dead_markers1 - dead_markers2)
    only_eliminated_by_setting2 = tuple(dead_markers2 - dead_markers1)

    # Is the candidate interesting?
    if not only_eliminated_by_setting1 and not only_eliminated_by_setting2:
        return None
    if testing_mode == DifferentialTestingMode.Unidirectional:
        if not only_eliminated_by_setting1:
            return None
    else:
        assert testing_mode == DifferentialTestingMode.Bidirectional

    return DifferentialTestingCase(
        program=instr_program,
        setting1=setting1,
        setting2=setting2,
        markers_only_eliminated_by_setting1=only_eliminated_by_setting1,
        markers_only_eliminated_by_setting2=only_eliminated_by_setting2,
    )


def generate_and_test(
    setting1: CompilationSetting,
    setting2: CompilationSetting,
    testing_mode: DifferentialTestingMode,
    number_candidates: int,
    jobs: int,
) -> list[DifferentialTestingCase]:
    """Generate cases in parallel and check them with `differential_test`

    Generate cases in parallel via `diopter.generator.CSmithGenerator` and test
    them in parallel with `differential_test` with `setting1` and `setting2` to
    find cases where one setting can eliminate markers that the other cannot.


    Args:
        setting1 (CompilationSetting):
            see the corresponding documentation of `differential_test`
        setting2 (CompilationSetting):
            see the corresponding documentation of `differential_test`
        testing_direction (DifferentialTestingDirection):
            see the corresponding documentation of `differential_test`
        number_candidates (int):
            how many candidates to generate and test
        jobs (int):
            how many parallel jobs to use

    Returns:
        list[DifferentialTestingCase]:
            generated cases found to be interesting by `differential_test`

    """

    config = DeadConfig.get_config()
    san = Sanitizer(gcc=config.gcc, clang=config.clang, ccomp=config.ccomp)
    gen = CSmithGenerator(
        san, csmith=str(config.csmith), include_path=str(config.csmith_include_path)
    )

    cases = []
    with ProcessPoolExecutor(jobs) as executor:
        diff_testing_jobs = []

        # Generate candidates
        for candidate_fut in progressbar(
            as_completed(gen.generate_programs_parallel(number_candidates, executor)),
            desc="Generating candidates",
            total=number_candidates,
        ):
            diff_testing_jobs.append(
                executor.submit(
                    differential_test,
                    candidate_fut.result(),
                    setting1,
                    setting2,
                    testing_mode,
                )
            )

        # Test candidates
        for diff_testing_job in progressbar(
            diff_testing_jobs,
            desc="Testing candidates",
            total=number_candidates,
        ):
            case = diff_testing_job.result()
            if not case:
                continue
            cases.append(case)
    return cases
