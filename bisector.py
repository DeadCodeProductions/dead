#!/usr/bin/env python3

import copy
import dataclasses
import functools
import logging
import math
import os
import tarfile
from dataclasses import dataclass
from pathlib import Path

import builder
import checker
import generator
import parsers
import patchdatabase
import reducer
import repository
import utils


def find_cached_revisions(
    compiler_name: str, config: utils.NestedNamespace
) -> list[str]:
    if compiler_name == "llvm":
        compiler_name = "clang"
    compilers = []
    for entry in Path(config.cachedir).iterdir():
        if entry.is_symlink() or not entry.stem.startswith(compiler_name):
            continue
        if not (entry / "bin" / compiler_name).exists():
            continue
        rev = str(entry).split("-")[-1]
        compilers.append(rev)
    return compilers


@dataclass
class Bisector:
    config: utils.NestedNamespace
    bldr: builder.Builder
    chkr: checker.Checker

    def _is_interesting(self, case: utils.Case, rev: str) -> bool:
        case_cpy = copy.deepcopy(case)
        case_cpy.bad_setting.rev = rev
        # TODO: Shall we do this?
        case_cpy.code = case_cpy.reduced_code[-1]
        return self.chkr.is_interesting(case_cpy, preprocess=False)

    def bisect(self, file: Path, force: bool = False):
        case = utils.Case.from_file(self.config, file)

        if not case.reduced_code:
            logging.info(f"Ignoring case {file}: Not reduced")
            return
        if not force and len(case.reduced_code) <= len(case.bisections):
            logging.info(f"Ignoring case {file}: Already bisected")
            return

        bad_compiler_config = case.bad_setting.compiler_config
        repo = repository.Repo(
            bad_compiler_config.repo, bad_compiler_config.main_branch
        )

        # ===== Get good and bad commits
        bad_commit = case.bad_setting.rev
        # Only the ones which are on the same opt_level and have the same compiler can be bisected
        possible_good_commits = [
            gs.rev
            for gs in case.good_settings
            if gs.opt_level == case.bad_setting.opt_level
            and gs.compiler_config.name == bad_compiler_config.name
        ]

        if len(possible_good_commits) == 0:
            logging.info(f"No matching optimization level found. Aborting...")
            return
        # Sort commits based on branch point wrt to the bad commit
        # Why? Look at the following commit graph
        # Bad
        #  |  Good_1
        #  | /
        #  A   Good_2
        #  |  /
        #  | /
        #  B
        #  |
        # We want to bisect between Bad and Good_1 because it's less bisection work.
        possible_good_commits = [
            (rev, repo.get_best_common_ancestor(bad_commit, rev))
            for rev in possible_good_commits
        ]

        good_commit, common_ancestor = min(
            possible_good_commits,
            key=functools.cmp_to_key(lambda x, y: repo.is_ancestor(x[1], y[1])),
        )

        # ====== Figure out in which part the introducer or fixer lies
        #
        # Bad     Bad
        #  |       |
        #  |       |    Good
        #  |   or  |b1 /
        #  |b0     |  / b2
        #  |       | /
        # Good     CA
        #
        # if good is_ancestor of bad:
        #    case b0
        #    searching regression
        # else:
        #    if CA is not interesting:
        #        case b1
        #        searching regression
        #    else:
        #        case b2
        #        searching fixer

        if repo.is_ancestor(good_commit, bad_commit):
            res = self._bisection(good_commit, bad_commit, case, repo)
            print(f"{res}")
        else:
            if not self._is_interesting(case, common_ancestor):
                # b1 case
                logging.info("B1 Case")
                res = self._bisection(
                    common_ancestor, bad_commit, case, repo, interesting_is_bad=True
                )
                print(f"{res}")
                self._check(case, res, repo)
            else:
                # b2 case
                logging.info("B2 Case")
                # TODO: Figure out how to save and handle b2
                logging.critical(f"Currently ignoring b2, sorry ({file}")
                return

                # res = self._bisection(
                #    common_ancestor, good_commit, case, repo, interesting_is_bad=False
                # )
                # self._check(case, res, repo, interesting_is_bad=False)
                # print(f"First good commit {res}")
        # Sanity check

        case.bisections.append(res)

        case.to_file(file)

    def _check(
        self,
        case: utils.Case,
        rev: str,
        repo: repository.Repo,
        interesting_is_bad: bool = True,
    ):

        prev_commit = repo.rev_to_commit(f"{rev}~")
        if interesting_is_bad:
            assert self._is_interesting(case, rev) and not self._is_interesting(
                case, prev_commit
            )
        else:
            assert not self._is_interesting(case, rev) and self._is_interesting(
                case, prev_commit
            )

    def _bisection(
        self,
        good_rev: str,
        bad_rev: str,
        case: utils.Case,
        repo: repository.Repo,
        interesting_is_bad: bool = True,
        max_build_fail: int = 2,
    ):

        # check cache
        possible_revs = repo.direct_first_parent_path(good_rev, bad_rev)
        cached_revs = find_cached_revisions(
            case.bad_setting.compiler_config.name, self.config
        )
        cached_revs = [r for r in cached_revs if r in possible_revs]

        # Create enumeration dict to sort cached_revs with
        sort_dict = dict((r, v) for v, r in enumerate(possible_revs))
        cached_revs = sorted(cached_revs, key=lambda x: sort_dict[x])

        # bisect in cache
        len_region = len(repo.direct_first_parent_path(good_rev, bad_rev))
        logging.info(f"Bisecting in cache...")
        midpoint = ""
        old_midpoint = ""
        while True:
            logging.info(f"{len(cached_revs): 4}, bad: {bad_rev}, good: {good_rev}")
            if len(cached_revs) == 0:
                break
            midpoint_idx = len(cached_revs) // 2
            old_midpoint = midpoint
            midpoint = cached_revs[midpoint_idx]
            if old_midpoint == midpoint:
                break
            # There should be no build failure here, as we are working on cached builds
            test: bool = self._is_interesting(case, midpoint)

            if test:
                # bad is always "on top" in the history tree
                # git rev-list returns commits in order of the parent relation
                # cached_revs is also sorted in that order
                # Thus when finding something bad i.e interesting, we have to cut the head
                # and when finding something good, we have to cut the tail
                if interesting_is_bad:
                    bad_rev = midpoint
                    cached_revs = cached_revs[midpoint_idx + 1 :]
                else:
                    good_rev = midpoint
                    cached_revs = cached_revs[:midpoint_idx]
            else:
                if interesting_is_bad:
                    good_rev = midpoint
                    cached_revs = cached_revs[:midpoint_idx]
                else:
                    bad_rev = midpoint
                    cached_revs = cached_revs[midpoint_idx + 1 :]

        len_region2 = len(repo.direct_first_parent_path(good_rev, bad_rev))
        logging.info(f"Cache bisection: range size {len_region} -> {len_region2}")

        # bisect
        len_region = len(repo.direct_first_parent_path(good_rev, bad_rev))
        logging.info(f"Bisecting for approx. {math.ceil(math.log2(len_region))} steps")
        midpoint = ""
        old_midpoint = ""
        failed_to_build = False
        failed_to_build_counter = 0
        while True:
            if not failed_to_build:
                old_midpoint = midpoint
                midpoint = repo.next_bisection_commit(good_rev, bad_rev)
                failed_to_build_counter = 0
                if midpoint == "" or midpoint == old_midpoint:
                    break
            else:
                if failed_to_build_counter >= max_build_fail:
                    raise Exception(
                        "Failed too many times in a row while bisecting. Aborting bisection..."
                    )
                if failed_to_build_counter % 2 == 0:
                    # Get size of range
                    range_size = len(repo.direct_first_parent_path(midpoint, bad_rev))

                    # Move 10% towards the last bad
                    step = max(int(0.9 * range_size), 1)
                    midpoint = repo.rev_to_commit(f"{bad_rev}~{step}")
                else:
                    # Symmetric to case above but jumping 10% into the other directory i.e 20% from our position.
                    range_size = len(repo.direct_first_parent_path(good_rev, midpoint))
                    step = max(int(0.2 * range_size), 1)
                    midpoint = repo.rev_to_commit(f"{midpoint}~{step}")

                failed_to_build_counter += 1
                failed_to_build = False

            logging.info(f"Midpoint: {midpoint}")

            try:
                test: bool = self._is_interesting(case, midpoint)
            except builder.BuildException:
                logging.warning(
                    f"Could not build {case.bad_setting.compiler_config.name} {midpoint}!"
                )
                failed_to_build = True
                continue

            if test:
                if interesting_is_bad:
                    # "As if not_interesting_is_good does not exist"-case
                    bad_rev = midpoint
                else:
                    good_rev = midpoint
            else:
                if interesting_is_bad:
                    # "As if not_interesting_is_good does not exist"-case
                    good_rev = midpoint
                else:
                    bad_rev = midpoint

        return bad_rev


if __name__ == "__main__":
    config, args = utils.get_config_and_parser(parsers.reducer_parser())

    patchdb = patchdatabase.PatchDB(config.patchdb)
    bldr = builder.Builder(config, patchdb, args.cores)
    chkr = checker.Checker(config, bldr)
    gnrtr = generator.CSmithCaseGenerator(config, patchdb)
    rdcr = reducer.Reducer(config, bldr)
    bsctr = Bisector(config, bldr, chkr)

    # TODO: This is duplicate code
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
                bsctr.bisect(tf, force=args.force)
            except AssertionError as e:
                print(f"AssertionError in {tf}: '{e}'")
                continue
            except builder.BuildException as e:
                print(f"BuildException in {tf}: '{e}'")
                continue

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
        if len(tmp.target_settings) > 0:
            scenario.target_settings = tmp.target_settings
        if len(tmp.attacker_settings) > 0:
            scenario.attacker_settings = tmp.attacker_settings

        gen = gnrtr.parallel_interesting_case(
            config, scenario, bldr.cores, output_dir, start_stop=True
        )

        if args.amount == 0:
            while True:
                path = next(gen)
                worked, _ = rdcr.reduce(path)
                if worked:
                    bsctr.bisect(path, force=args.force)
        else:
            for i in range(args.amount):
                path = next(gen)
                worked, _ = rdcr.reduce(path)
                if worked:
                    bsctr.bisect(path, force=args.force)

    else:
        file = Path(args.file)
        bsctr.bisect(file, force=args.force)
