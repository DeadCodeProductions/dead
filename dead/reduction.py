"""
Implements the reduction logic used for generating minimal test cases

e.g., given a DifferentialTestingCase and a target marker, which should
still be present in the minimal case, it produces a Reduction

reduced_case = reduce_case( case, target_marker, jobs=128)

reduce_case.reduced_program # the reduced program

"""

from dataclasses import dataclass

from callchain_checker.callchain_checker import callchain_exists
from dead_instrumenter.instrumenter import (
    DCEMarker,
    InstrumentedProgram,
    VRMarker,
    annotate_with_static,
)
from diopter.compiler import CompilationSetting, SourceProgram
from diopter.reducer import Reducer, ReductionCallback
from diopter.sanitizer import Sanitizer

from dead.config import DeadConfig
from dead.differential_testing import DifferentialTestingCase


@dataclass(frozen=True, kw_only=True)
class DeadReductionCallback(ReductionCallback):
    """Callback implementing the interestingness test for creduce.

    Attributes:
        bad_setting (CompilationSetting):
            the setting that should misse the `target_marker`
        good_setting (CompilationSetting):
            the setting that should eliminate the `target_marker`
        target_marker (VRMarker | DCEMarker):
            the marker targeted by the reduction
        sanitizer (Sanitizer):
            sanitizer used for checking that the reduced program is valid
    """

    bad_setting: CompilationSetting
    good_setting: CompilationSetting
    target_marker: DCEMarker | VRMarker
    sanitizer: Sanitizer

    def test(self, program: SourceProgram) -> bool:
        """Reduction test
        Args:
            program (SourceProgram):
                the reduced program that is being checked
        Returns:
            bool:
                whether the reduced program should be kept
        """
        assert isinstance(program, InstrumentedProgram)

        # Check that the marker can potentially be called from main
        if not callchain_exists(program, "main", self.target_marker.to_macro()):
            return False

        # creduce may drop static annotations, add them back
        program = annotate_with_static(program)
        assert isinstance(program, InstrumentedProgram)

        # The bad setting should miss the marker
        if self.target_marker in program.find_dead_markers(self.bad_setting):
            return False

        # The good setting should eliminate the marker
        if self.target_marker not in program.find_dead_markers(self.good_setting):
            return False

        # Sanitize
        return bool(
            self.sanitizer.sanitize(program.disable_remaining_markers(), debug=False)
        )


@dataclass(frozen=True, kw_only=True)
class Reduction:
    """A reduction represents a differential testing case and a reduced
    program containing the target marker that is missed by the bad setting
    but is eliminated by the good setting.

    Attributes:
        case (DifferentialTestingCase):
            the case in which the `target_marker` is eliminated by
            `good_setting` but missed by `bad_setting`
        reduced_program (InstrumentedProgram):
            a reduced version of `case.program` that still contains the
            `target_marker` which is eliminated by `good_setting` and
            missed by `bad_setting`
        target_marker (VRMarker | DCEMarker):
            the marker targeted by the reduction
        bad_setting (CompilationSetting):
            the setting that misses the `target_marker` both
            in `case.program` and in `reduced_program`
        good_setting (CompilationSetting):
            the setting that eliminates the `target_marker` both
            in `case.program` and in `reduced_program`
    """

    case: DifferentialTestingCase
    reduced_program: InstrumentedProgram
    target_marker: VRMarker | DCEMarker
    bad_setting: CompilationSetting
    good_setting: CompilationSetting


def reduce_case(
    case: DifferentialTestingCase, target_marker: DCEMarker | VRMarker, jobs: int
) -> Reduction:
    """Reduces `case.program` such that `target_marker` is missed by
    case.setting1 or case.setting2 and missed by the other.

    Args:
        case (DifferentialTestingCase):
            the case to be reduced
        target_marker (DCEMarker | VRMarker):
            the marker that will still be present in the reduced program
        jobs (int):
            how many parallel jobs to use

    Returns:
        Reduction:
            reduced case containing `target_marker`
    """

    # Figure out which setting misses and which eliminates the marker
    if target_marker in case.markers_only_eliminated_by_setting1:
        good_setting = case.setting1
        bad_setting = case.setting2
    else:
        assert target_marker in case.markers_only_eliminated_by_setting2
        good_setting = case.setting2
        bad_setting = case.setting1

    # Setup reducer and sanitizer
    config = DeadConfig.get_config()
    san = Sanitizer(gcc=config.gcc, clang=config.clang, ccomp=config.ccomp)
    reducer = Reducer(str(config.creduce))

    # Reduce
    reduced_program = reducer.reduce(
        case.program,
        DeadReductionCallback(
            bad_setting=bad_setting,
            good_setting=good_setting,
            sanitizer=san,
            target_marker=target_marker,
        ),
        jobs=jobs,
        debug=False,
    )
    assert isinstance(reduced_program, InstrumentedProgram)
    reduced_program = annotate_with_static(reduced_program)
    assert isinstance(reduced_program, InstrumentedProgram)
    return Reduction(
        case=case,
        reduced_program=reduced_program,
        target_marker=target_marker,
        bad_setting=bad_setting,
        good_setting=good_setting,
    )
