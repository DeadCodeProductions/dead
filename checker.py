#!/usr/bin/env python3

import copy
import logging
import re
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

from ccbuilder import Builder, PatchDB, Repo
from dead_instrumenter.instrumenter import annotate_with_static
from diopter import sanitizer

import parsers
import preprocessing
import utils

# ==================== Checker ====================


class Checker:
    def __init__(self, config: utils.NestedNamespace, bldr: Builder):
        self.config = config
        self.builder = bldr
        return

    def is_interesting_wrt_marker(self, case: utils.Case) -> bool:
        """Checks if the marker is eliminated by all good compilers/setting
        and not eliminated by the bad compiler/setting.

        Args:
            case (utils.Case): Case to check.

        Returns:
            bool: True if the maker is not eliminated by the bad setting and
                eliminated by all good settings.

        Raises:
            builder.CompileError: Finding alive markers may fail.
        """
        # Checks if the bad_setting does include the marker and
        # all the good settings do not.

        marker_prefix = utils.get_marker_prefix(case.marker)
        found_in_bad = utils.find_alive_markers(
            case.code, case.bad_setting, marker_prefix, self.builder
        )
        uninteresting = False
        if case.marker not in found_in_bad:
            return False
        for good_setting in case.good_settings:
            found_in_good = utils.find_alive_markers(
                case.code, good_setting, marker_prefix, self.builder
            )
            if case.marker in found_in_good:
                uninteresting = True
                break
        return not uninteresting

    def is_interesting_wrt_ccc(self, case: utils.Case) -> bool:
        """Check if there is a call chain between main and the marker.

        Args:
            case (utils.Case): Case to check.

        Returns:
            bool: If there is a call chain between main and the marker
        """
        with tempfile.NamedTemporaryFile(suffix=".c") as tf:
            with open(tf.name, "w") as f:
                f.write(case.code)

            # TODO: Handle include_paths better
            include_paths = utils.find_include_paths(
                self.config.llvm.sane_version, tf.name, case.bad_setting.get_flag_str()
            )
            cmd = [self.config.ccc, tf.name, "--from=main", f"--to={case.marker}"]

            for path in include_paths:
                cmd.append(f"--extra-arg=-isystem{path}")
            try:
                result = utils.run_cmd(cmd, timeout=8)
                return (
                    f"call chain exists between main -> {case.marker}".strip()
                    == result.strip()
                )
            except subprocess.CalledProcessError:
                logging.debug("CCC failed")
                return False
            except subprocess.TimeoutExpired:
                logging.debug("CCC timed out")
                return False

    def is_interesting_with_static_globals(self, case: utils.Case) -> bool:
        """Checks if the given case is still interesting, even when making all
        variables and functions static.

        Args:
            case (utils.Case): The case to check

        Returns:
            bool: If the case is interesting when using static globals

        Raises:
            builder.CompileError: Getting the assembly may fail.
        """

        with tempfile.NamedTemporaryFile(suffix=".c") as tf:
            with open(tf.name, "w") as new_cfile:
                print(case.code, file=new_cfile)

            # TODO: Handle include_paths better
            annotate_with_static(Path(tf.name), case.bad_setting.get_flag_cmd())

            with open(tf.name, "r") as annotated_file:
                static_code = annotated_file.read()

            asm_bad = utils.get_asm_str(static_code, case.bad_setting, self.builder)
            uninteresting = False
            if case.marker not in asm_bad:
                uninteresting = True
            for good_setting in case.good_settings:
                asm_good = utils.get_asm_str(static_code, good_setting, self.builder)
                if case.marker in asm_good:
                    uninteresting = True
                    break
            return not uninteresting

    def _emtpy_marker_code_str(self, case: utils.Case) -> str:
        marker_prefix = utils.get_marker_prefix(case.marker)
        p = re.compile(rf"void {marker_prefix}(.*)\(void\);(.*)")
        empty_body_code = ""
        for line in case.code.split("\n"):
            m = p.match(line)
            if m:
                empty_body_code += (
                    "\n"
                    + rf"void {marker_prefix}{m.group(1)}(void){{}}"
                    + "\n"
                    + rf"{m.group(2)}"
                )
            else:
                empty_body_code += f"\n{line}"

        return empty_body_code

    def is_interesting_with_empty_marker_bodies(self, case: utils.Case) -> bool:
        """Check if `case.code` does not exhibit undefined behaviour,
        compile errors or makes CompCert unhappy.
        To compile, all markers need to get an empty body, thus the name.

        Args:
            case (utils.Case): Case to check

        Returns:
            bool: True if the code passes the 'sanity-check'
        """

        empty_body_code = self._emtpy_marker_code_str(case)

        with tempfile.NamedTemporaryFile(suffix=".c") as tf:
            with open(tf.name, "w") as f:
                f.write(empty_body_code)

            return sanitizer.sanitize_file(
                self.config.gcc.sane_version,
                self.config.llvm.sane_version,
                self.config.ccomp,
                Path(tf.name),
                case.bad_setting.get_flag_str(),
            )

    def is_interesting(self, case: utils.Case, preprocess: bool = True) -> bool:
        """Check if a code passes all the 'interestingness'-checks.
        Preprocesses code by default to prevent surprises when preprocessing
        later.

        Args:
            self:
            case (utils.Case): Case to check.
            preprocess (bool): Whether or not to preprocess the code

        Returns:
            bool: True if the case passes all 'interestingness'-checks

        Raises:
            builder.CompileError
        """
        # TODO: Optimization potential. Less calls to clang etc.
        # when tests are combined.

        if preprocess:
            code_pp = preprocessing.preprocess_csmith_code(
                case.code,
                utils.get_marker_prefix(case.marker),
                case.bad_setting,
                self.builder,
            )
            case_cpy = copy.deepcopy(case)
            if code_pp:
                case_cpy.code = code_pp
            case = case_cpy
        # Taking advantage of shortciruit logic
        return (
            self.is_interesting_wrt_marker(case)
            and self.is_interesting_wrt_ccc(case)
            and self.is_interesting_with_static_globals(case)
            and self.is_interesting_with_empty_marker_bodies(case)
        )


def copy_flag(
    frm: utils.CompilerSetting, to: list[utils.CompilerSetting]
) -> list[utils.CompilerSetting]:
    res: list[utils.CompilerSetting] = []
    for setting in to:
        cpy = copy.deepcopy(setting)
        cpy.additional_flags = frm.additional_flags
        res.append(cpy)
    return res


def override_bad(
    case: utils.Case, override_settings: list[utils.CompilerSetting]
) -> list[utils.Case]:
    res = []
    bsettings = copy_flag(case.bad_setting, override_settings)
    for s in bsettings:
        cpy = copy.deepcopy(case)
        cpy.bad_setting = s
        res.append(cpy)
    return res


def override_good(
    case: utils.Case, override_settings: list[utils.CompilerSetting]
) -> utils.Case:
    gsettings = copy_flag(case.good_settings[0], override_settings)
    cpy = copy.deepcopy(case)
    cpy.good_settings = gsettings
    return cpy


if __name__ == "__main__":
    config, args = utils.get_config_and_parser(parsers.checker_parser())

    patchdb = PatchDB(Path(config.patchdb))
    gcc_repo = Repo.gcc_repo(config.gcc.repo)
    llvm_repo = Repo.llvm_repo(config.llvm.repo)
    bldr = Builder(
        cache_prefix=Path(config.cachedir),
        gcc_repo=gcc_repo,
        llvm_repo=llvm_repo,
        patchdb=patchdb,
        jobs=args.cores,
        logdir=Path(config.logdir),
    )
    chkr = Checker(config, bldr)

    file = Path(args.file)

    bad_settings = []
    good_settings = []

    if args.check_pp:
        file = Path(args.file).absolute()
        case = utils.Case.from_file(config, file)
        # preprocess file
        pp_code = preprocessing.preprocess_csmith_code(
            case.code,
            utils.get_marker_prefix(case.marker),
            case.bad_setting,
            bldr,
        )

        if pp_code:
            case.code = pp_code
        else:
            print("Could not preprocess code. Exiting")
            exit(1)
        # Taking advantage of shortciruit logic
        a = chkr.is_interesting_wrt_marker(case)
        b = chkr.is_interesting_wrt_ccc(case)
        c = chkr.is_interesting_with_static_globals(case)
        d = chkr.is_interesting_with_empty_marker_bodies(case)
        print(f"Marker:\t{a}")
        print(f"CCC:\t{b}")
        print(f"Static:\t{c}")
        print(f"Empty:\t{d}")
        if not all((a, b, c, d)):
            exit(1)
        exit(0)

    if args.scenario:
        scenario = utils.Scenario.from_file(config, Path(args.scenario))
        bad_settings = scenario.target_settings
        good_settings = scenario.attacker_settings
    elif args.interesting_settings:
        bad_settings, good_settings = utils.get_interesting_settings(
            config, args.interesting_settings
        )

    if args.bad_settings:
        bad_settings = utils.get_compiler_settings(
            config, args.bad_settings, args.bad_settings_default_opt_levels
        )

    if args.good_settings:
        good_settings = utils.get_compiler_settings(
            config, args.good_settings, args.good_settings_default_opt_levels
        )

    cases_to_test: list[utils.Case] = []
    check_marker: bool = False
    if args.bad_settings and args.good_settings or args.interesting_settings:
        # Override all options defined in the case
        scenario = utils.Scenario(bad_settings, good_settings)
        if tarfile.is_tarfile(file):
            case = utils.Case.from_file(config, file)
            code = case.code
            args.marker = case.marker
            if not bad_settings:
                bad_settings = copy_flag(case.scenario.target_settings[0], bad_settings)
            if not good_settings:
                good_settings = copy_flag(
                    case.scenario.attacker_settings[0], good_settings
                )
        else:
            with open(file, "r") as f:
                code = f.read()
            check_marker = True

        cases_to_test = [
            utils.Case(code, args.marker, bs, good_settings, scenario, None, None, None)
            for bs in bad_settings
        ]

    elif args.bad_settings and not args.good_settings:
        # TODO: Get flags from somewhere. For now,
        # take the ones from the first config.
        case = utils.Case.from_file(config, file)

        cases_to_test = override_bad(case, bad_settings)

    elif not args.bad_settings and args.good_settings:
        case = utils.Case.from_file(config, file)

        cases_to_test = [override_good(case, good_settings)]

    else:
        cases_to_test = [utils.Case.from_file(config, file)]

    if args.marker is not None:
        for cs in cases_to_test:
            cs.marker = args.marker
    elif check_marker:
        raise Exception("You need to specify a marker")

    if not cases_to_test:
        print("No cases arrived. Have you forgotten to specify an optimization level?")
        exit(2)

    if args.check_reduced:
        for cs in cases_to_test:
            if not cs.reduced_code:
                raise Exception("Case does not include reduced code!")
            cs.code = cs.reduced_code

    if all(
        chkr.is_interesting(
            c, preprocess=(not (args.dont_preprocess or args.check_reduced))
        )
        for c in cases_to_test
    ):
        sys.exit(0)
    else:
        sys.exit(1)
