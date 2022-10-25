from dataclasses import replace

from diopter.sanitizer import Sanitizer
from diopter.compiler import CompilationSetting
from diopter.reducer import ReductionCallback, Reducer
from diopter.preprocessor import preprocess_csmith_program

from dead_instrumenter.instrumenter import InstrumentedProgram

from dead.checker import find_interesting_markers
from dead.utils import DeadConfig, RegressionCase


class DeadReductionCallback(ReductionCallback):
    # TODO: this should operate directly on a case
    def __init__(self, case_: RegressionCase, sanitizer: Sanitizer):
        self.case = case_
        self.sanitizer = sanitizer

    def test(self, code: str) -> bool:
        # TODO: check bisection as well
        # TODO: globalize

        program = replace(self.case.program, code=code)

        if not self.sanitizer.sanitize(program):
            return False

        return self.case.marker in find_interesting_markers(
            program, self.case.bad_setting, self.case.good_setting
        )


def reduce_case(
    case_: RegressionCase,
    reducer: Reducer,
    sanitizer: Sanitizer,
    force: bool = False,
    preprocess: bool = True,
) -> bool:
    if case_.reduced_code and not force:
        return True
    if preprocess:
        pprogram = preprocess_csmith_program(case_.program, DeadConfig.get_config().gcc)
        if not pprogram:
            # XXX: log something here?
            return False
        code = pprogram.code
    else:
        code = case_.program.code
    rcallback = DeadReductionCallback(case_, sanitizer)
    assert rcallback.test(code)
    # TODO: pass number of jobs and logfile
    reduced_code = reducer.reduce(code, rcallback)

    if not reduced_code:
        return False

    case_.reduced_code = reduced_code

    return True
