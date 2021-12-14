#!/usr/bin/env python3

import logging
import os
from pathlib import Path

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
        gen = gnrtr.parallel_interesting_case(
            config, scenario, bldr.cores, start_stop=True
        )

        counter = 0
        while True:
            if args.amount and args.amount != 0:
                if counter >= args.amount:
                    break
            case = next(gen)

            if args.bisector:
                try:
                    if not bsctr.bisect_case(case):
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
                    worked = rdcr.reduce_case(case)
                except builder.BuildException as e:
                    print(f"BuildException: {e}")
                    continue

            ddb.record_case(case)
            counter += 1

    gnrtr.terminate_processes()
