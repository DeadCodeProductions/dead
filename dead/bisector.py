from typing import Optional

from diopter.bisector import Bisector, BisectionCallback
from diopter.compiler import CompilationSetting, CompilerExe

import ccbuilder

from dead.checker import find_alive_markers
from dead.utils import RegressionCase, DeadConfig


# TODO: move this to diopter.CompilationSetting.with_commit
def get_setting_with_commit(
    commit: ccbuilder.Commit, setting: CompilationSetting, bldr: ccbuilder.Builder
) -> CompilationSetting:
    return CompilationSetting(
        CompilerExe(
            setting.compiler.project,
            bldr.build(setting.compiler.project, commit, True),
            commit,
        ),
        setting.opt_level,
        setting.flags,
        setting.include_paths,
        setting.system_include_paths,
    )


class DeadBisectionCallback(BisectionCallback):
    # TODO: this should operate directly on a case
    def __init__(
        self,
        code: str,
        setting: CompilationSetting,
        marker: str,
        bldr: ccbuilder.Builder,
    ):
        self.code = code
        self.setting = setting
        self.marker = marker
        self.bldr = bldr

    def check(self, commit: ccbuilder.Commit) -> Optional[bool]:
        # try:
        return self.marker in find_alive_markers(
            self.code,
            get_setting_with_commit(commit, self.setting, self.bldr),
            "DCEMarker",
        )
        # except Exception as e:
        # logging.warning(f"Test failed with: '{e}'. Continuing...")
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
        case_.code,
        case_.bad_setting,
        case_.marker,
        builder,
    )
    assert callback.check(case_.bad_setting.compiler.revision)

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
