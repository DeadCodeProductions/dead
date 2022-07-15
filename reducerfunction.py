import copy
import json
import logging
import multiprocessing
import os
import random
import shutil
import time
from pathlib import Path
from typing import Any, Optional

import ccbuilder
import diopter

import preprocessing
import utils


def reduce_file(
    config: utils.NestedNamespace,
    bldr: ccbuilder.Builder,
    file: Path,
    force: bool = False,
    jobs: int = multiprocessing.cpu_count(),
) -> bool:
    """Reduce a case given in the .tar format.
    Interface for `reduced_code`.

    Args:
        file (Path): Path to .tar case.
        force (bool): Force a reduction (even if the case is already reduced).
    Returns:
        bool: If the reduction was successful.
    """
    case = utils.Case.from_file(config, file)

    if reduce_case(config=config, bldr=bldr, case=case, force=force, jobs=jobs):
        case.to_file(file)
        return True
    return False


def reduce_case(
    config: utils.NestedNamespace,
    bldr: ccbuilder.Builder,
    case: utils.Case,
    force: bool = False,
    jobs: int = multiprocessing.cpu_count(),
) -> bool:
    """Reduce a case.

    Args:
        case (utils.Case): Case to reduce.
        force (bool): Force a reduction (even if the case is already reduced).

    Returns:
        bool: If the reduction was successful.
    """
    if not force and case.reduced_code:

        return True

    case.reduced_code = reduce_code(
        config=config,
        bldr=bldr,
        code=case.code,
        marker=case.marker,
        bad_setting=case.bad_setting,
        good_settings=case.good_settings,
        bisection=case.bisection,
        jobs=jobs,
    )
    return bool(case.reduced_code)


def reduce_code(
    config: utils.NestedNamespace,
    bldr: ccbuilder.Builder,
    code: str,
    marker: str,
    bad_setting: utils.CompilerSetting,
    good_settings: list[utils.CompilerSetting],
    bisection: Optional[str] = None,
    preprocess: bool = True,
    jobs: Optional[int] = None,
) -> Optional[str]:
    """Reduce given code w.r.t. `marker`

    Args:
        code (str):
        marker (str): Marker which exhibits the interesting behaviour.
        bad_setting (utils.CompilerSetting): Setting which can not eliminate the marker.
        good_settings (list[utils.CompilerSetting]): Settings which can eliminate the marker.
        bisection (Optional[str]): if present the reducer will also check for the bisection
        preprocess (bool): Whether or not to run the code through preprocessing.

    Returns:
        Optional[str]: Reduced code, if successful.
    """

    jobs = jobs if jobs else bldr.jobs

    bad_settings = [bad_setting]
    if bisection:
        bad_settings.append(copy.deepcopy(bad_setting))
        bad_settings[-1].rev = bisection
        repo = bad_setting.repo
        good_settings = good_settings + [copy.deepcopy(bad_setting)]
        good_settings[-1].rev = repo.rev_to_commit(f"{bisection}~")

    # creduce likes to kill unfinished processes with SIGKILL
    # so they can't clean up after themselves.
    # Setting a temporary temporary directory for creduce to be able to clean
    # up everything
    with diopter.utils.TempDirEnv() as tmpdir:
        # preprocess file
        if preprocess:
            tmp = preprocessing.preprocess_csmith_code(
                code,
                utils.get_marker_prefix(marker),
                bad_setting,
                bldr,
            )
            # Preprocesssing may fail
            pp_code = tmp if tmp else code

        else:
            pp_code = code

        pp_code_path = tmpdir / "code_pp.c"
        with open(pp_code_path, "w") as f:
            f.write(pp_code)

        int_settings: dict[str, Any] = {}
        int_settings["bad_settings"] = [bs.to_jsonable_dict() for bs in bad_settings]
        int_settings["good_settings"] = [gs.to_jsonable_dict() for gs in good_settings]

        script = (
            "#/bin/sh\n"
            "TMPD=$(mktemp -d)\n"
            "trap '{ rm -rf \"$TMPD\"; }' INT TERM EXIT\n"
            "timeout 15 "
            f"{Path(__file__).parent.resolve()}/checker.py"
            f" --dont-preprocess"
            f" --config {config.config_path}"
            f" --marker {marker}"
            f" --interesting-settings '{json.dumps(int_settings)}'"
            f" --file code.c"
        )

        rdcr = diopter.reducer.Reducer()

        current_time = time.strftime("%Y%m%d-%H%M%S")
        build_log_path = (
            Path(config.logdir) / f"{current_time}-creduce-{random.randint(0,1000)}.log"
        )
        build_log_path.touch()
        # Set permissions of logfile
        shutil.chown(build_log_path, group=config.cache_group)
        os.chmod(build_log_path, 0o660)
        logging.info(f"creduce logfile at {build_log_path}")
        with open(build_log_path, "a") as build_log:
            return rdcr.reduce(pp_code, script, jobs=jobs, log_file=build_log)
