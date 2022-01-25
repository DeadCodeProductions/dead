#!/usr/bin/env python3

from __future__ import annotations

import json
import logging
import math
import os
from os.path import join as pjoin
from pathlib import Path
from typing import TYPE_CHECKING, Optional, Union

import builder
import parsers
import utils
from enum import Enum
from patchdatabase import PatchDB
from repository import Repo

if TYPE_CHECKING:
    from utils import NestedNamespace


class PatchingResult(Enum):
    BuildsWithoutPatch: int = 1
    BuildsWithPatch: int = 2
    BuildFailed: int = 3


class Patcher:
    def __init__(
        self, config: NestedNamespace, patchdb: PatchDB, cores: Optional[int] = None
    ):
        self.config = config
        self.patchdb = patchdb
        self.builder = builder.Builder(config, self.patchdb, cores=cores)

    def _check_building_patch(
        self, compiler_config: NestedNamespace, rev: str, patch: Path, repo: Repo
    ) -> PatchingResult:
        if not self.patchdb.requires_this_patch(rev, patch, repo):
            try:
                logging.info(f"Building {rev} without patch {patch}...")
                self.builder.build(compiler_config, rev)
                return PatchingResult.BuildsWithoutPatch

            except builder.BuildException as e:
                logging.info(f"Failed to build {rev} without patch {patch}: {e}")

            try:
                logging.info(f"Building {rev} WITH patch {patch}...")
                self.builder.build(compiler_config, rev, additional_patches=[patch])
                return PatchingResult.BuildsWithPatch

            except builder.BuildException as e:
                logging.critical(
                    f"Failed to build {rev} with patch {patch}. Manual intervention needed. Exception: {e}"
                )
                self.patchdb.manual_intervention_required(compiler_config, rev)
                return PatchingResult.BuildFailed
        else:
            logging.info(f"Read form PatchDB: {rev} requires patch {patch}")
            return PatchingResult.BuildsWithPatch

    def _bisection(
        self,
        good_rev: str,
        bad_rev: str,
        compiler_config: NestedNamespace,
        patch: Path,
        repo: Repo,
        failure_is_good: bool = False,
        max_double_fail: int = 2,
    ) -> tuple[str, str]:

        good = good_rev
        bad = bad_rev

        double_fail_counter = 0
        encountered_double_fail = False

        # Bisection
        midpoint = ""
        while True:
            if encountered_double_fail:

                if double_fail_counter >= max_double_fail:
                    raise Exception(
                        "Failed too many times in a row while bisecting. Aborting bisection..."
                    )

                # TODO: More robust testing.
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

                double_fail_counter += 1
                encountered_double_fail = False

            else:
                old_midpoint = midpoint
                midpoint = repo.next_bisection_commit(good=good, bad=bad)
                logging.info(f"Midpoint: {midpoint}")
                if midpoint == "" or midpoint == old_midpoint:
                    break

            patching_result = self._check_building_patch(
                compiler_config, midpoint, patch, repo
            )

            if patching_result.BuildsWithoutPatch:
                if failure_is_good:
                    bad = midpoint
                else:
                    good = midpoint
                continue

            if patching_result.BuildsWithPatch:
                if failure_is_good:
                    good = midpoint
                else:
                    bad = midpoint
                continue

            encountered_double_fail = True

        return good, bad

    def _find_oldest_ancestor_not_needing_patch_and_oldest_patchable_from_releases(
        self,
        repo: Repo,
        compiler_config: utils.NestedNamespace,
        patchable_commit: str,
        potentially_human_readable_name: str,
        patch: Path,
    ) -> tuple[Optional[str], Optional[str]]:
        """
        Find two oldest common ancestors of patchable_commit and one of the releases:
            (1) that doesn't need the patch
            (2) that is buildable only with the patch
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
                    logging.warning(f"Found only older releases requiring the patch!")
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
            patching_result = self._check_building_patch(
                compiler_config, common_ancestor, patch, repo
            )

            if patching_result is PatchingResult.BuildsWithoutPatch:
                no_patch_common_ancestor = common_ancestor
                break

            if patching_result is PatchingResult.BuildsWithPatch:
                if not oldest_patchable_ancestor:  # None have been found
                    oldest_patchable_ancestor = common_ancestor
            else:
                tested_ancestors.append(common_ancestor)

        return no_patch_common_ancestor, oldest_patchable_ancestor

    def find_ranges(
        self, compiler_config: utils.NestedNamespace, patchable_commit: str, patch: Path
    ) -> None:
        introducer = ""
        found_introducer = False
        repo = Repo(compiler_config.repo, compiler_config.main_branch)

        potentially_human_readable_name = patchable_commit
        patchable_commit = repo.rev_to_commit(patchable_commit)
        patch = patch.absolute()
        if not Path(patch).exists():
            logging.critical(f"Patch {patch} doesn't exist. Aborting...")
            raise Exception(f"Patch {patch} doesn't exist. Aborting...")

        (
            no_patch_common_ancestor,
            oldest_patchable_ancestor,
        ) = self._find_oldest_ancestor_not_needing_patch_and_oldest_patchable_from_releases(
            repo,
            compiler_config,
            patchable_commit,
            potentially_human_readable_name,
            patch,
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
        #    (which currently is 7d75ea04cf6d9c8960d5c6119d6203568b7069e9 for gcc)
        #   - Find fixer commits from there (could do something if no_patch_common_ancestor exists)

        if no_patch_common_ancestor:
            # Find introducer commit
            _, introducer = self._bisection(
                no_patch_common_ancestor, patchable_commit, compiler_config, patch, repo
            )

            # Insert from introducer to and with patchable_commit as requiring patching
            # This is of course not the complete range but will help when bisecting
            rev_range = f"{introducer}~..{patchable_commit}"
            self.patchdb.save(patch, repo.rev_to_commit_list(rev_range), repo)

            self.find_fixer_from_introducer_to_releases(
                introducer=introducer,
                compiler_config=compiler_config,
                patch=patch,
                repo=repo,
            )

        elif oldest_patchable_ancestor:
            self.find_fixer_from_introducer_to_releases(
                introducer=oldest_patchable_ancestor,
                compiler_config=compiler_config,
                patch=patch,
                repo=repo,
            )

    def find_fixer_from_introducer_to_releases(
        self, introducer: str, compiler_config: NestedNamespace, patch: Path, repo: Repo
    ) -> None:
        logging.info(f"Starting bisection of fixer commits from {introducer}...")

        # Find reachable releases
        reachable_releases = [
            repo.rev_to_commit(release)
            for release in compiler_config.releases
            if repo.is_ancestor(introducer, release)
        ]

        fixer_list: list[str] = []
        for release in reachable_releases:
            logging.info(f"Searching fixer for release {release}")

            patching_result = self._check_building_patch(
                compiler_config, release, patch, repo
            )

            # Check if any of already found fixers is ancestor of release
            # As we assume that a fixer at a given point fixes all its children, this is fine.
            logging.info(f"Checking for known fixers...")
            if (
                len(fixer_list) > 0
                and patching_result.BuildsWithoutPatch
                and any([repo.is_ancestor(fixer, release) for fixer in fixer_list])
            ):
                logging.info(f"Already known fixer. No additional searching required")
                continue

            if patching_result is PatchingResult.BuildFailed:
                continue

            elif patching_result is PatchingResult.BuildsWithPatch:
                # release only builds with patch, everything to release is to be included
                commits = repo.rev_to_commit_list(f"{introducer}~1..{release}")
                self.patchdb.save(patch, commits, repo)
                continue

            elif patching_result is PatchingResult.BuildsWithoutPatch:
                # Range A..B is includes B, thus we want B to be the last good one
                # as good requires the patch
                fixer, _ = self._bisection(
                    introducer,
                    release,
                    compiler_config,
                    patch,
                    repo,
                    failure_is_good=True,
                )

                fixer_list.append(fixer)

                self.patchdb.save(
                    patch, repo.rev_to_range_needing_patch(introducer, fixer), repo
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
        if args.patch is None:
            print("Missing argument for `patch` when using --find-range.")
            exit(1)
        else:
            patch = args.patch

        compiler_config = utils.get_compiler_config(config, args.compiler)

        if args.patchable_revision is None:
            print("Missing argument for `patchable-revision` when using --find-range.")
            exit(1)
        else:
            patchable_commit = args.patchable_revision

        p.find_ranges(compiler_config, patchable_commit=patchable_commit, patch=patch)

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
