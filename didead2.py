#!/usr/bin/env python3

import pickle
import logging
import copy
import tempfile
from dataclasses import dataclass
from typing import Optional
from concurrent.futures import ProcessPoolExecutor, as_completed, Future, wait
from pathlib import Path

import ccbuilder
from dead_instrumenter.instrumenter import instrument_program
from diopter.preprocessor import preprocess_csmith_code
from diopter.compiler import CompilationSetting, CompilerExe, OptLevel, ClangTool
from diopter.generator import CSmithGenerator
from diopter.reducer import Reducer, ReductionCallback
from diopter.bisector import Bisector, BisectionCallback

from dead.checker import Checker, find_alive_markers

from tqdm import tqdm  # type: ignore


class DeadGenerator(CSmithGenerator):
    def generate_code(self) -> str:
        csmith_code = super().generate_code()
        with tempfile.NamedTemporaryFile(suffix=".c") as tfile:
            with open(tfile.name, "w") as f:
                f.write(csmith_code)
            instrument_program(Path(tfile.name), flags=["-I/usr/include/csmith-2.3.0/"])
            with open(tfile.name, "r") as f:
                return f.read()


def create_compilation_settings(
    bldr: ccbuilder.Builder,
    project: ccbuilder.CompilerProject,
    repo: ccbuilder.Repo,
    revs: list[ccbuilder.Revision],
    opt_levels: list[OptLevel],
    flags: list[str] = [],
    include_paths: list[str] = [],
    system_include_paths: list[str] = [],
    # DiopterContext should have a dict[CompilerProject,Repo]
) -> list[CompilationSetting]:

    res: list[CompilationSetting] = []
    for rev in revs:
        commit = repo.rev_to_commit(rev)
        for opt in opt_levels:
            res.append(
                CompilationSetting(
                    compiler=CompilerExe(
                        project, bldr.build(project, rev, True), commit
                    ),
                    opt_level=opt,
                    include_paths=copy.deepcopy(include_paths),
                    system_include_paths=copy.deepcopy(system_include_paths),
                    flags=copy.deepcopy(flags),
                )
            )
    return res


def check_interestingness(
    checker: Checker,
    candidate: str,
    target: CompilationSetting,
    attackers: list[CompilationSetting],
) -> Optional[tuple[str, list[tuple[str, list[CompilationSetting]]]]]:
    markers = checker.interesting_markers(candidate, target, attackers)
    if not markers:
        return None
    return candidate, markers


class DeadReductionCallback(ReductionCallback):
    def __init__(
        self,
        marker: str,
        bad_setting: CompilationSetting,
        good_setting: CompilationSetting,
        checker: Checker,
    ):
        self.marker = marker
        self.bad_setting = bad_setting
        self.good_setting = good_setting
        self.checker = checker

    def test(self, code: str) -> bool:
        return self.checker.is_interesting_marker(
            code, self.marker, self.bad_setting, [self.good_setting], preprocess=False
        )


def get_setting_with_commit(
    commit: ccbuilder.Commit, setting: CompilationSetting, bldr: ccbuilder.Builder
) -> CompilationSetting:
    return CompilationSetting(
        CompilerExe(
            setting.compiler.project,
            bldr.build(setting.compiler.project, commit, True),
            commit,
        ),
        setting.opt_level,
        setting.flags,
        setting.include_paths,
        setting.system_include_paths,
    )


class DeadBisectionCallback(BisectionCallback):
    def __init__(
        self,
        code: str,
        setting: CompilationSetting,
        marker: str,
        bldr: ccbuilder.Builder,
    ):
        self.code = code
        self.setting = setting
        self.marker = marker
        self.bldr = bldr

    def check(self, commit: ccbuilder.Commit) -> Optional[bool]:
        # try:
        return self.marker in find_alive_markers(
            self.code,
            get_setting_with_commit(commit, self.setting, self.bldr),
            "DCEMarker",
        )
        # except Exception as e:
        logging.warning(f"Test failed with: '{e}'. Continuing...")
        return None


if __name__ == "__main__":
    num_lvl = getattr(logging, "DEBUG")
    logging.basicConfig(level=num_lvl)

    # All the default paths and standard objects, e.g., the repos,
    # should be part of DiopterContext

    llvm_repo = ccbuilder.get_llvm_repo()
    gcc_repo = ccbuilder.get_gcc_repo()
    bldr = ccbuilder.Builder(
        Path("/zdata/compiler_cache"),
        gcc_repo,
        llvm_repo,
        logdir=Path("didead2log").absolute(),
    )

    attackers = create_compilation_settings(
        bldr,
        project=ccbuilder.CompilerProject.GCC,
        revs=ccbuilder.MajorCompilerReleases[ccbuilder.CompilerProject.GCC][:4],
        opt_levels=[OptLevel.O3, OptLevel.O2],
        system_include_paths=["/usr/include/csmith-2.3.0/"],
        repo=gcc_repo,
    )

    target = create_compilation_settings(
        bldr,
        project=ccbuilder.CompilerProject.GCC,
        revs=["trunk"],
        opt_levels=[OptLevel.O3],
        system_include_paths=["/usr/include/csmith-2.3.0/"],
        repo=gcc_repo,
    )[0]

    generator = DeadGenerator()

    llvm = CompilerExe(ccbuilder.CompilerProject.LLVM, Path("clang"), "system")
    gcc = CompilerExe(ccbuilder.CompilerProject.GCC, Path("gcc"), "system")
    ccc = ClangTool.init_with_paths_from_llvm(
        Path("/home/theo/dead/callchain_checker/build/bin/ccc"), llvm
    )
    checker = Checker(
        llvm,
        gcc,
        ccc,
        "ccomp",
    )

    if False:
        interesting_candidate_futures = []
        interesting_candidates = []
        with ProcessPoolExecutor() as p:
            n = 1024
            for candidate in tqdm(
                generator.generate_code_parallel(n, p),
                desc="Generating candidates",
                total=n,
                dynamic_ncols=True,
            ):
                interesting_candidate_futures.append(
                    p.submit(
                        check_interestingness,
                        checker,
                        candidate,
                        target,
                        attackers,
                    )
                )

            print("Filtering interesting candidates")
            for fut in tqdm(
                as_completed(interesting_candidate_futures),
                desc="Filtering candidates",
                total=n,
                dynamic_ncols=True,
            ):
                r = fut.result()
                if not r:
                    continue
                interesting_candidates.append(r)

            print(f"Found {len(interesting_candidates)} interesting candidates")

    else:
        with open("case.pickle", "rb") as f:
            interesting_candidates = [pickle.load(f)]

    print("Bisecting")
    bsctr = Bisector(bldr.cache_prefix)

    for code, markersettings in interesting_candidates:
        # with open("case.pickle", "wb") as f:
        # pickle.dump((code, markersettings), f)
        # exit(0)

        callback = DeadBisectionCallback(code, target, markersettings[0][0], bldr)
        assert callback.check(target.compiler.revision)
        print(
            bsctr.bisect(
                callback,
                target.compiler.revision,
                markersettings[0][1][0].compiler.revision,
                ccbuilder.CompilerProject.GCC,
                gcc_repo,
            )
        )

    print("Reducing")
    for code, markersettings in interesting_candidates:
        code = preprocess_csmith_code(
            code, str(gcc.exe), ["-isystem/usr/include/csmith-2.3.0"]
        )
        rcallback = DeadReductionCallback(
            markersettings[0][0], target, markersettings[0][1][0], checker
        )
        Reducer().reduce(code, rcallback)
