#!/usr/bin/env python3

import os
import builder
import utils
import logging
import subprocess
import json
import parsers
import math

from contextlib import contextmanager
from pathlib import Path
from typing import Union, Optional
from os.path import join as pjoin

PathLike = Union[os.PathLike[str], Path]


class Repo:
    def __init__(self, path: PathLike, main_branch: str):
        self.path = os.path.abspath(path)
        self._showed_stale_warning = False
        self.main_branch = main_branch

    @contextmanager
    def repo_context(self):
        original_dir = os.getcwd()
        os.chdir(self.path)

        # TODO: Doesn't look good
        try:
            yield None
        finally:
            os.chdir(original_dir)

    def get_best_common_ancestor(self, rev_a, rev_b):
        with self.repo_context():
            a = self._in_repo_rev_to_commit(rev_a)
            b = self._in_repo_rev_to_commit(rev_b)
            return utils.run_cmd(f"git merge-base {a} {b}")

    def rev_to_commit(self, rev):
        # Could support list of revs...
        if rev == "trunk" or rev == "master" or rev == "main":
            if not self._showed_stale_warning:
                logging.warning(
                    "Reminder: trunk/master/main/hauptzweig/principale is stale"
                )
                self._showed_stale_warning = True
            rev = self.main_branch
        with self.repo_context():
            return utils.run_cmd(f"git rev-parse {rev}")

    def _in_repo_rev_to_commit(self, rev):
        # Could support list of revs...
        if rev == "trunk" or rev == "master" or rev == "main":
            if not self._showed_stale_warning:
                logging.warning(
                    "Reminder: trunk/master/main/hauptzweig/principale is stale"
                )
                self._showed_stale_warning = True
            rev = self.main_branch
        return utils.run_cmd(f"git rev-parse {rev}")

    def rev_to_range_needing_patch(self, introducer: str, fixer: str) -> list[str]:
        # This functions aim is best described with a picture
        #    O---------P
        #   /   G---H   \      I---J       L--M
        #  /   /     \   \    /     \     /
        # A---B---Z---C---N---D-------E---F---K
        #      \     /
        #       Q---R
        # call rev_to_range_needing_patch(G, K) gives
        # (K, F, 'I, J, D, E', C, H, G)
        # in particular it doesn't include Z, P, O, Q and R
        # Range G~..K would include these
        #

        with self.repo_context():
            # Get all commits with at least 2 parents
            merges_after_introducer = utils.run_cmd(
                f"git rev-list --merges {introducer}~..{fixer}"
            )
            if len(merges_after_introducer) > 0:
                # Get all parent commits of these (so for C it would be H, Z and R)
                cmd = f"git rev-parse " + "^@ ".join(merges_after_introducer)
                merger_parents = set(utils.run_cmd(cmd).split("\n"))

                # Remove all parents which which are child of requested commit
                unwanted_merger_parents = [
                    parent
                    for parent in merger_parents
                    if not self.is_ancestor(introducer, parent)
                ]
                # Final command
            else:
                unwanted_merger_parents = []
            cmd = f"git rev-list {fixer} ^{introducer} " + " ^".join(
                unwanted_merger_parents
            )
            res = [
                commit for commit in utils.run_cmd(cmd).split("\n") if commit != ""
            ] + [introducer]
            return res

    def direct_first_parent_path(self, older: str, younger: str) -> list[str]:
        with self.repo_context():
            cmd = f"git rev-list --first-parent {younger} ^{older}"
            res = [
                commit for commit in utils.run_cmd(cmd).split("\n") if commit != ""
            ] + [older]
            return res

    def rev_to_commit_list(self, rev):
        # TODO: maybe merge with rev_to_commit...
        with self.repo_context():
            return utils.run_cmd(f"git log --format=%H {rev}").split("\n")

    def is_ancestor(self, rev_old, rev_young) -> bool:
        with self.repo_context():
            rev_old = self._in_repo_rev_to_commit(rev_old)
            rev_young = self._in_repo_rev_to_commit(rev_young)

            process = subprocess.run(
                f"git merge-base --is-ancestor {rev_old} {rev_young}".split(" "),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return process.returncode == 0

    def is_branch_point_ancestor_wrt_master(self, rev_old, rev_young):
        with self.repo_context():
            rev_old = self._in_repo_rev_to_commit(rev_old)
            rev_young = self._in_repo_rev_to_commit(rev_young)
            rev_master = self._in_repo_rev_to_commit("master")
            ca_young = self.get_best_common_ancestor(rev_master, rev_young)
            ca_old = self.get_best_common_ancestor(rev_master, rev_old)

        return self.is_ancestor(ca_old, ca_young)

    def on_same_branch_wrt_master(self, rev_a, rev_b):
        rev_a = self.rev_to_commit(rev_a)
        rev_b = self.rev_to_commit(rev_b)
        rev_master = self.rev_to_commit("master")

        ca_a = self.get_best_common_ancestor(rev_a, rev_master)
        ca_b = self.get_best_common_ancestor(rev_b, rev_master)

        return ca_b == ca_a

    def get_unix_timestamp(self, rev):
        rev = self.rev_to_commit(rev)
        with self.repo_context():
            return int(utils.run_cmd(f"git log -1 --format=%at {rev}"))

    def apply(self, patches: list[PathLike], check: bool = False):
        patches = [str(os.path.abspath(patch)) for patch in patches]
        git_patches = [patch for patch in patches if not patch.endswith(".sh")]
        sh_patches = [f"sh {patch}" for patch in patches if patch.endswith(".sh")]
        check_opt = "--check" if check else ""
        with self.repo_context():
            if check:
                git_cmd = f"git apply --check".split(" ") + git_patches
                sh_patches = [patch_cmd + " --check" for patch_cmd in sh_patches]
            else:
                git_cmd = f"git apply".split(" ") + git_patches

            sh_patches = [patch_cmd.split(" ") for patch_cmd in sh_patches]
            returncode = 0
            for patch_cmd in sh_patches:
                logging.debug(patch_cmd)
                returncode += subprocess.run(
                    patch_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                ).returncode

            if len(git_patches) > 0:
                logging.debug(git_cmd)
                returncode += subprocess.run(
                    git_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                ).returncode

            return returncode == 0

    def next_bisection_commit(self, good: str, bad: str):
        with self.repo_context():
            # request_str = "git rev-list --bisect " + " ".join(bad) + " ^" + " ^".join(good)
            request_str = f"git rev-list --bisect {bad} ^{good}"
            logging.debug(request_str)
            return utils.run_cmd(request_str)


class PatchDB:
    def __init__(self, path_to_db):
        # TODO: maybe enforce this somehow...
        logging.debug(
            "Creating an instance of PatchDB. If you see this message twice, you may have a problem. Only one instance of PatchDB should exist."
        )
        self.path = os.path.abspath(path_to_db)
        with open(self.path, "r") as f:
            self.data = json.load(f)

    def _save_db(func):
        def save_decorator(*args, **kwargs):

            res = func(*args, **kwargs)
            with open(args[0].path, "w") as f:
                json.dump(args[0].data, f, indent=4)
            return res

        return save_decorator

    @_save_db
    def save(self, patch: PathLike, revs: list[str], repo: Repo):
        commits = []
        for rev in revs:
            commits.append(repo.rev_to_commit(rev))
        # To not be computer dependend, just work with the name of the patch
        patch = str(os.path.basename(patch))
        logging.debug(f"Saving entry for {patch}: {commits}")

        if patch not in self.data:
            self.data[patch] = commits
        else:
            self.data[patch].extend(commits)

        # Make entries unique
        self.data[patch] = list(set(self.data[patch]))

    @_save_db
    def save_bad(self, patches: list[PathLike], rev: str, repo: Repo, compiler_config):
        logging.debug(f"Saving bad: {compiler_config.name} {rev} {patches}")
        patches = [str(os.path.basename(patch)) for patch in patches]
        rev = repo.rev_to_commit(rev)

        if "bad" not in self.data:
            self.data["bad"] = {}

        if compiler_config.name not in self.data["bad"]:
            self.data["bad"][compiler_config.name] = {}

        if rev not in self.data["bad"][compiler_config.name]:
            self.data["bad"][compiler_config.name][rev] = []

        self.data["bad"][compiler_config.name][rev].append(patches)

    @_save_db
    def clear_bad(self, patches: list[PathLike], rev: str, repo: Repo, compiler_config):
        logging.debug(f"Clearing bad: {compiler_config.name} {rev} {patches}")
        patches = [str(os.path.basename(patch)) for patch in patches]
        rev = repo.rev_to_commit(rev)

        if (
            "bad" not in self.data
            or compiler_config.name not in self.data["bad"]
            or rev not in self.data["bad"][compiler_config.name]
        ):
            return

        good_hash = hash("".join(patches))
        list_bad = self.data["bad"][compiler_config.name][rev]
        list_bad = [combo for combo in list_bad if hash("".join(combo)) != good_hash]

        self.data["bad"][compiler_config.name][rev] = list_bad

    def is_known_bad(
        self, patches: list[PathLike], rev: str, repo: Repo, compiler_config
    ):
        patches = [str(os.path.basename(patch)) for patch in patches]
        rev = repo.rev_to_commit(rev)

        if "bad" not in self.data:
            return False

        if compiler_config.name not in self.data["bad"]:
            return False

        if rev not in self.data["bad"][compiler_config.name]:
            return False

        current_hash = hash("".join(patches))
        for known_bad in self.data["bad"][compiler_config.name][rev]:
            if current_hash == hash("".join(sorted(known_bad))):
                return True

        return False

    def required_patches(self, rev: str, repo: Repo) -> list[PathLike]:
        commit = repo.rev_to_commit(rev)
        required_patches = []
        for patch, patch_commits in self.data.items():
            if commit in patch_commits:
                required_patches.append(os.path.abspath(pjoin("patches", patch)))
        return required_patches

    def requires_this_patch(self, rev, patch, repo: Repo) -> bool:
        rev = repo.rev_to_commit(rev)
        patch = os.path.basename(patch)
        if patch not in self.data:
            return False
        else:
            return rev in self.data[patch]

    @_save_db
    def manual_intervention_required(self, compiler_config, rev: str):
        if "manual" not in self.data:
            self.data["manual"] = []

        self.data["manual"].append(f"{compiler_config.name} {rev}")
        self.data["manual"] = list(set(self.data["manual"]))

    def in_manual(self, compiler_config, rev: str) -> bool:
        if "manual" not in self.data:
            return False
        else:
            return f"{compiler_config.name} {rev}" in self.data["manual"]


class Patcher:
    def __init__(self, config, patchdb: PatchDB, cores: Optional[int] = None):
        self.config = config
        self.patchdb = patchdb
        self.builder = builder.Builder(config, self.patchdb, cores=cores)

    def _check_building_patch(
        self, compiler_config, rev: str, patch: os.PathLike, repo: Repo
    ) -> tuple[bool, Optional[bool]]:

        if not self.patchdb.requires_this_patch(rev, patch, repo):
            try:
                logging.info(f"Building {rev} without patch {patch}...")
                self.builder.build(compiler_config, rev)
                return True, None

            except builder.BuildException as e:
                logging.info(f"Failed to build {rev} without patch {patch}: {e}")

            try:
                logging.info(f"Building {rev} WITH patch {patch}...")
                self.builder.build(compiler_config, rev, additional_patches=[patch])
                return False, True

            except builder.BuildException as e:
                logging.critical(
                    f"Failed to build {rev} with patch {patch}. Manual intervention needed. Exception: {e}"
                )
                self.patchdb.manual_intervention_required(compiler_config, rev)
                return False, False
        else:
            logging.info(f"Read form PatchDB: {rev} requires patch {patch}")
            return False, True

    def _bisection(
        self,
        good_rev: str,
        bad_rev: str,
        compiler_config,
        patch: os.PathLike,
        repo: Repo,
        failure_is_good: bool = False,
        max_double_fail: int = 2,
    ) -> tuple[str, str]:

        good = [good_rev]
        bad = [bad_rev]

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

                if double_fail_counter % 2 == 0:
                    # Get size of range
                    range_size = len(repo.direct_first_parent_path(midpoint, bad[-1]))

                    # Move 10% towards the last bad
                    step = max(int(0.9 * range_size), 1)
                    midpoint = repo.rev_to_commit(f"{bad[-1]}~{step}")
                else:
                    # Symmetric to case above
                    range_size = len(repo.direct_first_parent_path(good[-1], midpoint))
                    step = max(int(0.1 * range_size), 1)
                    midpoint = repo.rev_to_commit(f"{midpoint}~{step}")

                double_fail_counter += 1
                encountered_double_fail = False

            else:
                old_midpoint = midpoint
                midpoint = repo.next_bisection_commit(good=good[-1], bad=bad[-1])
                logging.info(f"Midpoint: {midpoint}")
                if midpoint == "" or midpoint == old_midpoint:
                    break

            built_wo_patch, built_w_patch = self._check_building_patch(
                compiler_config, midpoint, patch, repo
            )

            if built_wo_patch:
                if failure_is_good:
                    bad.append(midpoint)
                else:
                    good.append(midpoint)
                continue

            if built_w_patch:
                if failure_is_good:
                    good.append(midpoint)
                else:
                    bad.append(midpoint)
                continue

            encountered_double_fail = True

        return good[-1], bad[-1]

    def find_ranges(
        self, compiler_config: utils.NestedNamespace, patchable_commit, patch
    ):
        introducer = ""
        found_introducer = False
        repo = Repo(compiler_config.repo, compiler_config.main_branch)

        potentially_human_readable_name = patchable_commit
        patchable_commit = repo.rev_to_commit(patchable_commit)
        patch = os.path.abspath(patch)
        if not Path(patch).exists():
            logging.critical(f"Patch {patch} doesn't exist. Aborting...")
            raise Exception(f"Patch {patch} doesn't exist. Aborting...")

        # For now, just assume this is sorted in descending release-recency
        # Using commit dates doesn't really work
        # TODO: do something with `from packaging import version; version.parse()`
        release_versions = ["trunk"] + compiler_config.releases
        release_versions.reverse()

        tested_ancestors = []
        no_patch_common_ancestor = ""
        oldest_patchable_ancestor = ""
        for old_version in release_versions:

            logging.info(f"Testing for {old_version}")
            if not repo.is_branch_point_ancestor_wrt_master(
                old_version, patchable_commit
            ):
                if oldest_patchable_ancestor != "":
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
            built_wo_patch, built_w_patch = self._check_building_patch(
                compiler_config, common_ancestor, patch, repo
            )

            if built_wo_patch:
                no_patch_common_ancestor = common_ancestor
                break

            if built_w_patch:
                if oldest_patchable_ancestor == "":  # None have been found
                    oldest_patchable_ancestor = common_ancestor
            else:
                tested_ancestors.append(common_ancestor)

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

        if no_patch_common_ancestor != "":
            # Find introducer commit
            _, introducer = self._bisection(
                no_patch_common_ancestor, patchable_commit, compiler_config, patch, repo
            )

            # Insert from introducer to and with patchable_commit as requiring patching
            # This is of course not the complete range but will help when bisecting
            rev_range = f"{introducer}~..{patchable_commit}"
            self.patchdb.save(patch, repo.rev_to_commit_list(rev_range), repo)

            # Do what is happening for oldest_patchable_ancestor for introducer
            self.find_fixer_from_introducer_to_releases(
                introducer=introducer,
                compiler_config=compiler_config,
                patch=patch,
                repo=repo,
            )

        elif oldest_patchable_ancestor != "":
            self.find_fixer_from_introducer_to_releases(
                introducer=oldest_patchable_ancestor,
                compiler_config=compiler_config,
                patch=patch,
                repo=repo,
            )

    def find_fixer_from_introducer_to_releases(
        self, introducer: str, compiler_config, patch: PathLike, repo: Repo
    ) -> None:
        logging.info(f"Starting bisection of fixer commits from {introducer}...")

        # Find reachable releases
        reachable_releases = [
            repo.rev_to_commit(release)
            for release in compiler_config.releases
            if repo.is_ancestor(introducer, release)
        ]

        fixer_list = []
        for release in reachable_releases:
            logging.info(f"Searching fixer for release {release}")

            no_patch_release, w_patch_release = self._check_building_patch(
                compiler_config, release, patch, repo
            )

            # Check if any of already found fixers is ancestor of release
            # As we assume that a fixer at a given point fixes all its children, this is fine.
            # What about release backporting? For example 8.5.0 and 8.4.0 both get an update just thrown
            # into their history and 8.4.0 is still ancestor of 8.5.0; then we have a problem: TODO
            logging.info(f"Checking for known fixers...")
            if (
                len(fixer_list) > 0
                and no_patch_release
                and any([repo.is_ancestor(fixer, release) for fixer in fixer_list])
            ):
                logging.info(
                    f"Already known fixer {fixer} is ancestor of {release}. No additional searching required"
                )
                continue

            if not no_patch_release and not w_patch_release:
                continue

            elif not no_patch_release and w_patch_release:
                # release only builds with patch, everything to release is to be included
                commits = repo.rev_to_commit_list(f"{introducer}~1..{release}")
                self.patchdb.save(patch, commits, repo)
                continue

            elif no_patch_release and not w_patch_release:

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
        compiler_config,
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

    def find_introducer(self, compiler_config, broken_rev: str):
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

    cores = None if args.cores is None else args.cores

    patchdb = PatchDB(config.patchdb)
    p = Patcher(config, patchdb, cores=cores)

    if args.find_range:
        problems = []
        if args.patch is None:
            problems.append("Missing argument for `patch` when using --find-range.")
        else:
            patch = args.patch[0]

        if args.compiler is None:
            problems.append("Missing argument for `compiler` when using --find-range.")
        else:
            compiler = args.compiler[0]
            if compiler == "gcc":
                compiler_config = config.gcc
            elif compiler == "llvm" or compiler == "clang":
                compiler_config = config.llvm
            else:
                problems.append(
                    f"Unknown compiler {compiler}. gcc and llvm/clang are supported options."
                )

        if args.patchable_revision is None:
            problems.append(
                "Missing argument for `patchable-revision` when using --find-range."
            )
        else:
            patchable_commit = args.patchable_revision[0]

        if len(problems) > 0:
            print("Some arguments required for --find-range have problems:")
            for pr in problems:
                print(" - " + pr)
            exit(1)
        else:
            p.find_ranges(
                compiler_config, patchable_commit=patchable_commit, patch=patch
            )

    # ====================
    elif args.find_introducer:
        problems = []

        if args.broken_revision is None:
            problems.append(
                "Missing argument for `broken-revision` when using --find-introducer."
            )
        else:
            broken_rev = args.broken_revision[0]

        if args.compiler is None:
            problems.append(
                "Missing argument for `compiler` when using --find-introducer."
            )
        else:
            compiler = args.compiler[0]
            if compiler == "gcc":
                compiler_config = config.gcc
            elif compiler == "llvm" or compiler == "clang":
                compiler_config = config.llvm
            else:
                problems.append(
                    f"Unknown compiler {compiler}. gcc and llvm/clang are supported options."
                )

        if len(problems) > 0:
            print("Some arguments required for --find-introducer have problems:")
            for pr in problems:
                print(" - " + pr)
            exit(1)
        else:
            p.find_introducer(compiler_config, broken_rev)
