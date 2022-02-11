from __future__ import annotations

import json
import logging
import os
from os.path import join as pjoin
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, TypeVar, Union

from repository import Repo

if TYPE_CHECKING:
    from utils import NestedNamespace

T = TypeVar("T")


def _save_db(func: Callable[..., T]) -> Callable[..., T]:
    def save_decorator(db: PatchDB, *args: list[Any], **kwargs: dict[Any, Any]) -> T:

        res = func(db, *args, **kwargs)
        with open(db.path, "w") as f:
            json.dump(db.data, f, indent=4)
        return res

    return save_decorator


class PatchDB:
    def __init__(self, path_to_db: Path):
        logging.debug(
            "Creating an instance of PatchDB. If you see this message twice, you may have a problem. Only one instance of PatchDB should exist."
        )
        self.path = os.path.abspath(path_to_db)
        with open(self.path, "r") as f:
            self.data: dict[str, Any] = json.load(f)

    @_save_db
    def save(self, patch: Path, revs: list[str], repo: Repo) -> None:
        commits = []
        for rev in revs:
            commits.append(repo.rev_to_commit(rev))
        # To not be computer dependend, just work with the name of the patch
        patch_basename = os.path.basename(patch)
        logging.debug(f"Saving entry for {patch_basename}: {commits}")

        if patch_basename not in self.data:
            self.data[patch_basename] = commits
        else:
            self.data[patch_basename].extend(commits)

        # Make entries unique
        self.data[patch_basename] = list(set(self.data[patch_basename]))

    @_save_db
    def save_bad(
        self,
        patches: list[Path],
        rev: str,
        repo: Repo,
        compiler_config: NestedNamespace,
    ) -> None:
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
        self,
        patches: list[Path],
        rev: str,
        repo: Repo,
        compiler_config: NestedNamespace,
    ) -> None:
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
        self,
        patches: list[Path],
        rev: str,
        repo: Repo,
        compiler_config: NestedNamespace,
    ) -> bool:
        """Checks if a given compiler-revision-patches combination
        has already been tested and failed to build.

        Args:
            self:
            patches (list[Path]): patches
            rev (str): rev
            repo (Repo): repo
            compiler_config (NestedNamespace): compiler_config

        Returns:
            bool:
        """
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

    def required_patches(self, rev: str, repo: Repo) -> list[Path]:
        """Get the known required patches form the database.

        Args:
            self:
            rev (str): rev
            repo (Repo): repo

        Returns:
            list[Path]: List of known required patches.
        """
        commit = repo.rev_to_commit(rev)

        required_patches = []
        for patch, patch_commits in self.data.items():
            if commit in patch_commits:
                required_patches.append(Path(os.path.abspath(pjoin("patches", patch))))
        return required_patches

    def requires_this_patch(self, rev: str, patch: Path, repo: Repo) -> bool:
        rev = repo.rev_to_commit(rev)
        patch_basename = os.path.basename(patch)
        if patch_basename not in self.data:
            return False
        else:
            return rev in self.data[patch_basename]

    def requires_all_these_patches(
        self, rev: str, patches: list[Path], repo: Repo
    ) -> bool:
        rev = repo.rev_to_commit(rev)
        patch_basenames = [os.path.basename(patch) for patch in patches]
        if any(patch_basename not in self.data for patch_basename in patch_basenames):
            return False
        else:
            return all(
                rev in self.data[patch_basename] for patch_basename in patch_basenames
            )

    @_save_db
    def manual_intervention_required(
        self, compiler_config: NestedNamespace, rev: str
    ) -> None:
        if "manual" not in self.data:
            self.data["manual"] = []

        self.data["manual"].append(f"{compiler_config.name} {rev}")
        self.data["manual"] = list(set(self.data["manual"]))

    def in_manual(self, compiler_config: NestedNamespace, rev: str) -> bool:
        if "manual" not in self.data:
            return False
        else:
            return f"{compiler_config.name} {rev}" in self.data["manual"]
