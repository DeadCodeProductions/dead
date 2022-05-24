import os
import re
import shutil
import tempfile
from pathlib import Path
from typing import Generator, Iterable, Optional

import builder
import utils

"""
Functions to preprocess code for creduce.
See creduce --help to see what it wants.
"""


class PreprocessError(Exception):
    pass


def find_marker_decl_range(lines: list[str], marker_prefix: str) -> tuple[int, int]:
    p = re.compile(rf"void {marker_prefix}(.*)\(void\);")
    first = 0
    for i, line in enumerate(lines):
        if p.match(line):
            first = i
            break
    last = first + 1
    for i, line in enumerate(lines[first + 1 :], start=first + 1):
        if p.match(line):
            continue
        else:
            last = i
            break
    return first, last


def find_platform_main_end(lines: Iterable[str]) -> Optional[int]:
    p = re.compile(r".*platform_main_end.*")
    for i, line in enumerate(lines):
        if p.match(line):
            return i
    return None


def remove_platform_main_begin(lines: Iterable[str]) -> list[str]:
    p = re.compile(r".*platform_main_begin.*")
    return [line for line in lines if not p.match(line)]


def remove_print_hash_value(lines: Iterable[str]) -> list[str]:
    p = re.compile(r".*print_hash_value = 1.*")
    return [line for line in lines if not p.match(line)]


def preprocess_lines(lines: list[str]) -> str:
    start_patterns = [
        re.compile(r"^extern.*"),
        re.compile(r"^typedef.*"),
        re.compile(r"^struct.*"),
        # The following patterns are to catch if the last of the previous
        # patterns in the file was tainted and we'd otherwise mark the rest
        # of the file as tainted, as we'll find no end in this case.
        re.compile(r"^static.*"),
        re.compile(r"^void.*"),
    ]
    taint_patterns = [
        re.compile(r".*__access__.*"),  # LLVM doesn't know about this
        re.compile(r".*__malloc__.*"),
        re.compile(
            r".*_[F|f]loat[0-9]{1,3}x{0,1}.*"
        ),  # https://gcc.gnu.org/onlinedocs/gcc/Floating-Types.html#Floating-Types
        re.compile(r".*__asm__.*"),  # CompCert has problems
    ]

    def is_start(l: str) -> bool:
        return any([p_start.match(l) for p_start in start_patterns])

    lines_to_skip: list[int] = []
    for i, line in enumerate(lines):
        for p in taint_patterns:
            if p.match(line):
                # Searching for start of tainted region
                up_i = i
                up_line = lines[up_i]
                while up_i > 0 and not is_start(up_line):
                    up_i -= 1
                    up_line = lines[up_i]

                # Searching for end of tainted region
                down_i = i + 1
                down_line = lines[down_i]
                while down_i < len(lines) and not is_start(down_line):
                    down_i += 1
                    down_line = lines[down_i]

                lines_to_skip.extend(list(range(up_i, down_i)))

    return "\n".join([line for i, line in enumerate(lines) if i not in lines_to_skip])


def preprocess_csmith_file(
    path: os.PathLike[str],
    marker_prefix: str,
    compiler_setting: utils.CompilerSetting,
    bldr: builder.Builder,
) -> str:

    with tempfile.NamedTemporaryFile(suffix=".c") as tf:
        shutil.copy(path, tf.name)

        additional_flags = (
            []
            if compiler_setting.additional_flags is None
            else compiler_setting.additional_flags
        )
        cmd = [
            str(builder.get_compiler_executable(compiler_setting, bldr)),
            tf.name,
            "-P",
            "-E",
        ] + additional_flags
        lines = utils.run_cmd(cmd).split("\n")

        return preprocess_lines(lines)


def preprocess_csmith_code(
    code: str,
    marker_prefix: str,
    compiler_setting: utils.CompilerSetting,
    bldr: builder.Builder,
) -> Optional[str]:
    """Will *try* to preprocess code as if it comes from csmith.

    Args:
        code (str): code to preprocess
        marker_prefix (str): Marker prefix
        compiler_setting (utils.CompilerSetting): Setting to preprocess with
        bldr (builder.Builder):

    Returns:
        Optional[str]: preprocessed code if it was able to preprocess it.
    """
    tf = utils.save_to_tmp_file(code)
    try:
        res = preprocess_csmith_file(
            Path(tf.name), marker_prefix, compiler_setting, bldr
        )
        return res
    except PreprocessError:
        return None
