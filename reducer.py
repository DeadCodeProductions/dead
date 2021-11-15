#!/usr/bin/env python3

import json
import logging
import os
import subprocess
import tarfile
import tempfile
import time
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import builder
import generator
import parsers
import patchdatabase
import preprocessing
import utils


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

    def reduce_file(self, file: Path, force: bool = False) -> bool:
        case = utils.Case.from_file(self.config, file)
        if self.reduce_case(case, force=force):
            case.to_file(file)
            return True
        return False

    def reduce_case(self, case: utils.Case, force: bool = False) -> bool:
        if not force and case.reduced_code:
            return True

        if not case.reduced_code:
            case.reduced_code = []
        if reduce_code := self.reduce_code(
            case.code, case.marker, case.bad_setting, case.good_settings
        ):
            case.reduced_code.append(reduce_code)
            return True
        return False

    def reduce_code(
        self,
        code: str,
        marker: str,
        bad_setting: utils.CompilerSetting,
        good_settings: list[utils.CompilerSetting],
    ) -> Optional[str]:

        # creduce likes to kill unfinished processes with SIGKILL
        # so they can't clean up after themselves.
        # Setting a temporary temporary directory for creduce to be able to clean
        # up everthing
        with temp_dir_env() as tmpdir:
            # preprocess file
            pp_code = preprocessing.preprocess_csmith_code(
                code,
                utils.get_marker_prefix(marker),
                bad_setting,
                self.bldr,
            )

            pp_code_path = tmpdir / "code_pp.c"
            with open(pp_code_path, "w") as f:
                f.write(pp_code)

            # save interesting_settings
            settings_path = tmpdir / "interesting_settings.json"

            int_settings = {}
            int_settings["bad_setting"] = bad_setting.to_jsonable_dict()
            int_settings["good_settings"] = [
                gs.to_jsonable_dict() for gs in good_settings
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
                    f" --dont-preprocess"
                    f" --config {self.config.config_path}"
                    f" --marker {marker}"
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
                current_time = time.strftime("%Y%m%d-%H%M%S")
                build_log_path = Path(config.logdir) / f"{current_time}-creduce.log"
                logging.info(f"creduce logfile at {build_log_path}")
                with open(build_log_path, "a") as build_log:
                    utils.run_cmd_to_logfile(
                        creduce_cmd, log_file=build_log, working_dir=Path(tmpdir)
                    )
            except subprocess.CalledProcessError as e:
                logging.info(f"Failed to process code. Exception: {e}")
                return None

            # save result in tar
            with open(pp_code_path, "r") as f:
                reduced_code = f.read()

            return reduced_code


if __name__ == "__main__":
    config, args = utils.get_config_and_parser(parsers.reducer_parser())

    patchdb = patchdatabase.PatchDB(config.patchdb)
    bldr = builder.Builder(config, patchdb, args.cores)
    gnrtr = generator.CSmithCaseGenerator(config, patchdb)
    rdcr = Reducer(config, bldr)

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
            try:
                rdcr.reduce_file(tf, args.force)
            except builder.BuildException as e:
                print("{e}")

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
                try:
                    rdcr.reduce_file(path)
                except builder.BuildException as e:
                    print(f"{e}")
        else:
            for i in range(args.amount):
                path = next(gen)
                try:
                    rdcr.reduce_file(path)
                except builder.BuildException as e:
                    print(f"{e}")

    elif not args.work_through:
        if not args.file:
            print(
                "--file is needed when just running checking for a file. Have you forgotten to set --generate?"
            )
        file = Path(args.file).absolute()
        if rdcr.reduce_file(file, args.force):
            print(file)
