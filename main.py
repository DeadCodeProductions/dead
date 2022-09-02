#!/usr/bin/env python3

import copy
import hashlib
import json
import logging
import os
import random
import re
import subprocess
import sys
import tempfile
import time
import urllib.parse
from multiprocessing import Pool
from pathlib import Path
from typing import Any, Dict, Optional, cast

import ccbuilder
import requests
from ccbuilder import (
    Builder,
    BuildException,
    PatchDB,
    Repo,
    get_gcc_repo,
    get_llvm_repo,
    CompilerProject,
)

import parsers
import utils

from dead.utils import (
    DeadConfig,
    RegressionCase,
    repo_from_setting,
    old_scenario_to_new_scenario,
    get_verbose_compiler_info,
    get_llvm_IR,
    setting_report_str,
)
import dead.database as database
from dead.generator import generate_interesting_cases
from dead.bisector import bisect_case
from dead.reducer import reduce_case
from dead.checker import Checker, find_alive_markers
from dead.diagnose import diagnose_case

from diopter import compiler
from diopter import bisector
from diopter import reducer


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


def check_llvm_issues(rev: str) -> bool:
    print(f"Looking for existing issues...", end="", file=sys.stderr)
    url_pre = f"https://api.github.com/search/issues?q={rev} repo:llvm/llvm-project"
    open_issues = json.loads(requests.get(url_pre + " is:open").content)
    closed_issues = json.loads(requests.get(url_pre + " is:closed").content)
    issues = open_issues["items"] + closed_issues["items"]
    if issues:
        print(
            f"!!!\nWarning: The following issues already contain the revision {rev}!",
            file=sys.stderr,
        )
        for issue in issues:
            print(issue["html_url"], file=sys.stderr)
        return False
    print(f"found none", file=sys.stderr)
    return True


def check_gcc_issues(rev: str) -> bool:
    print(f"Looking for existing issues...", end="", file=sys.stderr)
    url_pre = f"https://gcc.gnu.org/bugzilla/rest/bug?quicksearch={rev}"
    issues = json.loads(requests.get(url_pre).content)["bugs"]
    if issues:
        print(
            f"!!!\nWarning: The following issues already contain the revision {rev}!",
            file=sys.stderr,
        )
        for issue in issues:
            print(
                f"https://gcc.gnu.org/bugzilla/show_bug.cgi?id={issue['id']}",
                file=sys.stderr,
            )
        return False
    print(f"found none", file=sys.stderr)
    return True


def get_all_bisections(ddb: database.CaseDatabase) -> list[str]:
    res = ddb.con.execute("select distinct bisection from cases")
    return [r[0] for r in res]


def update_trunk(last_update_time: float, scenario: utils.Scenario) -> float:
    if (time.time() - last_update_time) / 3600 > args.update_trunk_after_X_hours:

        logging.info("Updating repositories...")

        last_update_time = time.time()

        known: Dict[str, list[int]] = dict()
        for i, s in enumerate(scenario.target_settings):
            cname = s.compiler_project.name
            if cname not in known:
                known[cname] = []
            known[cname].append(i)

        for cname, l in known.items():
            repo = scenario.target_settings[l[0]].repo
            old_trunk_commit = repo.rev_to_commit("trunk")
            repo.pull()
            new_trunk_commit = repo.rev_to_commit("trunk")

            for i in l:
                if scenario.target_settings[i].rev == old_trunk_commit:
                    scenario.target_settings[i].rev = new_trunk_commit
    return last_update_time


def _run() -> None:
    scenario = utils.get_scenario(config, args)

    counter = 0
    output_directory = (
        Path(args.output_directory).absolute() if args.output_directory else None
    )

    pipeline_components = (
        ["Generator<parallel>"]
        + (["Bisector"] if args.bisector else [])
        + (
            ["Reducer<Only New>"]
            if args.reducer is None
            else (["Reducer<Always>"] if args.reducer == True else [])
        )
    )

    print("Pipeline:", " -> ".join(pipeline_components), file=sys.stderr)

    last_update_time = time.time()

    while True:
        if args.amount and args.amount != 0:
            if counter >= args.amount:
                break

        if args.update_trunk_after_X_hours is not None:
            last_update_time = update_trunk(last_update_time, scenario)

        for case_ in generate_interesting_cases(
            old_scenario_to_new_scenario(scenario, bldr), args.cores, 1024
        ):
            print("FOUND A CASE")
            if args.bisector:
                try:
                    if not bisect_case(case_, bsctr, bldr):
                        print("Bisection failed")
                        continue
                except bisector.BisectionException as e:
                    print(f"BisectionException: '{e}'", file=sys.stderr)
                    continue
                except AssertionError as e:
                    print(f"AssertionError: '{e}'", file=sys.stderr)
                    continue
                except BuildException as e:
                    print(f"BuildException: '{e}'", file=sys.stderr)
                    continue

            if args.reducer is not False:
                if (
                    args.reducer
                    or case_.bisection
                    and not case_.bisection in get_all_bisections(ddb)
                ):
                    try:
                        # XXX: we don't really need to pass the checker here
                        worked = reduce_case(case_, rdcr, chkr)
                    except BuildException as e:
                        print(f"BuildException: {e}")
                        continue

            if not output_directory:
                case_id = ddb.record_case(case_)
            else:
                h = abs(hash(str(case_)))
                path = output_directory / Path(f"case_{counter:08}-{h:019}.tar")
                logging.debug("Writing case to {path}...")
                case_.to_file(path)

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
        case = RegressionCase.from_file(config, file)
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
    case.code = rereduce_code
    print(f"Re-reducing code with respect to Case {args.case_id}", file=sys.stderr)
    if reduce_case(
        case,
        rdcr,
        chkr,
        force=True,
        preprocess=False,
    ):
        print(case.reduced_code)
    else:
        print("Could not reduce code")


def _report() -> None:
    pre_check_case = ddb.get_case_from_id(args.case_id)
    if not pre_check_case:
        print("No case with this ID.", file=sys.stderr)
        exit(1)
    else:
        case = pre_check_case

    if not case.bisection:
        print("Case is not bisected. Starting bisection...", file=sys.stderr)
        try:
            worked = bisect_case(case, bsctr, bldr)
        except bisector.BisectionException as e:
            print(f"BisectionException: '{e}'", file=sys.stderr)
            worked = False
        except AssertionError as e:
            print(f"AssertionError: '{e}'", file=sys.stderr)
            worked = False
        except BuildException as e:
            print(f"BuildException: '{e}'", file=sys.stderr)
            worked = False

        if worked:
            ddb.update_case(args.case_id, case)
        else:
            print("Could not bisect case. Aborting...", file=sys.stderr)
            exit(1)

    # check for reduced and massaged code
    if not case.reduced_code:
        print("Case is not reduced. Starting reduction...", file=sys.stderr)
        if reduce_case(case, rdcr, chkr):
            ddb.update_case(args.case_id, case)
        else:
            print("Could not reduce case. Aborting...", file=sys.stderr)
            exit(1)

    massaged_code, _, _ = ddb.get_report_info_from_id(args.case_id)

    if massaged_code:
        case.reduced_code = massaged_code

    bad_setting = case.bad_setting
    bad_repo = repo_from_setting(bad_setting)
    is_gcc: bool = bad_setting.compiler.project == ccbuilder.CompilerProject.GCC

    # Last sanity check
    cpy = copy.deepcopy(case)
    cpy.code = cast(str, case.reduced_code)
    print("Normal interestingness test...", end="", file=sys.stderr, flush=True)
    if not chkr.is_interesting_case(cpy, preprocess=False, make_globals_static=False):
        print("\nCase is not interesting! Aborting...", file=sys.stderr)
        exit(1)
    else:
        print("OK", file=sys.stderr)

    # Check against newest upstream
    if args.pull:
        print("Pulling Repo...", file=sys.stderr)
        bad_repo.pull()
    print("Interestingness test against main...", end="", file=sys.stderr)
    cpy.bad_setting = cpy.bad_setting.with_revision(
        bad_repo.rev_to_commit(bad_repo.main_branch), bldr
    )
    if not chkr.is_interesting_case(cpy, preprocess=False, make_globals_static=False):
        print(
            "\nCase is not interesting on main! Might be fixed. Stopping...",
            file=sys.stderr,
        )
        exit(0)
    else:
        print("OK", file=sys.stderr)
        # Use newest main in report
        case.bad_setting = cpy.bad_setting

    # Check if bisection commit is what it should be
    print("Checking bisection commit...", file=sys.stderr)
    marker_prefix = utils.get_marker_prefix(case.marker)
    assert cpy.bisection, "No bisection commit found"
    bisection_setting = copy.deepcopy(cpy.bad_setting).with_revision(
        cpy.bisection, bldr
    )
    prebisection_setting = copy.deepcopy(bisection_setting).with_revision(
        repo_from_setting(bisection_setting).rev_to_commit(f"{case.bisection}~"), bldr
    )

    bis_set = find_alive_markers(cpy.code, bisection_setting, marker_prefix)
    rebis_set = find_alive_markers(cpy.code, prebisection_setting, marker_prefix)

    if not cpy.marker in bis_set or cpy.marker in rebis_set:
        print("Bisection commit is not correct! Aborting...", file=sys.stderr)
        exit(1)

    good_setting = case.good_setting

    # Replace markers
    source = cpy.code.replace(cpy.marker, "foo").replace(
        utils.get_marker_prefix(cpy.marker), "bar"
    )

    bad_setting_tag = bad_setting.compiler.revision + " (trunk)"
    bad_setting_str = (
        f"{bad_setting.compiler.project}-{bad_setting_tag} -O{bad_setting.opt_level}"
    )

    tmp = bad_repo.rev_to_tag(good_setting.compiler.revision)
    if not tmp:
        good_setting_tag = good_setting.compiler.revision
    else:
        good_setting_tag = tmp
    good_setting_str = (
        f"{good_setting.compiler.project}-{good_setting_tag} -O{good_setting.opt_level}"
    )

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
        asm_bad = case.bad_setting.get_asm_from_code(source)
        asm_good = good_setting.get_asm_from_code(source)

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
        print(get_verbose_compiler_info(bad_setting).split("lto-wrapper\n")[-1])
        print(f"\n----- {good_setting_tag}")
        print(get_verbose_compiler_info(good_setting).split("lto-wrapper\n")[-1])

    else:

        print("Target: `x86_64-unknown-linux-gnu`")
        ir_bad = get_llvm_IR(source, case.bad_setting)
        ir_good = get_llvm_IR(source, good_setting)

        asm_bad = case.bad_setting.get_asm_from_code(source)
        asm_good = good_setting.get_asm_from_code(source)
        print("\n------------------------------------------------\n")
        print_cody_str(f"{bad_setting_str} -emit-llvm -S -o /dev/stdout case.c", is_gcc)
        print(prep_IR(ir_bad))
        print()
        print("\n------------------------------------------------\n")
        print_cody_str(
            f"{good_setting_str} -emit-llvm -S -o /dev/stdout case.c", is_gcc
        )
        print()
        print(prep_IR(ir_good))

        print("\n------------------------------------------------\n")
        print("### Bisection")
        bisection_setting = copy.deepcopy(case.bad_setting).with_revision(
            cast(str, case.bisection), bldr
        )
        print(f"Bisected to: {case.bisection}")
        author = get_llvm_github_commit_author(cast(str, case.bisection))
        if author:
            print(f"Committed by: @{author}")
        print("\n------------------------------------------------\n")
        bisection_ir = get_llvm_IR(source, bisection_setting)
        print(
            to_cody_str(
                f"{setting_report_str(bisection_setting)} -emit-llvm -S -o /dev/stdout case.c",
                is_gcc,
            )
        )
        print(prep_IR(bisection_ir))

        print("\n------------------------------------------------\n")
        prebisection_setting = copy.deepcopy(bisection_setting).with_revision(
            bad_repo.rev_to_commit(f"{bisection_setting.compiler.revision}~"), bldr
        )
        print(f"Previous commit: {prebisection_setting.compiler.revision}")
        print(
            "\n"
            + to_cody_str(
                f"{setting_report_str(prebisection_setting)} -emit-llvm -S -o /dev/stdout case.c",
                is_gcc,
            )
        )
        prebisection_ir = get_llvm_IR(source, prebisection_setting)
        print()
        print(prep_IR(prebisection_ir))

    with open("case.txt", "w") as f:
        f.write(source)
    print("Saved case.txt...", file=sys.stderr)

    if is_gcc:
        check_gcc_issues(cast(str, case.bisection))
    else:
        check_llvm_issues(cast(str, case.bisection))


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
    bad_alive = find_alive_markers(new_code, case.bad_setting, prefix)
    nice_print(f"Bad {case.bad_setting}", ok_fail(case.marker in bad_alive))

    good_alive = find_alive_markers(new_code, case.good_setting, prefix)
    nice_print(f"Good {case.good_setting}", ok_fail(case.marker not in good_alive))

    case.code = new_code
    case.reduced_code = new_code

    if case.bisection:
        prev_rev = repo_from_setting(case.bad_setting).rev_to_commit(
            f"{case.bisection}~"
        )
        cpy = copy.deepcopy(case)
        cpy.bad_setting = cpy.bad_setting.with_revision(case.bisection, bldr)
        bis_res_og = case.marker in find_alive_markers(
            new_code, cpy.bad_setting, prefix
        )
        cpy.bad_setting = cpy.bad_setting.with_revision(prev_rev, bldr)
        bis_prev_res_og = case.marker in find_alive_markers(
            new_code, cpy.bad_setting, prefix
        )

        nice_print("Bisection test", ok_fail(bis_res_og and not bis_prev_res_og))
        cpy = copy.deepcopy(case)
    else:
        print("No bisection found! Please bisect the case first.")

    nice_print("Check", ok_fail(chkr.is_interesting_case(case, preprocess=False)))
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
    bad_repo = repo_from_setting(case.bad_setting)

    asmbad = case.bad_setting.get_asm_from_code(case.code)
    asmgood = case.good_setting.get_asm_from_code(case.code)
    save_wrapper("asmbad", asmbad)
    save_wrapper("asmgood", asmgood)

    if case.reduced_code:
        reducedasmbad = case.bad_setting.get_asm_from_code(case.reduced_code)
        reducedasmgood = case.good_setting.get_asm_from_code(case.reduced_code)
        save_wrapper("reducedasmbad", reducedasmbad)
        save_wrapper("reducedasmgood", reducedasmgood)
    if case.bisection:
        bisection_setting = copy.deepcopy(case.bad_setting).with_revision(
            case.bisection, bldr
        )

        asmbisect = bisection_setting.get_asm_from_code(case.code)
        save_wrapper("asmbisect", asmbisect)
        if case.reduced_code:
            reducedasmbisect = bisection_setting.get_asm_from_code(case.reduced_code)
            save_wrapper("reducedasmbisect", reducedasmbisect)
    print(case.marker)


def _get() -> None:
    # Why are you printing code with end=""?
    case_id: int = int(args.case_id)
    if args.what in ["ocode", "rcode", "bisection", "marker"]:
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
        elif args.what == "marker":
            print(case.marker, end="")
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

    repo = repo_from_setting(case.bad_setting)

    if args.what == "ocode":
        with open(args.var, "r") as f:
            new_code = f.read()
        case.code = new_code
        if chkr.is_interesting_case(case):
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
        if chkr.is_interesting_case(case):
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

        case.bad_setting = case.bad_setting.with_revision(rev, bldr)
        if not chkr.is_interesting_case(case):
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
        if chkr.is_interesting_case(case):
            print("Checking bisection...")
            try:
                worked = bisect_case(case, bsctr, bldr, force=True)
            except bisector.BisectionException as e:
                print(f"BisectionException: '{e}'", file=sys.stderr)
                worked = False
            except AssertionError as e:
                print(f"AssertionError: '{e}'", file=sys.stderr)
                worked = False
            except BuildException as e:
                print(f"BuildException: '{e}'", file=sys.stderr)
                worked = False

            if not worked:
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
    project, repo = ccbuilder.get_compiler_info(args.project, Path(config.repodir))
    additional_patches: list[Path] = []
    if args.add_patches:
        additional_patches = [Path(patch).absolute() for patch in args.add_patches]
    for rev in args.rev:
        print(
            bldr.build(
                project=project,
                rev=rev,
                additional_patches=additional_patches
                # TODO: implement force
                # force=args.force,
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
        if reduce_case(case, rdcr, chkr, force=args.force):
            ddb.update_case(case_id, case)
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

        try:
            worked = bisect_case(case, bsctr, bldr, force=args.force)
        except bisector.BisectionException as e:
            print(f"BisectionException: '{e}'", file=sys.stderr)
            worked = False
        except AssertionError as e:
            print(f"AssertionError: '{e}'", file=sys.stderr)
            worked = False
        except BuildException as e:
            print(f"BuildException: '{e}'", file=sys.stderr)
            worked = False

        if worked:
            ddb.update_case(case_id, case)
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
            gcc_repo = Repo(config.gcc.repo, config.gcc.main_branch)
            llvm_repo = Repo(config.llvm.repo, config.llvm.main_branch)

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

    if not res:
        return

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
        select cases.case_id, bisection, bug_report_link, compiler from cases 
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

    if not (res := ddb.con.execute(query).fetchall()):
        return

    if args.id_only:
        for case_id, _, _ in res:
            print(case_id)
    elif args.good_settings:

        gcc_repo = Repo(config.gcc.repo, config.gcc.main_branch)
        llvm_repo = Repo(config.llvm.repo, config.llvm.main_branch)
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
        case = RegressionCase.from_file(config, Path(args.var))
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

    system_llvm = compiler.CompilerExe(
        ccbuilder.CompilerProject.LLVM, Path("clang"), "system"
    )
    system_gcc = compiler.CompilerExe(
        ccbuilder.CompilerProject.GCC, Path("gcc"), "system"
    )
    gcc_repo = get_gcc_repo(config.gcc.repo)
    llvm_repo = get_llvm_repo(config.llvm.repo)
    DeadConfig.init(
        system_llvm,
        llvm_repo,
        system_gcc,
        gcc_repo,
        compiler.ClangTool.init_with_paths_from_llvm(config.ccc, system_llvm),
        config.ccomp,
        config.csmith.include_path,
    )

    patchdb = PatchDB(Path(config.patchdb))
    bldr = Builder(
        cache_prefix=Path(config.cachedir),
        gcc_repo=gcc_repo,
        llvm_repo=llvm_repo,
        patchdb=patchdb,
        jobs=args.cores,
        logdir=Path(config.logdir),
    )
    chkr = Checker(
        DeadConfig.get_config().llvm,
        DeadConfig.get_config().gcc,
        DeadConfig.get_config().ccc,
        DeadConfig.get_config().ccomp,
    )

    rdcr = reducer.Reducer()
    bsctr = bisector.Bisector(config.cachedir)

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
        diagnose_case()
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
