from typing import Optional

from diopter.bisector import Bisector, BisectionCallback, BisectionException
from diopter.compiler import CompilationSetting, CompilerExe

import ccbuilder

from dead.utils import RegressionCase, DeadConfig


class DeadBisectionCallback(BisectionCallback):
    # TODO: this should operate directly on a case
    def __init__(
        self,
        case: RegressionCase,
        bldr: ccbuilder.Builder,
    ):
        self.case = case
        self.bldr = bldr

    def check(self, commit: ccbuilder.Commit) -> Optional[bool]:
        try:
            return self.case.marker in self.case.program.find_alive_markers(
                self.case.bad_setting.with_revision(commit, self.bldr)
            )
        except Exception:
            return None


def bisect_case(
    case_: RegressionCase,
    bisector: Bisector,
    builder: ccbuilder.Builder,
    force: bool = False,
) -> bool:
    if case_.bisection and not force:
        return True

    callback = DeadBisectionCallback(
        case_,
        builder,
    )

    if not callback.check(case_.bad_setting.compiler.revision):
        raise BisectionException("The case marker is not interesting")

    # TODO: pass number of jobs and logfile
    bisection_commit = bisector.bisect(
        callback,
        case_.bad_setting.compiler.revision,
        case_.good_setting.compiler.revision,
        case_.bad_setting.compiler.project,
        DeadConfig.get_config().gcc_repo
        if case_.bad_setting.compiler.project == ccbuilder.CompilerProject.GCC
        else DeadConfig.get_config().llvm_repo,  # there should be code somewhere for this
    )

    if not bisection_commit:
        return False

    case_.bisection = bisection_commit

    return True
