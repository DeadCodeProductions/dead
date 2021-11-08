import json
import logging
import os
from os.path import join as pjoin
from pathlib import Path

from repository import Repo


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
    def save(self, patch: os.PathLike[str], revs: list[str], repo: Repo):
        commits = []
        for rev in revs:
            commits.append(repo.rev_to_commit(rev))
        # To not be computer dependend, just work with the name of the patch
        patch = Path(os.path.basename(patch))
        logging.debug(f"Saving entry for {patch}: {commits}")

        if patch not in self.data:
            self.data[patch] = commits
        else:
            self.data[patch].extend(commits)

        # Make entries unique
        self.data[patch] = list(set(self.data[patch]))

    @_save_db
    def save_bad(
        self, patches: list[os.PathLike], rev: str, repo: Repo, compiler_config
    ):
        logging.debug(f"Saving bad: {compiler_config.name} {rev} {patches}")
        patches_str = [str(os.path.basename(patch)) for patch in patches]
        rev = repo.rev_to_commit(rev)

        if "bad" not in self.data:
            self.data["bad"] = {}

        if compiler_config.name not in self.data["bad"]:
            self.data["bad"][compiler_config.name] = {}

        if rev not in self.data["bad"][compiler_config.name]:
            self.data["bad"][compiler_config.name][rev] = []

        self.data["bad"][compiler_config.name][rev].append(patches_str)

    @_save_db
    def clear_bad(
        self, patches: list[os.PathLike], rev: str, repo: Repo, compiler_config
    ):
        logging.debug(f"Clearing bad: {compiler_config.name} {rev} {patches}")
        patches_str = [str(os.path.basename(patch)) for patch in patches]
        rev = repo.rev_to_commit(rev)

        if (
            "bad" not in self.data
            or compiler_config.name not in self.data["bad"]
            or rev not in self.data["bad"][compiler_config.name]
        ):
            return

        good_hash = hash("".join(patches_str))
        list_bad = self.data["bad"][compiler_config.name][rev]
        list_bad = [combo for combo in list_bad if hash("".join(combo)) != good_hash]

        self.data["bad"][compiler_config.name][rev] = list_bad

    def is_known_bad(
        self, patches: list[os.PathLike], rev: str, repo: Repo, compiler_config
    ):
        patches_str = [str(os.path.basename(patch)) for patch in patches]
        rev = repo.rev_to_commit(rev)

        if "bad" not in self.data:
            return False

        if compiler_config.name not in self.data["bad"]:
            return False

        if rev not in self.data["bad"][compiler_config.name]:
            return False

        current_hash = hash("".join(patches_str))
        for known_bad in self.data["bad"][compiler_config.name][rev]:
            if current_hash == hash("".join(sorted(known_bad))):
                return True

        return False

    def required_patches(self, rev: str, repo: Repo) -> list[os.PathLike]:
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
