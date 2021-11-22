import logging
import os
import subprocess
from contextlib import contextmanager
from pathlib import Path

import utils


class Repo:
    def __init__(self, path: os.PathLike, main_branch: str):
        self.path = os.path.abspath(path)
        self._showed_stale_warning = False
        self.main_branch = main_branch

    def get_best_common_ancestor(self, rev_a, rev_b):
        a = self.rev_to_commit(rev_a)
        b = self.rev_to_commit(rev_b)
        return utils.run_cmd(f"git -C {self.path} merge-base {a} {b}")

    def rev_to_commit(self, rev):
        # Could support list of revs...
        if rev == "trunk" or rev == "master" or rev == "main":
            if not self._showed_stale_warning:
                logging.warning(
                    "Reminder: trunk/master/main/hauptzweig/principale is stale"
                )
                self._showed_stale_warning = True
            rev = self.main_branch
        return utils.run_cmd(f"git -C {self.path} rev-parse {rev}")

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

        # Get all commits with at least 2 parents
        merges_after_introducer = utils.run_cmd(
            f"git -C {self.path} rev-list --merges {introducer}~..{fixer}"
        )
        if len(merges_after_introducer) > 0:
            # Get all parent commits of these (so for C it would be H, Z and R)
            cmd = f"git -C {self.path} rev-parse " + "^@ ".join(merges_after_introducer)
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
        cmd = f"git -C {self.path} rev-list {fixer} ^{introducer} " + " ^".join(
            unwanted_merger_parents
        )
        res = [commit for commit in utils.run_cmd(cmd).split("\n") if commit != ""] + [
            introducer
        ]
        return res

    def direct_first_parent_path(self, older: str, younger: str) -> list[str]:
        cmd = f"git -C {self.path} rev-list --first-parent {younger} ^{older}"
        res = [commit for commit in utils.run_cmd(cmd).split("\n") if commit != ""] + [
            older
        ]
        return res

    def rev_to_commit_list(self, rev):
        # TODO: maybe merge with rev_to_commit...
        return utils.run_cmd(f"git -C {self.path} log --format=%H {rev}").split("\n")

    def is_ancestor(self, rev_old, rev_young) -> bool:
        rev_old = self.rev_to_commit(rev_old)
        rev_young = self.rev_to_commit(rev_young)

        process = subprocess.run(
            f"git -C {self.path} merge-base --is-ancestor {rev_old} {rev_young}".split(
                " "
            ),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return process.returncode == 0

    def is_branch_point_ancestor_wrt_master(self, rev_old, rev_young):
        rev_old = self.rev_to_commit(rev_old)
        rev_young = self.rev_to_commit(rev_young)
        rev_master = self.rev_to_commit("master")
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
        return int(utils.run_cmd(f"git -C {self.path} log -1 --format=%at {rev}"))

    def apply(self, patches: list[os.PathLike[str]], check: bool = False):
        patches = [Path(os.path.abspath(patch)) for patch in patches]
        git_patches = [
            str(patch) for patch in patches if not str(patch).endswith(".sh")
        ]
        sh_patches = [f"sh {patch}" for patch in patches if str(patch).endswith(".sh")]
        if check:
            git_cmd = f"git -C {self.path} apply --check".split(" ") + git_patches
            sh_patches = [patch_cmd + " --check" for patch_cmd in sh_patches]
        else:
            git_cmd = f"git -C {self.path} apply".split(" ") + git_patches

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
        request_str = f"git -C {self.path} rev-list --bisect {bad} ^{good}"
        logging.debug(request_str)
        return utils.run_cmd(request_str)
