import copy
import functools
import logging
import subprocess
from typing import Optional

from ccbuilder import Builder, Commit

import checker
import utils


def test_bisection(
    new_commit: Commit, chkrncse: tuple[checker.Checker, utils.Case], bldr: Builder
) -> Optional[bool]:
    chkr, cse = chkrncse
    case_cpy = copy.deepcopy(cse)
    case_cpy.bad_setting.rev = new_commit
    try:
        if case_cpy.reduced_code:
            case_cpy.code = case_cpy.reduced_code
            return chkr.is_interesting(case_cpy, preprocess=False)
        else:
            return chkr.is_interesting(case_cpy, preprocess=True)
    except subprocess.CalledProcessError as e:
        logging.warning(f"{e}")
    return None
