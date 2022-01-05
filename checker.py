#!/usr/bin/env python3

import copy
import json
import logging
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
from contextlib import contextmanager
from pathlib import Path
from types import TracebackType
from typing import Optional

import builder
import parsers
import patchdatabase
import preprocessing
import utils


# ==================== Sanitize ====================
def get_cc_output(cc: str, file: Path, flags: str, cc_timeout: int) -> tuple[int, str]:
    cmd = [
        cc,
        str(file),
        "-c",
        "-o/dev/null",
        "-Wall",
        "-Wextra",
        "-Wpedantic",
        "-O1",
        "-Wno-builtin-declaration-mismatch",
    ]
    if flags:
        cmd.extend(flags.split())
    try:
        # Not using utils.run_cmd because of redirects
        result = subprocess.run(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=cc_timeout
        )
    except subprocess.TimeoutExpired:
        return 1, ""
    except subprocess.CalledProcessError:
        # Possibly a compilation failure
        return 1, ""
    return result.returncode, result.stdout.decode("utf-8")


def check_compiler_warnings(
    clang: str, gcc: str, file: Path, flags: str, cc_timeout: int
) -> bool:
    """
    Check if the compiler outputs any warnings that indicate
    undefined behaviour.

    Args:
        clang (str): Normal executable of clang.
        gcc (str): Normal executable of gcc.
        file (Path): File to compile.
        flags (str): (additional) flags to be used when compiling.
        cc_timeout (int): Timeout for the compilation in seconds.

    Returns:
        bool: True if no warnings were found.
    """
    clang_rc, clang_output = get_cc_output(clang, file, flags, cc_timeout)
    gcc_rc, gcc_output = get_cc_output(gcc, file, flags, cc_timeout)

    if clang_rc != 0 or gcc_rc != 0:
        return False

    warnings = [
        "conversions than data arguments",
        "incompatible redeclaration",
        "ordered comparison between pointer",
        "eliding middle term",
        "end of non-void function",
        "invalid in C99",
        "specifies type",
        "should return a value",
        "uninitialized",
        "incompatible pointer to",
        "incompatible integer to",
        "comparison of distinct pointer types",
        "type specifier missing",
        "uninitialized",
        "Wimplicit-int",
        "division by zero",
        "without a cast",
        "control reaches end",
        "return type defaults",
        "cast from pointer to integer",
        "useless type name in empty declaration",
        "no semicolon at end",
        "type defaults to",
        "too few arguments for format",
        "incompatible pointer",
        "ordered comparison of pointer with integer",
        "declaration does not declare anything",
        "expects type",
        "comparison of distinct pointer types",
        "pointer from integer",
        "incompatible implicit",
        "excess elements in struct initializer",
        "comparison between pointer and integer",
        "return type of ‘main’ is not ‘int’",
        "past the end of the array",
        "no return statement in function returning non-void",
    ]

    ws = [w for w in warnings if w in clang_output or w in gcc_output]
    if len(ws) > 0:
        logging.debug(f"Compiler warnings found: {ws}")
        return False

    return True


class CCompEnv:
    def __init__(self) -> None:
        self.td: tempfile.TemporaryDirectory[str]

    def __enter__(self) -> Path:
        self.td = tempfile.TemporaryDirectory()
        tempfile.tempdir = self.td.name
        return Path(self.td.name)

    def __exit__(
        self,
        exc_type: Optional[type[BaseException]],
        exc_value: Optional[BaseException],
        exc_traceback: Optional[TracebackType],
    ) -> None:
        tempfile.tempdir = None


def verify_with_ccomp(
    ccomp: str, file: Path, flags: str, compcert_timeout: int
) -> bool:
    """Check if CompCert is unhappy about something.

    Args:
        ccomp (str): Path to ccomp executable or name in $PATH.
        file (Path): File to compile.
        flags (str): Additional flags to use.
        compcert_timeout (int): Timeout in seconds.

    Returns:
        bool: True if CompCert does not complain.
    """
    with CCompEnv() as tmpdir:
        cmd = [
            ccomp,
            str(file),
            "-interp",
            "-fall",
        ]
        if flags:
            cmd.extend(flags.split())
        res = True
        try:
            utils.run_cmd(
                cmd,
                additional_env={"TMPDIR": str(tmpdir)},
                timeout=compcert_timeout,
            )
            res = True
        except subprocess.CalledProcessError:
            res = False
        except subprocess.TimeoutExpired:
            res = False

        logging.debug(f"CComp returncode {res}")
        return res


def use_ub_sanitizers(
    clang: str, file: Path, flags: str, cc_timeout: int, exe_timeout: int
) -> bool:
    """Run clang undefined-behaviour tests

    Args:
        clang (str): Path to clang executable or name in $PATH.
        file (Path): File to test.
        flags (str): Additional flags to use.
        cc_timeout (int): Timeout for compiling in seconds.
        exe_timeout (int): Timeout for running the resulting exe in seconds.

    Returns:
        bool: True if no undefined was found.
    """
    cmd = [clang, str(file), "-O1", "-fsanitize=undefined,address"]
    if flags:
        cmd.extend(flags.split())

    with CCompEnv():
        with tempfile.NamedTemporaryFile(suffix=".exe", delete=False) as exe:
            exe.close()
            os.chmod(exe.name, 0o777)
            cmd.append(f"-o{exe.name}")
            result = subprocess.run(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=cc_timeout,
            )
            if result.returncode != 0:
                logging.debug(f"UB Sanitizer returncode {result.returncode}")
                if os.path.exists(exe.name):
                    os.remove(exe.name)
                return False
            result = subprocess.run(
                exe.name,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=exe_timeout,
            )
            os.remove(exe.name)
            logging.debug(f"UB Sanitizer returncode {result.returncode}")
            return result.returncode == 0


def sanitize(
    gcc: str,
    clang: str,
    ccomp: str,
    file: Path,
    flags: str,
    cc_timeout: int = 8,
    exe_timeout: int = 2,
    compcert_timeout: int = 16,
) -> bool:
    """Check if there is anything that could indicate undefined behaviour.

    Args:
        gcc (str): Path to gcc executable or name in $PATH.
        clang (str): Path to clang executable or name in $PATH.
        ccomp (str): Path to ccomp executable or name in $PATH.
        file (Path): File to check.
        flags (str): Additional flags to use.
        cc_timeout (int): Compiler timeout in seconds.
        exe_timeout (int): Undef.-Behaviour. runtime timeout in seconds.
        compcert_timeout (int): CompCert timeout in seconds.

    Returns:
        bool: True if nothing indicative of undefined behaviour is found.
    """
    # Taking advantage of shortciruit logic...
    try:
        return (
            check_compiler_warnings(gcc, clang, file, flags, cc_timeout)
            and use_ub_sanitizers(clang, file, flags, cc_timeout, exe_timeout)
            and verify_with_ccomp(ccomp, file, flags, compcert_timeout)
        )
    except subprocess.TimeoutExpired:
        return False


# ==================== Checker ====================


def annotate_program_with_static(
    annotator: str, file: Path, include_paths: list[str]
) -> None:
    """Turn all global variables and functions into static ones.

    Args:
        annotator (str): Path to annotator executable or name in $PATH.
        file (Path): Path to file to annotate.
        include_paths (list[str]): Include paths to use when compiling.
    """
    cmd = [annotator, str(file)]
    for path in include_paths:
        cmd.append(f"--extra-arg=-isystem{path}")
    try:
        utils.run_cmd(cmd)
    except subprocess.CalledProcessError as e:
        raise Exception("Static annotator failed to annotate {file}! {e}")


class Checker:
    def __init__(self, config: utils.NestedNamespace, bldr: builder.Builder):
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
        found_in_bad = builder.find_alive_markers(
            case.code, case.bad_setting, marker_prefix, self.builder
        )
        uninteresting = False
        if case.marker not in found_in_bad:
            uninteresting = True
        for good_setting in case.good_settings:
            found_in_good = builder.find_alive_markers(
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
            include_paths = utils.find_include_paths(
                self.config.llvm.sane_version, tf.name, case.bad_setting.get_flag_str()
            )
            annotate_program_with_static(
                self.config.static_annotator, Path(tf.name), include_paths
            )

            with open(tf.name, "r") as annotated_file:
                static_code = annotated_file.read()

            asm_bad = builder.get_asm_str(static_code, case.bad_setting, self.builder)
            uninteresting = False
            if case.marker not in asm_bad:
                uninteresting = True
            for good_setting in case.good_settings:
                asm_good = builder.get_asm_str(static_code, good_setting, self.builder)
                if case.marker in asm_good:
                    uninteresting = True
                    break
            return not uninteresting

    def _emtpy_marker_code_str(self, case: utils.Case) -> str:
        marker_prefix = utils.get_marker_prefix(case.marker)
        p = re.compile(f"void {marker_prefix}(.*)\(void\);")
        empty_body_code = ""
        for line in case.code.split("\n"):
            m = p.match(line)
            if m:
                empty_body_code += f"\nvoid {marker_prefix}{m.group(1)}(void){{}}"
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

            return sanitize(
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

    patchdb = patchdatabase.PatchDB(config.patchdb)
    bldr = builder.Builder(config, patchdb, args.cores)
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
        tmp, good_settings = utils.get_interesting_settings(
            config, args.interesting_settings
        )
        bad_settings = [tmp]

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
