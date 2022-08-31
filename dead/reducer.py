from diopter.compiler import CompilationSetting
from diopter.reducer import ReductionCallback, Reducer
from diopter.preprocessor import preprocess_csmith_code

from dead.checker import Checker
from dead.utils import DeadConfig, Case


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
            code, self.marker, self.bad_setting, [self.good_setting], preprocess=False
        )


def reduce_case(
    case_: Case,
    reducer: Reducer,
    checker: Checker,
    force: bool = False,
    preprocess: bool = True,
) -> bool:
    if case_.reduced_code and not force:
        return True
    # TODO: drop this once we/if we switch to RegressionCase
    def get_good_setting_for_reduction() -> CompilationSetting:
        for setting in case_.good_settings:
            if (
                setting.opt_level == case_.bad_setting.opt_level
                and setting.compiler.project == case_.bad_setting.compiler.project
            ):
                return setting
        assert False, "reduction_case: this is not a regression"

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
        case_.marker, case_.bad_setting, get_good_setting_for_reduction(), checker
    )
    assert rcallback.test(pcode)
    # TODO: pass number of jobs and logfile
    reduced_code = reducer.reduce(pcode, rcallback)

    if not reduced_code:
        return False

    case_.reduced_code = reduced_code

    return True
