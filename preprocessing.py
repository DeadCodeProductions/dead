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
    p = re.compile(f"void {marker_prefix}(.*)\(void\);")
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
    p = re.compile(".*platform_main_end.*")
    for i, line in enumerate(lines):
        if p.match(line):
            return i
    return None


def remove_platform_main_begin(lines: Iterable[str]) -> list[str]:
    p = re.compile(".*platform_main_begin.*")
    return [line for line in lines if not p.match(line)]


def remove_print_hash_value(lines: Iterable[str]) -> list[str]:
    p = re.compile(".*print_hash_value = 1.*")
    return [line for line in lines if not p.match(line)]


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
        marker_range = find_marker_decl_range(lines, marker_prefix)
        platform_main_end_line = find_platform_main_end(lines)
        if not platform_main_end_line:
            raise PreprocessError("Couldn't find 'platform_main_end'")
        marker_decls = lines[marker_range[0] : marker_range[1]]

        lines = lines[platform_main_end_line + 1 :]
        lines = remove_print_hash_value(remove_platform_main_begin(lines))
        lines = (
            marker_decls
            + [
                "typedef unsigned int size_t;",
                "typedef signed char int8_t;",
                "typedef short int int16_t;",
                "typedef int int32_t;",
                "typedef long long int int64_t;",
                "typedef unsigned char uint8_t;",
                "typedef unsigned short int uint16_t;",
                "typedef unsigned int uint32_t;",
                "typedef unsigned long long int uint64_t;",
                "int printf (const char *, ...);",
                "void __assert_fail (const char *__assertion, const char *__file, unsigned int __line, const char *__function);",
                "static void",
                "platform_main_end(uint32_t crc, int flag)",
            ]
            + list(lines)
        )

        return "\n".join(lines)


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
