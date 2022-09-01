from diopter.compiler import CompilationSetting
from diopter.reducer import ReductionCallback, Reducer
from diopter.preprocessor import preprocess_csmith_code

from dead.checker import Checker
from dead.utils import DeadConfig, RegressionCase


class DeadReductionCallback(ReductionCallback):
    # TODO: this should operate directly on a case
    def __init__(
        self,
        marker: str,
        bad_setting: CompilationSetting,
        good_setting: CompilationSetting,
        checker: Checker,
    ):
        self.marker = marker
        self.bad_setting = bad_setting
        self.good_setting = good_setting
        self.checker = checker

    def test(self, code: str) -> bool:
        # TODO: check bisection as well
        return self.checker.is_interesting_marker(
            code,
            self.marker,
            self.bad_setting,
            self.good_setting,
            preprocess=False,
            make_globals_static=True,
        )


def reduce_case(
    case_: RegressionCase,
    reducer: Reducer,
    checker: Checker,
    force: bool = False,
    preprocess: bool = True,
) -> bool:
    if case_.reduced_code and not force:
        return True
    if preprocess:
        pcode = preprocess_csmith_code(
            case_.code,
            str(DeadConfig.get_config().gcc.exe),
            [f"-I{DeadConfig.get_config().csmith_include_path}"],
        )
        if not pcode:
            # XXX: log something here?
            return False
    else:
        pcode = case_.code
    rcallback = DeadReductionCallback(
        case_.marker, case_.bad_setting, case_.good_setting, checker
    )
    assert rcallback.test(pcode)
    # TODO: pass number of jobs and logfile
    reduced_code = reducer.reduce(pcode, rcallback)

    if not reduced_code:
        return False

    case_.reduced_code = reduced_code

    return True
