#!/usr/bin/env python3

import logging
import re
import subprocess
import sys
import tempfile
from collections import defaultdict
from pathlib import Path
from typing import Optional

from dead_instrumenter.instrumenter import annotate_with_static
from diopter import preprocessor, sanitizer, compiler

from dead.utils import DeadConfig, RegressionCase


def find_alive_markers(
    code: str,
    compiler_setting: compiler.CompilationSetting,
    marker_prefix: str,  # get this from dead_instrumenter?
) -> set[str]:
    """Return set of markers which are found in the assembly.

    Args:
        code (str): Code with markers
        compiler_setting (utils.CompilerSetting): Compiler to use
        marker_prefix (str): Prefix of markers (utils.get_marker_prefix)
        bldr (Builder): Builder to get the compiler

    Returns:
        set[str]: Set of markers found in the assembly i.e. alive markers

    Raises:
        CompileError: Raised when code can't be compiled.
    """
    alive_regex = re.compile(f".*[call|jmp].*{marker_prefix}([0-9]+)_.*")
    asm = compiler_setting.get_asm_from_code(code)

    alive_markers = set()
    for line in asm.split("\n"):
        m = alive_regex.match(line.strip())
        if m:
            alive_markers.add(f"{marker_prefix}{m.group(1)}_")

    return alive_markers


# TODO: we could write a more generic checker, e.g., one that checks also for signatures
# TODO: the checker should probably not deal with making globals static, it
# should be done externally
class Checker:
    def __init__(
        self,
        llvm: compiler.CompilerExe,
        gcc: compiler.CompilerExe,
        ccc: compiler.ClangTool,
        ccomp: Optional[str],
        marker_prefix: str = "DCEMarker",
    ):
        self.llvm = llvm
        self.gcc = gcc
        self.ccc = ccc
        self.ccomp = ccomp
        self.marker_prefix = marker_prefix

    def is_interesting_wrt_marker(
        self,
        code: str,
        marker: str,
        bad_setting: compiler.CompilationSetting,
        good_setting: compiler.CompilationSetting,
    ) -> bool:
        """Checks if the marker is eliminated by all good compilers/setting
        and not eliminated by the bad compiler/setting.

        Args:
            code (str): csmith code to check.

        Returns:
            bool: True if the maker is not eliminated by the bad setting and
                eliminated by all good settings.

        Raises:
            builder.CompileError: Finding alive markers may fail.
        """
        if marker not in find_alive_markers(code, bad_setting, self.marker_prefix):
            return False

        return marker not in find_alive_markers(code, good_setting, self.marker_prefix)

    def is_marker_in_callchain_from_main(
        self,
        code: str,
        marker: str,
        setting: compiler.CompilationSetting,
    ) -> bool:
        """Check if there is a call chain between main and the marker.

        Args:


        Returns:
            bool: If there is a call chain between main and the marker
        """

        try:
            # TODO: after moving ccc to a separate repo, add some kind of
            # python wrapper so that we don't manually check the output
            return (
                f"call chain exists between main -> {marker}".strip()
                in self.ccc.run_on_code(
                    code,
                    ["--from=main", f"--to={marker}"],
                    setting.include_paths + setting.system_include_paths,
                    compiler.ClangToolMode.CAPTURE_OUT_ERR,
                )
            )
        except subprocess.CalledProcessError:
            logging.debug("CCC failed")
            return False
        except subprocess.TimeoutExpired:
            logging.debug("CCC timed out")
            return False

    def get_code_with_static_globals(
        self,
        code: str,
        setting: compiler.CompilationSetting,
    ) -> str:
        with tempfile.NamedTemporaryFile(suffix=".c") as tf:
            with open(tf.name, "w") as new_cfile:
                print(code, file=new_cfile)

            # TODO: Handle include_paths better
            # TODO: annotate_with_static should operate on an str
            annotate_with_static(
                Path(tf.name),
                [
                    f"-isystem{path}"
                    for path in setting.include_paths + setting.system_include_paths
                ],
            )

            with open(tf.name, "r") as annotated_file:
                static_code = annotated_file.read()
            return static_code

    def _emtpy_marker_code_str(self, code: str) -> str:
        p = re.compile(rf"void {self.marker_prefix}(.*)\(void\);(.*)")
        empty_body_code = ""
        for line in code.split("\n"):
            m = p.match(line)
            if m:
                empty_body_code += (
                    "\n"
                    + rf"void {self.marker_prefix}{m.group(1)}(void){{}}"
                    + "\n"
                    + rf"{m.group(2)}"
                )
            else:
                empty_body_code += f"\n{line}"

        return empty_body_code

    def is_interesting_marker(
        self,
        code: str,
        marker: str,
        bad_setting: compiler.CompilationSetting,
        good_setting: compiler.CompilationSetting,
        sanitize: bool = True,
        make_globals_static: bool = True,
        preprocess: bool = False,
    ) -> bool:
        """Check if a code passes all the 'interestingness'-checks.
        Preprocesses code by default to prevent surprises when preprocessing
        later.

        Args:
            self:
            code (str): the csmith code to check.
            preprocess (bool): Whether or not to preprocess the code
            sanitize (bool): Whether or not to sanitize the code

        Returns:
            bool: True if the case passes all 'interestingness'-checks

        Raises:
            builder.CompileError
        """

        if preprocess:
            # we should read the include path from DiopterContext
            if pp_code := preprocessor.preprocess_csmith_code(
                code,
                str(self.gcc.exe),
                [f"-isystem{DeadConfig.get_config().csmith_include_path}"],
            ):
                code = pp_code

        if not self.is_marker_in_callchain_from_main(code, marker, bad_setting):
            return False

        if make_globals_static:
            code = self.get_code_with_static_globals(code, bad_setting)

        if not self.is_interesting_wrt_marker(code, marker, bad_setting, good_setting):
            return False

        if sanitize:
            empty_body_code = self._emtpy_marker_code_str(code)
            if not sanitizer.sanitize_code(
                str(self.gcc.exe),
                str(self.llvm.exe),
                str(self.ccomp),
                empty_body_code,
                bad_setting.flags_str(),
            ):
                return False

        return True

    def find_interesting_markers(
        self,
        code: str,
        bad_setting: compiler.CompilationSetting,
        good_settings: list[compiler.CompilationSetting],
        make_globals_static: bool = True,
        preprocess: bool = False,
    ) -> list[tuple[str, list[compiler.CompilationSetting]]]:
        """Check if a code passes all the 'interestingness'-checks.
        Preprocesses code by default to prevent surprises when preprocessing
        later.

        Args:
            self:
            code (str): the csmith code to check.
            preprocess (bool): Whether or not to preprocess the code
            sanitize (bool): Whether or not to sanitize the code

        Returns:
            list(str): list of interesting markers
        """

        if preprocess:
            if pp_code := preprocessor.preprocess_csmith_code(
                code,
                str(self.gcc.exe),
                [f"-isystem{DeadConfig.get_config().csmith_include_path}"],
            ):
                code = pp_code

        if make_globals_static:
            code = self.get_code_with_static_globals(code, bad_setting)

        markers_in_bad = find_alive_markers(code, bad_setting, self.marker_prefix)
        interesting_markers_to_settings: dict[
            str, list[compiler.CompilationSetting]
        ] = defaultdict(list)

        for good_setting in good_settings:
            for marker in markers_in_bad - find_alive_markers(
                code, good_setting, self.marker_prefix
            ):
                interesting_markers_to_settings[marker].append(good_setting)

        return [
            (marker, settings)
            for marker, settings in interesting_markers_to_settings.items()
            if self.is_marker_in_callchain_from_main(code, marker, bad_setting)
        ]

    def is_interesting_case(
        self,
        case_: RegressionCase,
        sanitize: bool = True,
        make_globals_static: bool = True,
        preprocess: bool = False,
    ) -> bool:
        return self.is_interesting_marker(
            case_.code,
            case_.marker,
            case_.bad_setting,
            case_.good_setting,
            sanitize=sanitize,
            make_globals_static=make_globals_static,
            preprocess=preprocess,
        )
