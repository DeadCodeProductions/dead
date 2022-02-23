#!/usr/bin/env python3

import copy
import hashlib
import logging
import os
import random
import re
import subprocess
import sys
import tempfile
import time
from multiprocessing import Pool
from pathlib import Path
from typing import Any, Dict, Optional, cast

import requests

import bisector
import builder
import checker
import database
import generator
import init
import parsers
import patchdatabase
import preprocessing
import reducer
import repository
import utils


def get_llvm_github_commit_author(rev: str) -> Optional[str]:
    html = requests.get(
        "https://github.com/llvm/llvm-project/commit/" + rev
    ).content.decode()
    p = re.compile(r'.*\/llvm\/llvm-project\/commits\?author=(.*)".*')
    for l in html.split("\n"):
        l = l.strip()
        if m := p.match(l):
            return m.group(1)
    return None


def get_all_bisections(ddb: database.CaseDatabase) -> list[str]:
    res = ddb.con.execute("select distinct bisection from cases")
    return [r[0] for r in res]


def _run() -> None:
    scenario = utils.get_scenario(config, args)

    counter = 0
    output_directory = (
        Path(args.output_directory).absolute() if args.output_directory else None
    )

    parallel_generator = (
        gnrtr.parallel_interesting_case(config, scenario, args.cores, start_stop=True)
        if args.parallel_generation
        else None
    )
    pipeline_components = (
        ["Generator<" + "parallel>" if args.parallel_generation else "single>"]
        + (["Bisector"] if args.bisector else [])
        + (["Reducer"] if args.reducer else [])
    )

    print("Pipeline:", " -> ".join(pipeline_components), file=sys.stderr)

    last_update_time = time.time()

    while True:
        if args.amount and args.amount != 0:
            if counter >= args.amount:
                break

        if args.update_trunk_after_X_hours is not None:
            if (
                time.time() - last_update_time
            ) / 3600 > args.update_trunk_after_X_hours:

                logging.info("Updating repositories...")

                last_update_time = time.time()

                known: Dict[str, list[int]] = dict()
                for i, s in enumerate(scenario.target_settings):
                    cname = s.compiler_config.name
                    if cname not in known:
                        known[cname] = []
                    known[cname].append(i)

                for cname, l in known.items():
                    repo = repository.Repo.repo_from_setting(
                        scenario.target_settings[l[0]]
                    )
                    old_trunk_commit = repo.rev_to_commit("trunk")
                    repo.pull()
                    new_trunk_commit = repo.rev_to_commit("trunk")

                    for i in l:
                        if scenario.target_settings[i].rev == old_trunk_commit:
                            scenario.target_settings[i].rev = new_trunk_commit

        # Time db values
        generator_time: Optional[float] = None
        generator_try_count: Optional[int] = None
        bisector_time: Optional[float] = None
        bisector_steps: Optional[int] = None
        reducer_time: Optional[float] = None

        if parallel_generator:
            case = next(parallel_generator)
        else:
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

        if args.reducer is not False:
            if (
                args.reducer
                or case.bisection
                and case.bisection in get_all_bisections(ddb)
            ):
                try:
                    time_start_reducer = time.perf_counter()
                    worked = rdcr.reduce_case(case)
                    time_end_reducer = time.perf_counter()
                    reducer_time = time_end_reducer - time_start_reducer
                except builder.BuildException as e:
                    print(f"BuildException: {e}")
                    continue

        if not output_directory:
            case_id = ddb.record_case(case)
            ddb.record_timing(
                case_id,
                generator_time,
                generator_try_count,
                bisector_time,
                bisector_steps,
                reducer_time,
            )

        else:
            h = abs(hash(str(case)))
            path = output_directory / Path(f"case_{counter:08}-{h:019}.tar")
            logging.debug("Writing case to {path}...")
            case.to_file(path)

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

    if Path(args.absorb_object).is_file():
        read_into_db(Path(args.absorb_object))
        exit(0)
    pool = Pool(10)

    absorb_directory = Path(args.absorb_object).absolute()
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

    massaged_code, _, _ = ddb.get_report_info_from_id(args.case_id)

    if massaged_code:
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

    # Check if bisection commit is what it should be
    print("Checking bisection commit...")
    bisection_setting = copy.deepcopy(cpy.bad_setting)
    bisection_setting.rev = cast(str, cpy.bisection)
    prebisection_setting = copy.deepcopy(bisection_setting)
    repo = repository.Repo.repo_from_setting(bisection_setting)
    prebisection_setting.rev = repo.rev_to_commit(f"{case.bisection}~")

    bis_set = builder.find_alive_markers(cpy.code, bisection_setting, cpy.marker, bldr)
    rebis_set = builder.find_alive_markers(
        cpy.code, prebisection_setting, cpy.marker, bldr
    )

    if not cpy.marker in bis_set or cpy.marker in rebis_set:
        print("Bisection commit is not correct! Aborting...", file=sys.stderr)
        exit(1)

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
        if is_gcc:
            s = (
                "--------- OUTPUT ---------\n"
                + s
                + "\n---------- END OUTPUT ---------\n"
            )
        else:
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
            return code.replace(res, '"case.c"')
        return code

    def replace_file_name_IR(ir: str) -> str:
        head = "; ModuleID = 'case.c'\n" + 'source_filename = "case.c"\n'
        tail = ir.split("\n")[2:]
        ir = head + "\n".join(tail)
        return ir

    def keep_only_main(code: str) -> str:
        lines = list(code.split("\n"))
        first = 0
        for i, line in enumerate(lines):
            if "main:" in line:
                first = i
                break
        last = first + 1
        ex = re.compile(".*.cfi_endproc")
        for i, line in enumerate(lines[last:], start=last):
            if ex.match(line):
                last = i
                break
        return "\n".join(lines[first:last])

    def prep_asm(asm: str, is_gcc: bool) -> str:
        asm = replace_rand(asm)
        asm = keep_only_main(asm)
        asm = to_code(asm, is_gcc, "asm")
        asm = to_collapsed(asm, is_gcc, summary="Reduced assembly")
        return asm

    def prep_IR(ir: str) -> str:
        ir = replace_file_name_IR(ir)
        ir = to_code(ir, False, "ll")
        ir = to_collapsed(ir, False, summary="Emitted IR")
        return ir

    print(
        f"Dead Code Elimination Regression at -O{bad_setting.opt_level} (trunk vs. {good_setting_tag.split('-')[-1]}) {args.case_id}"
    )
    print("---------------")
    print(to_cody_str(f"cat case.c #{args.case_id}", is_gcc))
    print(to_code(source, is_gcc, "c"))

    print(
        f"`{bad_setting_str}` can not eliminate `foo` but `{good_setting_str}` can.\n"
    )

    # Compile
    if is_gcc:
        case.bad_setting.add_flag("-emit-llvm")
        good_setting.add_flag("-emit-llvm")
        asm_bad = builder.get_asm_str(source, case.bad_setting, bldr)
        asm_good = builder.get_asm_str(source, good_setting, bldr)

        print_cody_str(f"{bad_setting_str} -S -o /dev/stdout case.c", is_gcc)
        print(prep_asm(asm_bad, is_gcc))
        print()

        print_cody_str(f"{good_setting_str} -S -o /dev/stdout case.c", is_gcc)
        print(prep_asm(asm_good, is_gcc))
        print()
        print(
            "Bisects to: https://gcc.gnu.org/git/?p=gcc.git;a=commit;h="
            + str(case.bisection)
        )
        print()
        print("----- Build information -----")
        print(f"----- {bad_setting_tag}")
        print(
            builder.get_verbose_compiler_info(bad_setting, bldr).split("lto-wrapper\n")[
                -1
            ]
        )
        print(f"\n----- {good_setting_tag}")
        print(
            builder.get_verbose_compiler_info(good_setting, bldr).split(
                "lto-wrapper\n"
            )[-1]
        )

    else:

        print("Target: `x86_64-unknown-linux-gnu`")
        ir_bad = builder.get_llvm_IR(source, case.bad_setting, bldr)
        ir_good = builder.get_llvm_IR(source, good_setting, bldr)

        asm_bad = builder.get_asm_str(source, case.bad_setting, bldr)
        asm_good = builder.get_asm_str(source, good_setting, bldr)
        print("\n------------------------------------------------\n")
        print_cody_str(
            f"{bad_setting_str} [-emit-llvm] -S -o /dev/stdout case.c", is_gcc
        )
        print(prep_IR(ir_bad))
        print()
        print(prep_asm(asm_bad, is_gcc))
        print()
        print("\n------------------------------------------------\n")
        print_cody_str(
            f"{good_setting_str} [-emit-llvm] -S -o /dev/stdout case.c", is_gcc
        )
        print()
        print(prep_IR(ir_good))
        print()
        print(prep_asm(asm_good, is_gcc))

        print("\n------------------------------------------------\n")
        print("### Bisection")
        bisection_setting = copy.deepcopy(case.bad_setting)
        bisection_setting.rev = cast(str, case.bisection)
        print(f"Bisected to: {case.bisection}")
        author = get_llvm_github_commit_author(cast(str, case.bisection))
        if author:
            print(f"Committed by: @{author}")
        print("\n------------------------------------------------\n")
        bisection_asm = builder.get_asm_str(source, bisection_setting, bldr)
        bisection_ir = builder.get_llvm_IR(source, bisection_setting, bldr)
        print(
            to_cody_str(
                f"{bisection_setting.report_string()} [-emit-llvm] -S -o /dev/stdout case.c",
                is_gcc,
            )
        )
        print(prep_IR(bisection_ir))
        print()
        print(prep_asm(bisection_asm, is_gcc))

        print("\n------------------------------------------------\n")
        prebisection_setting = copy.deepcopy(bisection_setting)
        prebisection_setting.rev = bad_repo.rev_to_commit(f"{bisection_setting.rev}~")
        print(f"Previous commit: {prebisection_setting.rev}")
        print(
            "\n"
            + to_cody_str(
                f"{prebisection_setting.report_string()} [-emit-llvm] -S -o /dev/stdout case.c",
                is_gcc,
            )
        )
        prebisection_asm = builder.get_asm_str(source, prebisection_setting, bldr)
        prebisection_ir = builder.get_llvm_IR(source, prebisection_setting, bldr)
        print()
        print(prep_IR(prebisection_ir))
        print()
        print(prep_asm(prebisection_asm, is_gcc))

    with open("case.txt", "w") as f:
        f.write(source)
    print("Saved case.txt...", file=sys.stderr)


def _diagnose() -> None:
    width = 50

    def ok_fail(b: bool) -> str:
        if b:
            return "OK"
        else:
            return "FAIL"

    def nice_print(name: str, value: str) -> None:
        print(("{:.<" f"{width}}}").format(name), value)

    if args.case_id:
        case = ddb.get_case_from_id_or_die(args.case_id)
    else:
        case = utils.Case.from_file(config, Path(args.file))

    repo = repository.Repo(
        case.bad_setting.compiler_config.repo,
        case.bad_setting.compiler_config.main_branch,
    )

    def sanitize_values(
        config: utils.NestedNamespace,
        case: utils.Case,
        prefix: str,
        chkr: checker.Checker,
    ) -> None:
        empty_body_code = chkr._emtpy_marker_code_str(case)
        with tempfile.NamedTemporaryFile(suffix=".c") as tf:
            with open(tf.name, "w") as f:
                f.write(empty_body_code)
                res_comp_warnings = checker.check_compiler_warnings(
                    config.gcc.sane_version,
                    config.llvm.sane_version,
                    Path(tf.name),
                    case.bad_setting.get_flag_str(),
                    10,
                )
                nice_print(
                    prefix + "Sanity: compiler warnings",
                    ok_fail(res_comp_warnings),
                )
                res_use_ub_san = checker.use_ub_sanitizers(
                    config.llvm.sane_version,
                    Path(tf.name),
                    case.bad_setting.get_flag_str(),
                    10,
                    10,
                )
                nice_print(
                    prefix + "Sanity: undefined behaviour", ok_fail(res_use_ub_san)
                )
                res_ccomp = checker.verify_with_ccomp(
                    config.ccomp,
                    Path(tf.name),
                    case.bad_setting.get_flag_str(),
                    10,
                )
                nice_print(
                    prefix + "Sanity: ccomp",
                    ok_fail(res_ccomp),
                )

    def checks(case: utils.Case, prefix: str) -> None:
        nice_print(
            prefix + "Check marker", ok_fail(chkr.is_interesting_wrt_marker(case))
        )
        nice_print(prefix + "Check CCC", ok_fail(chkr.is_interesting_wrt_ccc(case)))
        nice_print(
            prefix + "Check static. annotated",
            ok_fail(chkr.is_interesting_with_static_globals(case)),
        )
        res_empty = chkr.is_interesting_with_empty_marker_bodies(case)
        nice_print(prefix + "Check empty bodies", ok_fail(res_empty))
        if not res_empty:
            sanitize_values(config, case, prefix, chkr)

    print(("{:=^" f"{width}}}").format(" Values "))

    nice_print("Marker", case.marker)
    nice_print("Code lenght", str(len(case.code)))
    nice_print("Bad Setting", str(case.bad_setting))
    same_opt = [
        gs for gs in case.good_settings if gs.opt_level == case.bad_setting.opt_level
    ]
    nice_print(
        "Newest Good Setting",
        str(utils.get_latest_compiler_setting_from_list(repo, same_opt)),
    )

    checks(case, "")
    cpy = copy.deepcopy(case)
    if not (
        code_pp := preprocessing.preprocess_csmith_code(
            case.code, utils.get_marker_prefix(case.marker), case.bad_setting, bldr
        )
    ):
        print("Code could not be preprocessed. Skipping perprocessed checks")
    else:
        cpy.code = code_pp
        checks(cpy, "PP: ")

    if case.reduced_code:
        cpy = copy.deepcopy(case)
        cpy.code = case.reduced_code
        checks(cpy, "Reduced: ")

    if args.case_id:
        massaged_code, _, _ = ddb.get_report_info_from_id(args.case_id)
        if massaged_code:
            cpy.code = massaged_code
            checks(cpy, "Massaged: ")

    if case.bisection:
        cpy = copy.deepcopy(case)
        nice_print("Bisection", case.bisection)
        prev_rev = repo.rev_to_commit(case.bisection + "~")
        nice_print("Bisection prev commit", prev_rev)
        bis_res_og = chkr.is_interesting(cpy, preprocess=False)
        cpy.bad_setting.rev = prev_rev
        bis_prev_res_og = chkr.is_interesting(cpy, preprocess=False)

        nice_print(
            "Bisection test original code", ok_fail(bis_res_og and not bis_prev_res_og)
        )
        cpy = copy.deepcopy(case)
        if cpy.reduced_code:
            cpy.code = cpy.reduced_code
            bis_res = chkr.is_interesting(cpy, preprocess=False)
            cpy.bad_setting.rev = prev_rev
            bis_prev_res = chkr.is_interesting(cpy, preprocess=False)
            nice_print(
                "Bisection test reduced code", ok_fail(bis_res and not bis_prev_res)
            )

    if case.reduced_code:
        print(case.reduced_code)


def _check_reduced() -> None:
    """Check code against every good and bad setting of a case.

    Args:

    Returns:
        None:
    """

    def ok_fail(b: bool) -> str:
        if b:
            return "OK"
        else:
            return "FAIL"

    def nice_print(name: str, value: str) -> None:
        width = 100
        print(("{:.<" f"{width}}}").format(name), value)

    with open(args.code_path, "r") as f:
        new_code = f.read()

    case = ddb.get_case_from_id_or_die(args.case_id)

    prefix = utils.get_marker_prefix(case.marker)
    bad_alive = builder.find_alive_markers(new_code, case.bad_setting, prefix, bldr)
    nice_print(f"Bad {case.bad_setting}", ok_fail(case.marker in bad_alive))

    for gs in case.good_settings:
        good_alive = builder.find_alive_markers(new_code, gs, prefix, bldr)
        nice_print(f"Good {gs}", ok_fail(case.marker not in good_alive))

    case.code = new_code
    case.reduced_code = new_code
    nice_print("Check", ok_fail(chkr.is_interesting(case, preprocess=False)))
    # Useful when working with watch -n 0 to see that something happened
    print(random.randint(0, 1000))


def _cache() -> None:
    if args.what == "clean":
        print("Cleaning...")
        for c in Path(config.cachedir).iterdir():
            if not (c / "DONE").exists():
                try:
                    os.rmdir(c)
                except FileNotFoundError:
                    print(c, "spooky. It just disappeared...")
                except OSError:
                    print(c, "is not empty but also not done!")
        print("Done")
    elif args.what == "stats":
        count_gcc = 0
        count_clang = 0
        for c in Path(config.cachedir).iterdir():
            if c.name.startswith("clang"):
                count_clang += 1
            else:
                count_gcc += 1

        tot = count_gcc + count_clang
        print("Amount compilers:", tot)
        print("Amount clang: {} {:.2f}%".format(count_clang, count_clang / tot * 100))
        print("Amount GCC: {} {:.2f}%".format(count_gcc, count_gcc / tot * 100))


def _asm() -> None:
    def save_wrapper(name: str, content: str) -> None:
        utils.save_to_file(Path(name + ".s"), content)
        print(f"Saving {name + '.s'}...")

    case = ddb.get_case_from_id_or_die(args.case_id)
    bad_repo = repository.Repo(
        case.bad_setting.compiler_config.repo,
        case.bad_setting.compiler_config.main_branch,
    )

    same_opt = [
        gs for gs in case.good_settings if gs.opt_level == case.bad_setting.opt_level
    ]
    good_setting = utils.get_latest_compiler_setting_from_list(bad_repo, same_opt)

    asmbad = builder.get_asm_str(case.code, case.bad_setting, bldr)
    asmgood = builder.get_asm_str(case.code, good_setting, bldr)
    save_wrapper("asmbad", asmbad)
    save_wrapper("asmgood", asmgood)

    if case.reduced_code:
        reducedasmbad = builder.get_asm_str(case.reduced_code, case.bad_setting, bldr)
        reducedasmgood = builder.get_asm_str(case.reduced_code, good_setting, bldr)
        save_wrapper("reducedasmbad", reducedasmbad)
        save_wrapper("reducedasmgood", reducedasmgood)
    if case.bisection:
        bisection_setting = copy.deepcopy(case.bad_setting)
        bisection_setting.rev = case.bisection

        asmbisect = builder.get_asm_str(case.code, bisection_setting, bldr)
        save_wrapper("asmbisect", asmbisect)
        if case.reduced_code:
            reducedasmbisect = builder.get_asm_str(
                case.reduced_code, bisection_setting, bldr
            )
            save_wrapper("reducedasmbisect", reducedasmbisect)
    print(case.marker)


def _get() -> None:
    # Why are you printing code with end=""?
    case_id: int = int(args.case_id)
    if args.what in ["ocode", "rcode", "bisection"]:
        case = ddb.get_case_from_id_or_die(args.case_id)
        if args.what == "ocode":
            print(case.code, end="")
            return
        elif args.what == "rcode":
            print(case.reduced_code, end="")
            return
        elif args.what == "bisection":
            print(case.bisection, end="")
            return
    else:
        mcode, link, fixed = ddb.get_report_info_from_id(case_id)
        if args.what == "link":
            print(link)
            return
        elif args.what == "fixed":
            print(fixed)
            return
        elif args.what == "mcode":
            print(mcode, end="")
            return

    logging.warning(
        "Whoops, this should not have"
        " happened because the parser forces "
        "`what` to only allow some strings."
    )
    return


def _set() -> None:
    case_id: int = int(args.case_id)
    case = ddb.get_case_from_id_or_die(case_id)
    mcode, link, fixed = ddb.get_report_info_from_id(case_id)
    repo = repository.Repo(
        case.bad_setting.compiler_config.repo,
        case.bad_setting.compiler_config.main_branch,
    )

    if args.what == "ocode":
        with open(args.var, "r") as f:
            new_code = f.read()
        case.code = new_code
        if chkr.is_interesting(case):
            ddb.update_case(case_id, case)
        else:
            logging.critical(
                "The provided code is not interesting wrt to the case. Will not save!"
            )
            exit(1)
        return
    elif args.what == "rcode":
        if args.var == "null":
            print("Old reduced_code:")
            print(case.reduced_code)
            case.reduced_code = None
            ddb.update_case(case_id, case)
            return

        with open(args.var, "r") as f:
            rcode = f.read()
        old_code = case.code
        case.code = rcode
        if chkr.is_interesting(case):
            case.code = old_code
            case.reduced_code = rcode
            ddb.update_case(case_id, case)
        else:
            logging.critical(
                "The provided code is not interesting wrt to the case. Will not save!"
            )
            exit(1)
        return
    elif args.what == "bisection":
        if args.var == "null":
            print("Old bisection:", case.bisection)
            case.bisection = None
            ddb.update_case(case_id, case)
            return

        # Also acts as check that the given rev is ok
        rev = repo.rev_to_commit(args.var)
        # Just in case someone accidentally overrides things...
        logging.info(f"Previous bisection for case {case_id}: {case.bisection}")
        case.bisection = rev
        ddb.update_case(case_id, case)
        return
    elif args.what == "link":
        if args.var == "null":
            print("Old link:", link)
            ddb.record_reported_case(case_id, mcode, None, fixed)
            return
        tmp: str = args.var
        tmp = tmp.strip()
        ddb.record_reported_case(case_id, mcode, tmp, fixed)
        return
    elif args.what == "fixed":
        if args.var == "null":
            print("Old fixed:", fixed)
            ddb.record_reported_case(case_id, mcode, link, None)
            return

        rev = repo.rev_to_commit(args.var)

        case.bad_setting.rev = rev
        if not chkr.is_interesting(case):
            ddb.record_reported_case(case_id, mcode, link, rev)
            print("Fixed")
        else:
            logging.critical(f"Case {case_id} was not fixed by {args.var}! Not saving!")
            exit(1)
        return
    elif args.what == "mcode":
        if args.var == "null":
            print("Old massaged code:")
            print(mcode)
            ddb.record_reported_case(case_id, None, link, fixed)
            return

        if not case.bisection:
            logging.fatal(
                "Can not save massaged code to a case that is not bisected. Bad things could happen. Stopping..."
            )
            exit(1)
        with open(args.var, "r") as f:
            new_mcode = f.read()
        old_bisection = case.bisection
        case.code = new_mcode
        if chkr.is_interesting(case):
            print("Checking bisection...")
            if not bsctr.bisect_case(case, force=True):
                logging.critical("Checking bisection failed...")
                exit(1)
            if case.bisection != old_bisection:
                logging.critical(
                    "Bisection of provided massaged code does not match the original bisection!"
                )
                exit(1)
            ddb.record_reported_case(case_id, new_mcode, link, fixed)
        else:
            logging.critical("The provided massaged code is not interesting!")
            exit(1)

        return

    logging.warning(
        "Whoops, this should not have"
        " happened because the parser forces "
        "`what` to only allow some strings."
    )
    return


def _build() -> None:
    compiler_config = utils.get_compiler_config(config, args.project)
    additional_patches: list[Path] = []
    if args.add_patches:
        additional_patches = [Path(patch).absolute() for patch in args.add_patches]
    for rev in args.rev:
        print(
            bldr.build(
                compiler_config,
                rev,
                additional_patches=additional_patches,
                force=args.force,
            )
        )


def _reduce() -> None:
    for i, case_id in enumerate(args.case_id):
        print(f"Reducing {case_id}. Done {i}/{len(args.case_id)}", file=sys.stderr)
        pre_case = ddb.get_case_from_id(case_id)
        if not pre_case:
            if len(args.case_id) == 1:
                print(f"Case ID {case_id} is not known. Aborting...", file=sys.stderr)
                exit(1)
            else:
                print(f"Case ID {case_id} is not known. Continuing...", file=sys.stderr)

            continue
        else:
            case = pre_case
        start_time = time.perf_counter()
        if rdcr.reduce_case(case, force=args.force):
            ddb.update_case(case_id, case)
            reducer_time = time.perf_counter() - start_time
            # If the reduction takes less than 5 seconds,
            # we can assume that the reduction was already done
            if reducer_time > 5.0:
                gtime, gtc, b_time, b_steps, _ = ddb.get_timing_from_id(case_id)
                ddb.record_timing(case_id, gtime, gtc, b_time, b_steps, reducer_time)
        else:
            print(f"{case_id} failed...", file=sys.stderr)
    print("Done")


def _bisect() -> None:
    for i, case_id in enumerate(args.case_id):
        print(f"Bisecting {case_id}. Done {i}/{len(args.case_id)}", file=sys.stderr)
        pre_case = ddb.get_case_from_id(case_id)
        if not pre_case:
            if len(args.case_id) == 1:
                print(f"Case ID {case_id} is not known. Aborting...", file=sys.stderr)
                exit(1)
            else:
                print(f"Case ID {case_id} is not known. Continuing...", file=sys.stderr)
            continue
        else:
            case = pre_case
        start_time = time.perf_counter()
        if bsctr.bisect_case(case, force=args.force):
            ddb.update_case(case_id, case)
            bisector_time = time.perf_counter() - start_time
            # if the bisection took less than 5 seconds
            # we can assume that it was already bisected
            if bisector_time > 5.0:
                gtime, gtc, _, _, rtime = ddb.get_timing_from_id(case_id)
                ddb.record_timing(
                    case_id, gtime, gtc, bisector_time, bsctr.steps, rtime
                )
        else:
            print(f"{case_id} failed...", file=sys.stderr)
    print("Done", file=sys.stderr)


def _edit() -> None:
    if "EDITOR" not in os.environ:
        print("Did not find EDITOR variable. Using nano...", file=sys.stderr)
        subprocess.run(["nano", config.config_path])
    else:
        subprocess.run(os.environ["EDITOR"].split(" ") + [config.config_path])


def _unreported() -> None:

    query = """
        WITH exclude_bisections AS (
        select distinct bisection from reported_cases join cases on cases.case_id = reported_cases.case_id
            where fixed_by is not NULL
                or bug_report_link is not NULL
        )
    """

    if args.good_version or args.OX_only:
        query += f"""
        ,concrete_good AS (
          select case_id from good_settings join compiler_setting on good_settings.compiler_setting_id = compiler_setting.compiler_setting_id
          where 1 
        """

        if args.good_version:
            gcc_repo = repository.Repo(config.gcc.repo, config.gcc.main_branch)
            llvm_repo = repository.Repo(config.llvm.repo, config.llvm.main_branch)

            try:
                rev = gcc_repo.rev_to_commit(args.good_version)
            except:
                rev = llvm_repo.rev_to_commit(args.good_version)
            query += f" and rev = '{rev}'"

        query += ")"

    query += """
    select MIN(cases.case_id), bisection, count(bisection) as cnt from cases
    join compiler_setting on cases.bad_setting_id = compiler_setting.compiler_setting_id
    """
    if args.good_version:
        query += "\njoin concrete_good on cases.case_id = concrete_good.case_id\n"

    if args.reduced or args.not_reduced:
        query += "\nleft join reported_cases on cases.case_id = reported_cases.case_id"

    query += """
    where bisection not in exclude_bisections
    """
    if args.clang_only:
        query += "\nand compiler = 'clang'"
    elif args.gcc_only:
        query += "\nand compiler = 'gcc'"

    if args.OX_only:
        query += f" and opt_level = '{args.OX_only}'"

    query += "\ngroup by bisection"

    if args.reduced:
        query += "\n having reduced_code_sha1 is not null "
    elif args.not_reduced:
        query += "\n having reduced_code_sha1 is null "

    query += "\norder by cnt desc"

    res = ddb.con.execute(query).fetchall()

    if res[-1][1] is None:
        res = res[:-1]

    if args.id_only:
        for case_id, _, _ in res:
            print(case_id)
    else:
        print("{: <8} {: <45} {}".format("ID", "Bisection", "Count"))
        print("{:-<64}".format(""))
        for case_id, bisection, count in res:
            print("{: <8} {: <45} {}".format(case_id, bisection, count))
        print("{:-<64}".format(""))
        print("{: <8} {: <45} {}".format("ID", "Bisection", "Count"))


def _reported() -> None:

    query = """
    with rep as (	
        select cases.case_id, bisection, bug_report_link from cases 
        join compiler_setting on bad_setting_id = compiler_setting_id 
        left join reported_cases on cases.case_id = reported_cases.case_id  
        where bug_report_link is not null order by cases.case_id
    )

    select rep.case_id, bisection, bug_report_link 
    """

    if args.good_settings:
        query += """, compiler_setting.compiler, compiler_setting.rev, compiler_setting.opt_level 
        from rep
        left join good_settings on rep.case_id = good_settings.case_id
        left join compiler_setting on good_settings.compiler_setting_id = compiler_setting.compiler_setting_id
        """
    else:
        query += " from rep"

    query += " where 1 "
    if args.clang_only or args.llvm_only:
        query += " and compiler = 'clang'"
    elif args.gcc_only:
        query += " and compiler = 'gcc'"

    query += " order by rep.case_id"

    res = ddb.con.execute(query).fetchall()

    if args.id_only:
        for case_id, _, _ in res:
            print(case_id)
    elif args.good_settings:

        gcc_repo = repository.Repo(config.gcc.repo, config.gcc.main_branch)
        llvm_repo = repository.Repo(config.llvm.repo, config.llvm.main_branch)
        print(
            "{: <8} {: <45} {: <45} {}".format(
                "ID", "Bisection", "Good Settings", "Link"
            )
        )
        last_case_id = -1
        for case_id, bisection, link, name, rev, opt_level in res:

            if name == "gcc":
                maybe_tag = gcc_repo.rev_to_tag(rev)
            else:
                maybe_tag = llvm_repo.rev_to_tag(rev)
            nice_rev = maybe_tag if maybe_tag else rev

            comp_str = f"{name}-{nice_rev} -O{opt_level}"
            if last_case_id != case_id:
                last_case_id = case_id
                print("{:-<155}".format(""))
                print(
                    "{: <8} {: <45} {: <45} {}".format(
                        case_id, bisection, comp_str, link
                    )
                )
            else:
                print("{: <8} {: <45} {: <45} {}".format("", "", comp_str, ""))

        print("{:-<155}".format(""))
        print(
            "{: <8} {: <45} {: <45} {}".format(
                "ID", "Bisection", "Good Settings", "Link"
            )
        )

    else:
        print("{: <8} {: <45} {}".format("ID", "Bisection", "Link"))
        print("{:-<110}".format(""))
        for case_id, bisection, link in res:
            print("{: <8} {: <45} {}".format(case_id, bisection, link))
        print("{:-<110}".format(""))
        print("{: <8} {: <45} {}".format("ID", "Bisection", "Link"))


def _findby() -> None:

    if args.what == "link":
        link_query = "SELECT case_id FROM reported_cases WHERE bug_report_link = ?"
        res = ddb.con.execute(link_query, (args.var.strip(),)).fetchall()
        for r in res:
            print(r[0])
        return
    elif args.what == "fixed":
        query = "SELECT case_id FROM reported_cases WHERE fixed_by = ?"
        res = ddb.con.execute(query, (args.var.strip(),)).fetchall()
        for r in res:
            print(r[0])
        return
    elif args.what == "case":
        case = utils.Case.from_file(config, Path(args.var))
        code_sha1 = hashlib.sha1(case.code.encode("utf-8")).hexdigest()
        # Try if we have any luck with just using code
        code_query = "SELECT cases.case_id FROM cases LEFT OUTER JOIN reported_cases ON cases.case_id = reported_cases.case_id WHERE code_sha1 = ? OR reduced_code_sha1 = ? OR massaged_code_sha1 = ?"
        res_ocode = ddb.con.execute(
            code_query, (code_sha1, code_sha1, code_sha1)
        ).fetchall()

        possible = set([i[0] for i in res_ocode])
        if case.reduced_code:
            rcode_sha1 = hashlib.sha1(case.reduced_code.encode("utf-8")).hexdigest()
            res_ocode = ddb.con.execute(
                code_query, (rcode_sha1, rcode_sha1, rcode_sha1)
            ).fetchall()
            possible.update([i[0] for i in res_ocode])

        if case.bisection:
            other = ddb.con.execute(
                "SELECT case_id FROM cases WHERE marker = ? AND bisection = ?",
                (case.marker, case.bisection),
            ).fetchall()
        else:
            other = ddb.con.execute(
                "SELECT case_id FROM cases WHERE marker = ?", (case.marker)
            ).fetchall()

        if len(possible) > 0:
            possible = possible.intersection([i[0] for i in other])
        else:
            possible = set([i[0] for i in other])

        for i in possible:
            print(i)
        return

    elif args.what == "code":
        with open(args.var, "r") as f:
            code = f.read()

        code_sha1 = hashlib.sha1(code.encode("utf-8")).hexdigest()

        res = ddb.con.execute(
            "SELECT cases.case_id FROM cases LEFT OUTER JOIN reported_cases ON cases.case_id = reported_cases.case_id WHERE code_sha1 = ? OR reduced_code_sha1 = ? OR massaged_code_sha1 = ?",
            (code_sha1, code_sha1, code_sha1),
        ).fetchall()

        for i in res:
            print(i[0])
        return
    return


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
    elif args.sub == "get":
        _get()
    elif args.sub == "set":
        _set()
    elif args.sub == "absorb":
        _absorb()
    elif args.sub == "tofile":
        _tofile()
    elif args.sub == "rereduce":
        _rereduce()
    elif args.sub == "report":
        _report()
    elif args.sub == "diagnose":
        if not args.case_id and not args.file:
            print("Need a file or a case id to work with", file=sys.stderr)
        _diagnose()
    elif args.sub == "checkreduced":
        _check_reduced()
    elif args.sub == "cache":
        _cache()
    elif args.sub == "asm":
        _asm()
    elif args.sub == "build":
        _build()
    elif args.sub == "reduce":
        _reduce()
    elif args.sub == "bisect":
        _bisect()
    elif args.sub == "edit":
        _edit()
    elif args.sub == "unreported":
        _unreported()
    elif args.sub == "reported":
        _reported()
    elif args.sub == "findby":
        _findby()
    elif args.sub == "init":
        init.main()

    gnrtr.terminate_processes()
