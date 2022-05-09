#!/usr/bin/env python3

import copy
import functools
import logging
import math
import os
import tarfile
from pathlib import Path
from typing import Optional

from ccbuildercached import Repo, BuilderWithCache, BuildException, CompilerConfig, get_compiler_config, PatchDB

import checker
import generator
import parsers
import reducer
import utils


class BisectionException(Exception):
    pass


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


class Bisector:
    """Class to bisect a given case."""

    def __init__(
        self,
        config: utils.NestedNamespace,
        bldr: BuilderWithCache,
        chkr: checker.Checker,
    ) -> None:
        self.config = config
        self.bldr = bldr
        self.chkr = chkr
        self.steps = 0

    def _is_interesting(self, case: utils.Case, rev: str) -> bool:
        """_is_interesting.

        Args:
            case (utils.Case): Case to check
            rev (str): What revision to check the case against.

        Returns:
            bool: True if the case is interesting wrt `rev`.

        Raises:
            builder.CompileError:
        """
        case_cpy = copy.deepcopy(case)
        case_cpy.bad_setting.rev = rev
        if case_cpy.reduced_code:
            case_cpy.code = case_cpy.reduced_code
            return self.chkr.is_interesting(case_cpy, preprocess=False)
        else:
            return self.chkr.is_interesting(case_cpy, preprocess=True)

    def bisect_file(self, file: Path, force: bool = False) -> bool:
        """Bisect case found in `file`.

        Args:
            file (Path): Path to case file to bisect.
            force (bool): Whether or not to force a bisection
                if there's already one.

        Returns:
            bool: True if the bisection of the case in `file` succeeded.
        """
        case = utils.Case.from_file(self.config, file)
        if self.bisect_case(case, force):
            case.to_file(file)
            return True
        return False

    def bisect_case(self, case: utils.Case, force: bool = False) -> bool:
        """Bisect a given case.

        Args:
            case (utils.Case): Case to bisect.
            force (bool): Whether or not to force a bisection
                if there's already one.

        Returns:
            bool: True if the bisection succeeded.
        """
        if not force and case.bisection:
            logging.info(f"Ignoring case: Already bisected")
            return True
        try:
            if res := self.bisect_code(
                case.code, case.marker, case.bad_setting, case.good_settings
            ):
                case.bisection = res
                return True
        except BisectionException:
            return False
        return False

    def bisect_code(
        self,
        code: str,
        marker: str,
        bad_setting: utils.CompilerSetting,
        good_settings: list[utils.CompilerSetting],
    ) -> Optional[str]:
        """Bisect a given code wrt. marker, the bad setting and the good settings.

        Args:
            self:
            code (str): code
            marker (str): marker
            bad_setting (utils.CompilerSetting): bad_setting
            good_settings (list[utils.CompilerSetting]): good_settings

        Returns:
            Optional[str]: Revision the code bisects to, if it is successful.
                None otherwise.

        Raises:
            BisectionException: Raised if the bisection failed somehow.
        """
        case = utils.Case(
            code,
            marker,
            bad_setting,
            good_settings,
            utils.Scenario([bad_setting], good_settings),
            None,
            None,
            None,
        )

        bad_compiler_config = case.bad_setting.compiler_config
        repo = bad_compiler_config.repo

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
            return None
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
        possible_good_commits_t = [
            (rev, repo.get_best_common_ancestor(bad_commit, rev))
            for rev in possible_good_commits
        ]

        good_commit: str
        common_ancestor: str

        def cmp_func(x: tuple[str, str], y: tuple[str, str]) -> bool:
            return repo.is_ancestor(x[1], y[1])

        good_commit, common_ancestor = min(
            possible_good_commits_t,
            key=functools.cmp_to_key(cmp_func),
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

        try:
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
                    logging.critical(f"Currently ignoring b2, sorry")
                    raise BisectionException("Currently ignoring Case type B2, sorry")

                    # res = self._bisection(
                    #    common_ancestor, good_commit, case, repo, interesting_is_bad=False
                    # )
                    # self._check(case, res, repo, interesting_is_bad=False)
                    # print(f"First good commit {res}")
        except utils.CompileError:
            return None

        return res

    def _check(
        self,
        case: utils.Case,
        rev: str,
        repo: Repo,
        interesting_is_bad: bool = True,
    ) -> None:
        """Sanity check, that the bisected commit is actually
        correct.

        Args:
            case (utils.Case): Case to check.
            rev (str): Revision believed to the bisection commit.
            repo (repository.Repo): Repository to get the previous commit from.
            interesting_is_bad (bool): Whether or not to switch the expected result
                of the interestingness-test.
        Raises:
            AssertionError: Raised when the check fails.
        """
        # TODO(Yann): Don't use assertion errors.

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
        repo: Repo,
        interesting_is_bad: bool = True,
        max_build_fail: int = 2,
    ) -> str:
        """Actual bisection part.
        First bisects within the cache, then continues with a normal bisection.

        Args:
            good_rev (str): Revision that is ancestor of bad_rev.
            bad_rev (str): Rev that comes later in the tree.
            case (utils.Case): Case to bisect.
            repo (repository.Repo): Repo to get the revisions from.
            interesting_is_bad (bool): Whether or not to switch how to interpret
                the outcome of the interestingness-test.
            max_build_fail (int): How many times the builder can fail to build w/o
                aborting the bisection.
        """

        self.steps = 0
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
        failed_to_compile = False
        while True:
            if failed_to_compile:
                failed_to_compile = False
                cached_revs.remove(midpoint)

            logging.info(f"{len(cached_revs): 4}, bad: {bad_rev}, good: {good_rev}")
            if len(cached_revs) == 0:
                break
            midpoint_idx = len(cached_revs) // 2
            old_midpoint = midpoint
            midpoint = cached_revs[midpoint_idx]
            if old_midpoint == midpoint:
                break

            # There should be no build failure here, as we are working on cached builds
            # But there could be a CompileError
            self.steps += 1
            try:
                test: bool = self._is_interesting(case, midpoint)
            except utils.CompileError:
                logging.warning(
                    f"Failed to compile code with {case.bad_setting.compiler_config.name}-{midpoint}"
                )
                failed_to_compile = True
                continue

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
        failed_to_build_or_compile = False
        failed_to_build_counter = 0

        guaranteed_termination_counter = 0
        while True:
            if not failed_to_build_or_compile:
                old_midpoint = midpoint
                midpoint = repo.next_bisection_commit(good_rev, bad_rev)
                failed_to_build_counter = 0
                if midpoint == "" or midpoint == old_midpoint:
                    break
            else:
                if failed_to_build_counter >= max_build_fail:
                    raise BisectionException(
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
                failed_to_build_or_compile = False

                if guaranteed_termination_counter >= 20:
                    raise BisectionException(
                        "Failed too many times in a row while bisecting. Aborting bisection..."
                    )
                guaranteed_termination_counter += 1

            logging.info(f"Midpoint: {midpoint}")

            try:
                test = self._is_interesting(case, midpoint)
            except BuildException:
                logging.warning(
                    f"Could not build {case.bad_setting.compiler_config.name} {midpoint}!"
                )
                failed_to_build_or_compile = True
                continue
            except utils.CompileError:
                logging.warning(
                    f"Failed to compile code with {case.bad_setting.compiler_config.name}-{midpoint}"
                )
                failed_to_build_or_compile = True
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
    config, args = utils.get_config_and_parser(parsers.bisector_parser())

    patchdb = PatchDB(config.patchdb)
    bldr = BuilderWithCache(Path(config.cachedir), patchdb, args.cores)
    chkr = checker.Checker(config, bldr)
    gnrtr = generator.CSmithCaseGenerator(config, patchdb, args.cores)
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
                bsctr.bisect_file(tf, force=args.force)
            except BisectionException as e:
                print(f"BisectionException in {tf}: '{e}'")
                continue
            except AssertionError as e:
                print(f"AssertionError in {tf}: '{e}'")
                continue
            except BuildException as e:
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

        gen = gnrtr.parallel_interesting_case_file(
            config, scenario, bldr.cores, output_dir, start_stop=True
        )

        if args.amount == 0:
            while True:
                path = next(gen)
                worked = False
                if args.reducer:
                    try:
                        worked = rdcr.reduce_file(path)
                    except BuildException as e:
                        print(f"BuildException in {path}: {e}")
                        continue

                if not args.reducer or worked:
                    try:
                        bsctr.bisect_file(path, force=args.force)
                    except BisectionException as e:
                        print(f"BisectionException in {path}: '{e}'")
                        continue
                    except AssertionError as e:
                        print(f"AssertionError in {path}: '{e}'")
                        continue
                    except BuildException as e:
                        print(f"BuildException in {path}: '{e}'")
                        continue
        else:
            for i in range(args.amount):
                path = next(gen)
                worked = False
                if args.reducer:
                    try:
                        worked = rdcr.reduce_file(path)
                    except BuildException as e:
                        print(f"BuildException in {path}: {e}")
                        continue
                if not args.reducer or worked:
                    try:
                        bsctr.bisect_file(path, force=args.force)
                    except BisectionException as e:
                        print(f"BisectionException in {path}: '{e}'")
                        continue
                    except AssertionError as e:
                        print(f"AssertionError in {path}: '{e}'")
                        continue
                    except BuildException as e:
                        print(f"BuildException in {path}: '{e}'")
                        continue

    elif args.file:
        file = Path(args.file)
        bsctr.bisect_file(file, force=args.force)

    gnrtr.terminate_processes()
