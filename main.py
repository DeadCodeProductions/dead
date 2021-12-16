#!/usr/bin/env python3

import logging
import os
import time
from multiprocessing import Pool
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

    if args.sub == "run":

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

    elif args.sub == "absorb":

        def read_into_db(file: Path) -> None:
            # Why another db here?
            # https://docs.python.org/3/library/sqlite3.html#sqlite3.threadsafety
            # “Threads may share the module, but not connections.”
            # Of course we are using multiple processes here, but the processes
            # are a copy of eachother and who knows how things are implemented,
            # so better be safe than sorry and create a new connection,
            # especially when the next sentence is:
            # "However, this may not always be true."
            # (They may just refer to the option of having sqlite compiled with
            # SQLITE_THREADSAFE=0)
            db = database.CaseDatabase(config, config.casedb)
            case = utils.Case.from_file(config, file)
            db.record_case(case)

        pool = Pool(10)
        absorb_directory = Path(args.absorb_directory).absolute()
        paths = [p for p in absorb_directory.iterdir() if p.match("*.tar")]
        len_paths = len(paths)
        len_len_paths = len(str(len_paths))
        print("Absorbing... ", end="", flush=True)
        status_str = ""
        counter = 0
        start_time = time.perf_counter()
        for _ in pool.imap_unordered(read_into_db, paths):
            counter += 1
            print("\b" * len(status_str), end="", flush=True)
            delta_t = time.perf_counter() - start_time
            status_str = f"{{: >{len_len_paths}}}/{len_paths} {delta_t:.2f}s".format(
                counter
            )
            print(status_str, end="", flush=True)
        print("")

    gnrtr.terminate_processes()
