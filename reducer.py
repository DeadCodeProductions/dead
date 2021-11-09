#!/usr/bin/env python3

import json
import logging
import os
import re
import shutil
import subprocess
import tarfile
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import builder
import generator
import parsers
import patchdatabase
import utils


# ==================== Preprocessing ====================
def find_marker_decl_range(lines, markers):
    p = re.compile(f"void {markers}(.*)\(void\);")
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


def find_platform_main_end(lines: list[str]):
    p = re.compile(".*platform_main_end.*")
    for i, line in enumerate(lines):
        if p.match(line):
            return i


def remove_platform_main_begin(lines: list[str]):
    p = re.compile(".*platform_main_begin.*")
    for line in lines:
        if not p.match(line):
            yield line


def remove_print_hash_value(lines: list[str]):
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
) -> str:
    tf = utils.save_to_tmp_file(code)
    res = preprocess_csmith_file(Path(tf.name), marker_prefix, compiler_setting, bldr)
    return res


# ==================== Reducer ====================
@contextmanager
def temp_dir_env() -> Path:
    td = tempfile.TemporaryDirectory()
    tempfile.tempdir = td.name
    try:
        yield Path(td.name)
    finally:
        tempfile.tempdir = None


@dataclass
class Reducer:
    config: utils.NestedNamespace
    bldr: builder.Builder

    def reduce(self, file: Path, force: bool = False) -> tuple[bool, Path]:
        case = utils.Case.from_file(self.config, file)
        if not force and case.reduced_code:
            return True, file

        # creduce likes to kill unfinished processes with SIGKILL
        # so they can't clean up after themselves.
        # Setting a temporary temporary directory for creduce to be able to clean
        # up everthing
        with temp_dir_env() as tmpdir:
            # preprocess file
            pp_code = preprocess_csmith_code(
                case.code,
                utils.get_marker_prefix(case.marker),
                case.bad_setting,
                self.bldr,
            )

            pp_code_path = tmpdir / "code_pp.c"
            with open(pp_code_path, "w") as f:
                f.write(pp_code)

            # save interesting_settings
            settings_path = tmpdir / "interesting_settings.json"

            int_settings = {}
            int_settings["bad_setting"] = case.bad_setting.to_jsonable_dict()
            int_settings["good_settings"] = [
                gs.to_jsonable_dict() for gs in case.good_settings
            ]
            with open(settings_path, "w") as f:
                json.dump(int_settings, f)

            # create script for creduce
            script_path = tmpdir / "check.sh"
            with open(script_path, "w") as f:
                print("#/bin/sh", file=f)
                print("TMPD=$(mktemp -d)", file=f)
                print("trap '{ rm -rf \"$TMPD\"; }' INT TERM EXIT", file=f)
                print(
                    "timeout 10 "
                    f"{Path(__file__).parent.resolve()}/checker.py"
                    f" --config {self.config.config_path}"
                    f" --marker {case.marker}"
                    f" --interesting-settings {str(settings_path)}"
                    f" --file code_pp.c",
                    # f' --file {str(pp_code_path)}',
                    file=f,
                )

            os.chmod(script_path, 0o777)
            # run creduce
            creduce_cmd = [
                self.config.creduce,
                "--n",
                f"{self.bldr.cores}",
                str(script_path.name),
                str(pp_code_path.name),
            ]

            try:
                subprocess.run(creduce_cmd, cwd=Path(tmpdir), check=True)
            except subprocess.CalledProcessError as e:
                logging.info(f"Failed to process {file}. Exception: {e}")
                return False, file

            # save result in tar
            with open(pp_code_path, "r") as f:
                case.reduced_code.append(f.read())
            if not case.path:
                case.path = file
            case.to_file(case.path)

            return True, case.path


if __name__ == "__main__":
    config, args = utils.get_config_and_parser(parsers.reducer_parser())

    patchdb = patchdatabase.PatchDB(config.patchdb)
    bldr = builder.Builder(config, patchdb, args.cores)
    gnrtr = generator.CSmithCaseGenerator(config, patchdb)
    rdcr = Reducer(config, bldr)

    if args.check_pp:
        file = Path(args.file).absolute()
        case = utils.Case.from_file(config, file)
        # preprocess file
        pp_code = preprocess_csmith_code(
            case.code,
            utils.get_marker_prefix(case.marker),
            case.bad_setting,
            bldr,
        )

        case.code = pp_code
        # Taking advantage of shortciruit logic
        a = gnrtr.chkr.is_interesting_wrt_marker(case)
        b = gnrtr.chkr.is_interesting_wrt_ccc(case)
        c = gnrtr.chkr.is_interesting_with_static_globals(case)
        d = gnrtr.chkr.is_interesting_with_empty_marker_bodies(case)
        print(a, b, c, d)
        if not all((a, b, c, d)):
            exit(1)
        exit(0)

    if args.work_through:
        if args.output_directory is None:
            print("Missing output/work-through directory!")
            exit(1)
        else:
            output_dir = Path(os.path.abspath(args.output_directory))
            os.makedirs(output_dir, exist_ok=True)

        tars = [
            output_dir / d
            for d in os.listdir(output_dir)
            if tarfile.is_tarfile(output_dir / d)
        ]

        print(f"Processing {len(tars)} tars")
        for tf in tars:
            print(f"Processing {tf}")
            case = utils.Case.from_file(config, tf)
            rdcr.reduce(tf, args.force)

    # if (We want to generate something and not only reduce a file)
    if args.generate:
        if args.output_directory is None:
            print("Missing output directory!")
            exit(1)
        else:
            output_dir = os.path.abspath(args.output_directory)
            os.makedirs(output_dir, exist_ok=True)

        scenario = utils.Scenario([], [])
        # When file is specified, use scenario of file as base
        if args.file:
            file = Path(args.file).absolute()
            scenario = utils.Case.from_file(config, file).scenario

        tmp = utils.get_scenario(config, args)
        if tmp.target_settings:
            scenario.target_settings = tmp.target_settings
        if tmp.attacker_settings:
            scenario.attacker_settings = tmp.attacker_settings

        gen = gnrtr.parallel_interesting_case(
            config, scenario, bldr.cores, output_dir, start_stop=True
        )
        if args.amount == 0:
            while True:
                path = next(gen)
                print(rdcr.reduce(path))
        else:
            for i in range(args.amount):
                path = next(gen)
                print(rdcr.reduce(path))

    else:
        if not args.file:
            print(
                "--file is needed when just running checking for a file. Have you forgotten to set --generate?"
            )
        file = Path(args.file).absolute()
        print(rdcr.reduce(file, args.force))
