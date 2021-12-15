#!/usr/bin/env python3

import logging
import os
import time
from pathlib import Path
from typing import Optional

import bisector
import builder
import checker
import database
import generator
import parsers
import patchdatabase
import reducer
import utils

if __name__ == "__main__":
    config, args = utils.get_config_and_parser(parsers.main_parser())

    patchdb = patchdatabase.PatchDB(config.patchdb)
    bldr = builder.Builder(config, patchdb, args.cores)
    chkr = checker.Checker(config, bldr)
    gnrtr = generator.CSmithCaseGenerator(config, patchdb, args.cores)
    rdcr = reducer.Reducer(config, bldr)
    bsctr = bisector.Bisector(config, bldr, chkr)

    ddb = database.CaseDatabase(config, config.casedb)

    if args.run:

        scenario = utils.get_scenario(config, args)

        counter = 0
        while True:
            if args.amount and args.amount != 0:
                if counter >= args.amount:
                    break
            # Time db values
            generator_time: Optional[float] = None
            generator_try_count: Optional[int] = None
            bisector_time: Optional[float] = None
            bisector_steps: Optional[int] = None
            reducer_time: Optional[float] = None

            time_start_gen = time.perf_counter()
            case = gnrtr.generate_interesting_case(scenario)
            time_end_gen = time.perf_counter()
            generator_time = time_end_gen - time_start_gen
            generator_try_count = gnrtr.try_counter

            if args.bisector:
                try:
                    time_start_bisector = time.perf_counter()
                    bisect_worked = bsctr.bisect_case(case)
                    time_end_bisector = time.perf_counter()
                    bisector_time = time_end_bisector - time_start_bisector
                    bisector_steps = bsctr.steps
                    if not bisect_worked:
                        continue
                except bisector.BisectionException as e:
                    print(f"BisectionException: '{e}'")
                    continue
                except AssertionError as e:
                    print(f"AssertionError: '{e}'")
                    continue
                except builder.BuildException as e:
                    print(f"BuildException: '{e}'")
                    continue

            if args.reducer:
                try:
                    time_start_reducer = time.perf_counter()
                    worked = rdcr.reduce_case(case)
                    time_end_reducer = time.perf_counter()
                    reducer_time = time_end_reducer - time_start_reducer
                except builder.BuildException as e:
                    print(f"BuildException: {e}")
                    continue

            case_id = ddb.record_case(case)
            ddb.add_timing(
                case_id,
                generator_time,
                generator_try_count,
                bisector_time,
                bisector_steps,
                reducer_time,
            )

            counter += 1

    gnrtr.terminate_processes()
