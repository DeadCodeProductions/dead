#!/usr/bin/env python3

"""

This code tries to figure out where a patch needs to be applied for a build to succeed. 
To achieve this, it heavily uses git and bisections and with that the terms 'good' and 'bad'.
However, 'good' does mean something different in different circumstances does not always indicate
a successful build.

The convention used for good and bad is taken from the normal use-case of `git bisect`:
    Something broke along the way and is now bad. Additionally, we know a commit, which worked,
    which is good.
So the bad commit is the newest w.r.t. the git history i.e. good is ancestor of bad.
And this is how 'good' and 'bad' are (should be) used in this file.

Other concepts are:
    introducer: The first commit, that makes a test fail.
    fixer: The first commit, that does not make a test fail, i.e. fixed it.
"""

from __future__ import annotations

import logging
import math
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Optional

import builder
import parsers
import utils
from patchdatabase import PatchDB
from repository import Repo

if TYPE_CHECKING:
    from utils import NestedNamespace


class PatchingResult(Enum):
    BuildsWithoutPatching: int = 1
    BuildsWithPatching: int = 2
    BuildFailed: int = 3


class Patcher:
    def __init__(
        self, config: NestedNamespace, patchdb: PatchDB, cores: Optional[int] = None
    ):
        self.config = config
        self.patchdb = patchdb
        self.builder = builder.Builder(config, self.patchdb, cores=cores)

    def _check_building_patches(
        self,
        compiler_config: NestedNamespace,
        rev: str,
        patches: list[Path],
        repo: Repo,
    ) -> PatchingResult:
        if not self.patchdb.requires_all_these_patches(rev, patches, repo):
            try:
                logging.info(f"Building {rev} without patches {patches}...")
                self.builder.build(compiler_config, rev)
                return PatchingResult.BuildsWithoutPatching

            except builder.BuildException as e:
                logging.info(f"Failed to build {rev} without patches {patches}: {e}")

            try:
                logging.info(f"Building {rev} WITH patches {patches}...")
                self.builder.build(compiler_config, rev, additional_patches=patches)
                return PatchingResult.BuildsWithPatching

            except builder.BuildException as e:
                logging.critical(
                    f"Failed to build {rev} with patches {patches}. Manual intervention needed. Exception: {e}"
                )
                self.patchdb.manual_intervention_required(compiler_config, rev)
                return PatchingResult.BuildFailed
        else:
            logging.info(f"Read form PatchDB: {rev} requires patches {patches}")
            return PatchingResult.BuildsWithPatching

    def _adjust_bisection_midpoint_after_failure(
        self,
        repo: Repo,
        double_fail_counter: int,
        max_double_fail: int,
        bad: str,
        midpoint: str,
        good: str,
    ) -> str:
        """
        Move the midpoint either forwards or backwards (depending on the double_fail_counter)

        Returns:
            new midpoint (str)
        """
        if double_fail_counter >= max_double_fail:
            raise Exception(
                "Failed too many times in a row while bisecting. Aborting bisection..."
            )
        # TODO: More robust testing.
        # XXX: what's the purpose of this check? To switch between moving the
        # midpoint forwards and backwards?
        if double_fail_counter % 2 == 0:
            # Get size of range
            range_size = len(repo.direct_first_parent_path(midpoint, bad))

            # Move 10% towards the last bad
            step = max(int(0.9 * range_size), 1)
            midpoint = repo.rev_to_commit(f"{bad}~{step}")
        else:
            # Symmetric to case above
            range_size = len(repo.direct_first_parent_path(good, midpoint))
            step = max(int(0.2 * range_size), 1)
            midpoint = repo.rev_to_commit(f"{midpoint}~{step}")
        return midpoint

    def _bisection(
        self,
        good_rev: str,
        bad_rev: str,
        compiler_config: NestedNamespace,
        patches: list[Path],
        repo: Repo,
        failure_is_good: bool = False,
        max_double_fail: int = 2,
    ) -> tuple[str, str]:

        good = good_rev
        bad = bad_rev

        # When building a particular commit and it fails to build
        # without the patches and with the patches, it is considered
        # a double fail.
        double_fail_counter = 0
        encountered_double_fail = False

        # Bisection
        midpoint = ""
        while True:
            if encountered_double_fail:
                midpoint = self._adjust_bisection_midpoint_after_failure(
                    repo, double_fail_counter, max_double_fail, bad, midpoint, good
                )
                double_fail_counter += 1
                encountered_double_fail = False
            else:
                old_midpoint = midpoint
                midpoint = repo.next_bisection_commit(good=good, bad=bad)
                logging.info(f"Midpoint: {midpoint}")
                if midpoint == "" or midpoint == old_midpoint:
                    break

            patching_result = self._check_building_patches(
                compiler_config, midpoint, patches, repo
            )

            if patching_result is PatchingResult.BuildFailed:
                encountered_double_fail = True
            elif (
                patching_result is PatchingResult.BuildsWithoutPatching
            ) ^ failure_is_good:
                good = midpoint
            else:
                bad = midpoint

        return good, bad

    def _find_oldest_ancestor_not_needing_patches_and_oldest_patchable_from_releases(
        self,
        repo: Repo,
        compiler_config: utils.NestedNamespace,
        patchable_commit: str,
        potentially_human_readable_name: str,
        patches: list[Path],
    ) -> tuple[Optional[str], Optional[str]]:
        """
        Find two oldest common ancestors of patchable_commit and one of the releases:
            (1) that doesn't need the patch(es)
            (2) that is buildable only with the patch(es)
        """

        # For now, just assume this is sorted in descending release-recency
        # Using commit dates doesn't really work
        # TODO: do something with `from packaging import version; version.parse()`
        release_versions = ["trunk"] + compiler_config.releases
        release_versions.reverse()

        tested_ancestors = []
        no_patch_common_ancestor = None
        oldest_patchable_ancestor = None
        for old_version in release_versions:

            logging.info(f"Testing for {old_version}")
            if not repo.is_branch_point_ancestor_wrt_master(
                old_version, patchable_commit
            ):
                if oldest_patchable_ancestor:
                    # XXX: Would something like "All older releases require
                    # patching" make more sense as a warning?
                    logging.warning(
                        f"Found only older releases requiring the patch(es)!"
                    )
                    break
                raise Exception(
                    "No buildable-version was found before patchable_commit!"
                )

            common_ancestor = repo.get_best_common_ancestor(
                old_version, patchable_commit
            )
            # TODO: Check that common_ancestor is ancestor of master.
            #       Otherwise we get stuck in a branch
            #       Is this actually a problem?
            if common_ancestor in tested_ancestors:
                logging.info(
                    f"Common ancestor of {old_version} and {potentially_human_readable_name} was already tested. Proceeding..."
                )
                continue

            # Building of releases
            patching_result = self._check_building_patches(
                compiler_config, common_ancestor, patches, repo
            )

            if patching_result is PatchingResult.BuildsWithoutPatching:
                no_patch_common_ancestor = common_ancestor
                break

            if patching_result is PatchingResult.BuildsWithPatching:
                if not oldest_patchable_ancestor:  # None have been found
                    oldest_patchable_ancestor = common_ancestor
            else:
                tested_ancestors.append(common_ancestor)

        return no_patch_common_ancestor, oldest_patchable_ancestor

    def find_ranges(
        self,
        compiler_config: utils.NestedNamespace,
        patchable_commit: str,
        patches: list[Path],
    ) -> None:
        """Given a compiler, a revision of the compiler that normally does not build
        and the set of patches needed to fix this particular revision,
        find the continuous region on the commit history which requires all these
        patches to build.

        We assume that such region is continuous. That means in case there's a gap
        which does not need the patch, we may end up including the whole gap into the
        region or do not find the region after the gap (w.r.t. the starting commit)
        at all.

        Args:
            compiler_config (utils.NestedNamespace): The compiler project which has the problematic commit (it is either config.llvm or config.gcc).
            patchable_commit (str): The problematic commit which is buildable with `patches`.
            patches (list[Path]): Patches required to build `patchable_commit`.


        Returns:
            None:
        """
        introducer = ""

        found_introducer = False
        repo = Repo(compiler_config.repo, compiler_config.main_branch)

        potentially_human_readable_name = patchable_commit
        patchable_commit = repo.rev_to_commit(patchable_commit)
        patches = [patch.absolute() for patch in patches]
        for patch in patches:
            if not Path(patch).exists():
                logging.critical(f"Patch {patch} doesn't exist. Aborting...")
                raise Exception(f"Patch {patch} doesn't exist. Aborting...")
        (
            no_patch_common_ancestor,
            oldest_patchable_ancestor,
        ) = self._find_oldest_ancestor_not_needing_patches_and_oldest_patchable_from_releases(
            repo,
            compiler_config,
            patchable_commit,
            potentially_human_readable_name,
            patches,
        )

        # Possible cases
        # no_patch_common_ancestor was found AND oldest_patchable_ancestor was found
        #   - This only happens if a bug was re-introduced or the patch just so happens to fix
        #     another intermediate bug.
        #     For simplicity we assume that BOTH were the ONLY ones found so we are fine
        #
        # ONLY no_patch_common_ancestor was found (hopefully the common case)
        #   - Proceed with bisection of introducer commit
        #
        # ONLY oldest_patchable_ancestor was found
        #   - Find fixer commits from there (could do something if no_patch_common_ancestor exists)

        if no_patch_common_ancestor:
            # Find introducer commit
            _, introducer = self._bisection(
                no_patch_common_ancestor,
                patchable_commit,
                compiler_config,
                patches,
                repo,
            )

            # Insert from introducer to and with patchable_commit as requiring patching
            # This is of course not the complete range but will help when bisecting
            rev_range = f"{introducer}~..{patchable_commit}"
            commit_list = repo.rev_to_commit_list(rev_range)
            for patch in patches:
                self.patchdb.save(patch, commit_list, repo)

            self.find_fixer_from_introducer_to_releases(
                introducer=introducer,
                compiler_config=compiler_config,
                patches=patches,
                repo=repo,
            )

        elif oldest_patchable_ancestor:
            self.find_fixer_from_introducer_to_releases(
                introducer=oldest_patchable_ancestor,
                compiler_config=compiler_config,
                patches=patches,
                repo=repo,
            )

    def find_fixer_from_introducer_to_releases(
        self,
        introducer: str,
        compiler_config: NestedNamespace,
        patches: list[Path],
        repo: Repo,
    ) -> None:
        logging.info(f"Starting bisection of fixer commits from {introducer}...")

        # Find reachable releases
        reachable_releases = [
            repo.rev_to_commit(release)
            for release in compiler_config.releases
            if repo.is_ancestor(introducer, release)
        ]

        last_needing_patch_list: list[str] = []
        for release in reachable_releases:
            logging.info(f"Searching fixer for release {release}")

            patching_result = self._check_building_patches(
                compiler_config, release, patches, repo
            )

            # Check if any of already found fixers is ancestor of release
            # As we assume that a fixer at a given point fixes all its children, this is fine.
            logging.info(f"Checking for known fixers...")
            if (
                len(last_needing_patch_list) > 0
                and patching_result.BuildsWithoutPatching
                and any(
                    [
                        repo.is_ancestor(fixer, release)
                        for fixer in last_needing_patch_list
                    ]
                )
            ):
                logging.info(f"Already known fixer. No additional searching required")
                continue

            if patching_result is PatchingResult.BuildFailed:
                continue

            elif patching_result is PatchingResult.BuildsWithPatching:
                # release only builds with patch, everything to release is to be included
                commits = repo.rev_to_commit_list(f"{introducer}~1..{release}")
                for patch in patches:
                    self.patchdb.save(patch, commits, repo)
                continue

            elif patching_result is PatchingResult.BuildsWithoutPatching:
                # Range A..B is includes B, thus we want B to be the last good one
                # as good requires the patch
                last_needing_patch, _ = self._bisection(
                    introducer,
                    release,
                    compiler_config,
                    patches,
                    repo,
                    failure_is_good=True,
                )

                last_needing_patch_list.append(last_needing_patch)
                range_needing_patching = repo.rev_to_range_needing_patch(
                    introducer, last_needing_patch
                )
                for patch in patches:
                    self.patchdb.save(
                        patch,
                        range_needing_patching,
                        repo,
                    )

        logging.info("Done finding fixers")
        return

    def bisect_build(
        self,
        good: str,
        bad: str,
        compiler_config: NestedNamespace,
        repo: Repo,
        failure_is_good: bool = False,
    ) -> tuple[str, str]:
        """Bisect w.r.t. building and not building.

        Args:
            good (str): Commit that is closer to the head of the branch than `bad`.
            bad (str): Commit that is further away from the head of the branch than `good`.
            compiler_config (NestedNamespace): Either config.gcc or config.llvm
            repo (Repo): Repository object for the compiler project.
            failure_is_good (bool): If failing to build is expected to happen to the `good` commit.

        Returns:
            tuple[str, str]: The two commits around the bisection point.
        """

        midpoint = ""

        while True:
            old_midpoint = midpoint
            midpoint = repo.next_bisection_commit(good=good, bad=bad)
            logging.info(f"Midpoint: {midpoint}")
            if midpoint == "" or midpoint == old_midpoint:
                break

            # ==================== BUILDING ====================
            try:
                logging.info(f"Building midpoint {midpoint}...")
                self.builder.build(compiler_config, midpoint)
                if failure_is_good:
                    bad = midpoint
                else:
                    good = midpoint
                continue

            except builder.BuildException as e:
                logging.info(f"Failed to build {midpoint}: {e}")
                if failure_is_good:
                    good = midpoint
                else:
                    bad = midpoint
                continue

        return (good, bad)

    def find_introducer(self, compiler_config: NestedNamespace, broken_rev: str) -> str:
        """Given a broken commit, find the commit that introduced the build failure.

        Args:
            compiler_config (NestedNamespace): Either config.gcc or config.llvm
            broken_rev (str): The revision which does not build.

        Returns:
            str: introducer commit hash
        """
        logging.info(f"Looking for introducer commit starting at {broken_rev}")

        repo = Repo(compiler_config.repo, compiler_config.main_branch)

        oldest_possible_commit = repo.get_best_common_ancestor(
            compiler_config.releases[-1], "main"
        )

        # === Introducer
        # ====== Search Phase

        exp = 0

        hit_upper_bound = False
        current_commit = broken_rev
        while True:
            prev_commit = current_commit
            current_commit = repo.rev_to_commit(broken_rev + f"~{2**exp + 10}")
            is_ancestor = repo.is_ancestor(oldest_possible_commit, current_commit)
            if hit_upper_bound:
                msg = (
                    f"Couldn't find buildable ancestor for broken revision {broken_rev}"
                )
                logging.critical(msg)
                raise Exception(msg)

            if not is_ancestor and not hit_upper_bound:
                current_commit = oldest_possible_commit
                hit_upper_bound = True

            try:
                logging.info(f"Building {current_commit} in search of buildable one")
                self.builder.build(compiler_config, current_commit)
                break
            except builder.BuildException as e:
                exp += 1
                logging.info(
                    f"Failed to build {current_commit}. Increasing exponent to {exp}: {e}"
                )

        # ====== Bisection
        msg = f"Staring bisection between {current_commit} and {prev_commit}, should take at most around {math.log(max(2**exp, 11) - 2**min(exp-1, 0), 2)} steps"
        logging.info(msg)
        print(msg)
        _, introducer = self.bisect_build(
            good=current_commit,
            bad=prev_commit,
            compiler_config=compiler_config,
            repo=repo,
            failure_is_good=False,
        )
        msg = f"Found introducer {introducer}"
        logging.info(msg)
        print(msg)
        return introducer


if __name__ == "__main__":
    config, args = utils.get_config_and_parser(parsers.patcher_parser())

    cores = args.cores

    patchdb = PatchDB(config.patchdb)
    p = Patcher(config, patchdb, cores=cores)

    if args.find_range:
        if not args.patches:
            print("Missing argument for `patches` when using --find-range.")
            exit(1)
        else:
            patches = [Path(patch) for patch in args.patches]

        compiler_config = utils.get_compiler_config(config, args.compiler)

        if args.patchable_revision is None:
            print("Missing argument for `patchable-revision` when using --find-range.")
            exit(1)
        else:
            patchable_commit = args.patchable_revision

        p.find_ranges(
            compiler_config, patchable_commit=patchable_commit, patches=patches
        )

    # ====================
    elif args.find_introducer:

        if args.broken_revision is None:
            print(
                "Missing argument for `broken-revision` when using --find-introducer."
            )
            exit(1)
        else:
            broken_rev = args.broken_revision

        compiler_config = utils.get_compiler_config(config, args.compiler)

        p.find_introducer(compiler_config, broken_rev)
