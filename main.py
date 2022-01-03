#!/usr/bin/env python3

import copy
import functools
import re
import sys
import time
from multiprocessing import Pool
from pathlib import Path
from typing import Optional, cast

import bisector
import builder
import checker
import database
import generator
import parsers
import patchdatabase
import reducer
import repository
import utils


def _run() -> None:
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
        ddb.record_timing(
            case_id,
            generator_time,
            generator_try_count,
            bisector_time,
            bisector_steps,
            reducer_time,
        )

        counter += 1


def _absorb() -> None:
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


def _tofile() -> None:
    case_pre = ddb.get_case_from_id(args.case_id)
    if not case_pre:
        print(f"Found no case for ID {args.case_id}")
        exit(1)
    else:
        case = case_pre
    print(f"Saving case to ./case_{args.case_id}.tar")
    case.to_file(Path(f"./case_{args.case_id}.tar"))


def _massageorlink() -> None:
    pre_check_case = ddb.get_case_from_id(args.case_id)
    if not pre_check_case:
        print("No case with this ID.", file=sys.stderr)
        exit(1)
    else:
        case = pre_check_case

    if args.sub == "massage":
        with open(args.code_path, "r") as f:
            massaged_code = f.read()

        cpy = copy.deepcopy(case)
        cpy.code = massaged_code
        # Check if massaged code is valid
        if not chkr.is_interesting(cpy, preprocess=False):
            print("Massaged code failed interestingness check.")
            exit(1)
        else:
            print("OK")
            _, link, fixed_by = ddb.get_report_info_from_id(args.case_id)
            if link or fixed_by:
                print("Not updating, was already fixed or reported..")
                exit(0)
            ddb.record_reported_case(args.case_id, massaged_code, link, fixed_by)
            print("Saved...")

    elif args.sub == "link":
        maybe_massaged_code, _, fixed_by = ddb.get_report_info_from_id(args.case_id)
        if fixed_by:
            print("Not updating, was already fixed...")
            exit(0)
        ddb.record_reported_case(args.case_id, maybe_massaged_code, args.link, fixed_by)
        print("Saved...")


def _rereduce() -> None:
    with open(args.code_path, "r") as f:
        rereduce_code = f.read()

    case = ddb.get_case_from_id_or_die(args.case_id)
    print(f"Re-reducing code with respect to Case {args.case_id}", file=sys.stderr)
    res = rdcr.reduce_code(
        rereduce_code,
        case.marker,
        case.bad_setting,
        case.good_settings,
        preprocess=False,
    )

    print(res)


def _report() -> None:
    pre_check_case = ddb.get_case_from_id(args.case_id)
    if not pre_check_case:
        print("No case with this ID.", file=sys.stderr)
        exit(1)
    else:
        case = pre_check_case

    if not case.bisection:
        print("Case is not bisected. Starting bisection...", file=sys.stderr)
        start_time = time.perf_counter()
        worked = bsctr.bisect_case(case)
        bisector_time = time.perf_counter() - start_time
        if worked:
            ddb.update_case(args.case_id, case)
            g_time, gtc, b_time, b_steps, r_time = ddb.get_timing_from_id(args.case_id)
            b_time = bisector_time
            b_steps = bsctr.steps
            ddb.record_timing(args.case_id, g_time, gtc, b_time, b_steps, r_time)

        else:
            print("Could not bisect case. Aborting...", file=sys.stderr)
            exit(1)

    # check for reduced and massaged code
    if not case.reduced_code:
        print("Case is not reduced. Starting reduction...", file=sys.stderr)
        if rdcr.reduce_case(case):
            ddb.update_case(args.case_id, case)
        else:
            print("Could not reduce case. Aborting...", file=sys.stderr)
            exit(1)

    massaged_code_pre, _, _ = ddb.get_report_info_from_id(args.case_id)

    if massaged_code_pre:
        massaged_code = massaged_code_pre
        # Check if both bisect to the same commit
        print("Check bisection of massaged code...", file=sys.stderr)
        cpy = copy.deepcopy(case)
        cpy.reduced_code = massaged_code
        bsctr.bisect_case(case, force=True)

        if cpy.bisection != case.bisection:
            print("Massaged code bisects to different commit!", file=sys.stderr)
            exit(1)
            # TODO: How to handle this?
            # Creating new good_settings by going through case.scenario
            # as the massaged_code may not have the same good_settings.
        else:
            case.reduced_code = massaged_code

    bad_setting = case.bad_setting
    bad_repo = repository.Repo(
        bad_setting.compiler_config.repo, bad_setting.compiler_config.main_branch
    )
    is_gcc: bool = bad_setting.compiler_config.name == "gcc"

    # Last sanity check
    cpy = copy.deepcopy(case)
    cpy.code = cast(str, case.reduced_code)
    print("Normal interestingness test...", end="", file=sys.stderr, flush=True)
    if not chkr.is_interesting(cpy, preprocess=False):
        print("\nCase is not interesting! Aborting...", file=sys.stderr)
        exit(1)
    else:
        print("OK", file=sys.stderr)

    # Check against newest upstream
    if args.pull:
        print("Pulling Repo...", file=sys.stderr)
        bad_repo.pull()
    print("Interestingness test against main...", end="", file=sys.stderr)
    cpy.bad_setting.rev = bad_repo.rev_to_commit(f"{bad_repo.main_branch}")
    if not chkr.is_interesting(cpy, preprocess=False):
        print(
            "\nCase is not interesting on main! Might be fixed. Stopping...",
            file=sys.stderr,
        )
        exit(0)
    else:
        print("OK", file=sys.stderr)
        # Use newest main in report
        case.bad_setting.rev = cpy.bad_setting.rev

    # Choose same opt level and newest version
    possible_good_compiler = [
        gs for gs in case.good_settings if gs.opt_level == bad_setting.opt_level
    ]

    good_setting = utils.get_latest_compiler_setting_from_list(
        bad_repo, possible_good_compiler
    )

    # Replace markers
    source = cpy.code.replace(cpy.marker, "foo").replace(
        utils.get_marker_prefix(cpy.marker), "bar"
    )

    bad_setting_tag = bad_setting.rev + " (trunk)"
    bad_setting_str = f"{bad_setting.compiler_config.name}-{bad_setting_tag} -O{bad_setting.opt_level}"

    tmp = bad_repo.rev_to_tag(good_setting.rev)
    if not tmp:
        good_setting_tag = good_setting.rev
    else:
        good_setting_tag = tmp
    good_setting_str = f"{good_setting.compiler_config.name}-{good_setting_tag} -O{good_setting.opt_level}"

    def to_collapsed(
        s: str, is_gcc: bool, summary: str = "Output", open: bool = False
    ) -> str:
        if not is_gcc:
            sopen = "open" if open else ""
            s = (
                f"<details {sopen}><summary>{summary}</summary><p>\n"
                + s
                + "\n</p></details>"
            )
        return s

    def to_code(code: str, is_gcc: bool, stype: str = "") -> str:
        if not is_gcc:
            return f"\n```{stype}\n" + code.rstrip() + "\n```"
        return code

    def print_cody_str(s: str, is_gcc: bool) -> None:
        if not is_gcc:
            s = "`" + s + "`"
        print(s)

    def to_cody_str(s: str, is_gcc: bool) -> str:
        if not is_gcc:
            s = "`" + s + "`"
        return s

    def replace_rand(code: str) -> str:
        # Replace .file with case.c
        ex = re.compile(r"\t\.file\t(\".*\")")
        m = ex.search(code)
        if m:
            res = m.group(1)
            return code.replace(res, "case.c")
        return code

    def prep_asm(asm: str, is_gcc: bool) -> str:
        asm = replace_rand(asm)
        asm = to_code(asm, is_gcc, "asm")
        asm = to_collapsed(asm, is_gcc)
        return asm

    print(to_cody_str("cat case.c", is_gcc))
    print(to_code(source, is_gcc, "c"))

    print(
        f"`{bad_setting_str}` can not eliminate `foo` but `{good_setting_str}` can.\n"
    )

    # Compile
    asm_bad = builder.get_asm_str(source, case.bad_setting, bldr)
    asm_good = builder.get_asm_str(source, good_setting, bldr)

    print_cody_str(f"{bad_setting_str} -S -o /dev/stdout case.c", is_gcc)
    print(prep_asm(asm_bad, is_gcc))
    print()

    print_cody_str(f"{good_setting_str} -S -o /dev/stdout case.c", is_gcc)
    print(prep_asm(asm_good, is_gcc))
    print("\n")
    print(
        to_collapsed(
            to_cody_str(
                f"{bad_setting.compiler_config.name}-{bad_setting.rev} -v", is_gcc
            ),
            is_gcc,
        )
    )
    print(to_code(builder.get_verbose_compiler_info(bad_setting, bldr), is_gcc))
    print()
    print(
        to_cody_str(
            f"{good_setting.compiler_config.name}-{good_setting.rev} -v", is_gcc
        )
    )
    print(
        to_collapsed(
            to_code(builder.get_verbose_compiler_info(good_setting, bldr), is_gcc),
            is_gcc,
        )
    )

    gcc_link = "https://gcc.gnu.org/git/?p=gcc.git;a=commit;h="
    # LLVM moved to github so the commits will be automatically
    # created.
    llvm_link = ""
    link_prefix = gcc_link if is_gcc else llvm_link
    print()
    if not is_gcc:
        print("### Bisection")
    bisection_setting = copy.deepcopy(case.bad_setting)
    bisection_setting.rev = cast(str, case.bisection)
    print(f"Started with {link_prefix}{case.bisection}")
    # print("------------------------------------------------")
    print(
        to_cody_str(
            f"{bisection_setting.report_string()} -S -o /dev/stdout case.c", is_gcc
        )
    )
    bisection_asm = replace_rand(builder.get_asm_str(source, bisection_setting, bldr))
    print(prep_asm(bisection_asm, is_gcc))
    # print("------------------------------------------------")
    prebisection_setting = copy.deepcopy(bisection_setting)
    prebisection_setting.rev = bad_repo.rev_to_commit(f"{bisection_setting.rev}~")
    print(f"Previous commit: {link_prefix}{prebisection_setting.rev}")
    print(
        "\n"
        + to_cody_str(
            f"{prebisection_setting.report_string()} -S -o /dev/stdout case.c",
            is_gcc,
        )
    )
    prebisection_asm = replace_rand(
        builder.get_asm_str(source, prebisection_setting, bldr)
    )
    print(prep_asm(prebisection_asm, is_gcc))


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
        _run()
    elif args.sub == "absorb":
        _absorb()
    elif args.sub == "tofile":
        _tofile()
    elif args.sub == "massage" or args.sub == "link":
        _massageorlink()
    elif args.sub == "rereduce":
        _rereduce()
    elif args.sub == "report":
        _report()

    gnrtr.terminate_processes()
