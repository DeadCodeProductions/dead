import os
import re
import shutil
import tempfile
from pathlib import Path
from typing import Generator, Optional

import builder
import utils

"""
Functions to preprocess code for creduce.
See creduce --help to see what it wants.
"""


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


def find_platform_main_end(lines: list[str]) -> Optional[int]:
    p = re.compile(".*platform_main_end.*")
    for i, line in enumerate(lines):
        if p.match(line):
            return i


def remove_platform_main_begin(lines: list[str]) -> Generator[str, None, None]:
    p = re.compile(".*platform_main_begin.*")
    for line in lines:
        if not p.match(line):
            yield line


def remove_print_hash_value(lines: list[str]) -> Generator[str, None, None]:
    p = re.compile(".*print_hash_value = 1.*")
    for line in lines:
        if not p.match(line):
            yield line


def preprocess_csmith_file(
    path: os.PathLike,
    marker_prefix: str,
    compiler_setting: utils.CompilerSetting,
    bldr: builder.Builder,
) -> str:

    with tempfile.NamedTemporaryFile(suffix=".c") as tf:
        shutil.copy(path, tf.name)

        bldr

        additional_flags = (
            []
            if compiler_setting.additional_flags is None
            else compiler_setting.additional_flags
        )
        cmd = [
            builder.get_compiler_executable(compiler_setting, bldr),
            tf.name,
            "-P",
            "-E",
        ] + additional_flags
        lines = utils.run_cmd(cmd).split("\n")
        marker_range = find_marker_decl_range(lines, marker_prefix)
        platform_main_end_line = find_platform_main_end(lines)
        if not platform_main_end_line:
            raise Exception("Couldn't find 'platform_main_end'")
        marker_decls = lines[marker_range[0] : marker_range[1]]

        lines = lines[platform_main_end_line + 1 :]
        lines = remove_print_hash_value([l for l in remove_platform_main_begin(lines)])
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
) -> str:
    tf = utils.save_to_tmp_file(code)
    res = preprocess_csmith_file(Path(tf.name), marker_prefix, compiler_setting, bldr)
    return res
