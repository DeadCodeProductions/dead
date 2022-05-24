#!/usr/bin/env python3

import grp
import json
import os
import shutil
import stat
from pathlib import Path
from typing import Any

import utils

from dead_instrumenter.utils import find_binary, Binary


def main() -> None:
    print(
        "Have you installed the following programs/projects: llvm, clang, compiler-rt, gcc, cmake, ccomp, csmith and creduce?"
    )
    print("Press enter to continue if you believe you have")
    input()

    not_found = []
    for p in ["clang", "gcc", "cmake", "ccomp", "csmith", "creduce"]:
        if not shutil.which(p):
            not_found.append(p)

    if not_found:
        print("Can't find", " ".join(not_found), " in $PATH.")

    if not Path("/usr/include/llvm/").exists():
        print("Can't find /usr/include/llvm/")
        not_found.append("kill")

    if not_found:
        exit(1)

    print("Creating default ~/.config/dead/config.json...")

    path = Path.home() / ".config/dead/config.json"
    if path.exists():
        print(f"{path} already exists! Aborting to prevent overriding data...")
        exit(1)

    config: dict[Any, Any] = {}
    # ====== GCC ======
    gcc: dict[str, Any] = {}
    gcc["name"] = "gcc"
    gcc["main_branch"] = "master"

    # Git clone repo
    print("Cloning gcc to ./gcc ...")
    if not Path("./gcc").exists():
        utils.run_cmd("git clone git://gcc.gnu.org/git/gcc.git")
    gcc["repo"] = "./gcc"

    if shutil.which("gcc"):
        gcc["sane_version"] = "gcc"
    else:
        gcc["sane_version"] = "???"
        print(
            "gcc is not in $PATH, you have to specify the executable yourself in gcc.sane_version"
        )

    gcc["releases"] = [
        "trunk",
        "releases/gcc-11.2.0",
        "releases/gcc-11.1.0",
        "releases/gcc-10.3.0",
        "releases/gcc-10.2.0",
        "releases/gcc-10.1.0",
        "releases/gcc-9.4.0",
        "releases/gcc-9.3.0",
        "releases/gcc-9.2.0",
        "releases/gcc-9.1.0",
        "releases/gcc-8.5.0",
        "releases/gcc-8.4.0",
        "releases/gcc-8.3.0",
        "releases/gcc-8.2.0",
        "releases/gcc-8.1.0",
        "releases/gcc-7.5.0",
        "releases/gcc-7.4.0",
        "releases/gcc-7.3.0",
        "releases/gcc-7.2.0",
    ]
    config["gcc"] = gcc

    # ====== LLVM ======
    llvm: dict[str, Any] = {}
    llvm["name"] = "clang"
    llvm["main_branch"] = "main"

    # Git clone repo
    print("Cloning llvm to ./llvm-project ...")
    if not Path("./llvm-project").exists():
        utils.run_cmd("git clone https://github.com/llvm/llvm-project")
    llvm["repo"] = "./llvm-project"

    if shutil.which("clang"):
        llvm["sane_version"] = "clang"
    else:
        llvm["sane_version"] = "???"
        print(
            "clang is not in $PATH, you have to specify the executable yourself in llvm.sane_version"
        )

    llvm["releases"] = [
        "trunk",
        "llvmorg-13.0.1",
        "llvmorg-13.0.0",
        "llvmorg-12.0.1",
        "llvmorg-12.0.0",
        "llvmorg-11.1.0",
        "llvmorg-11.0.1",
        "llvmorg-11.0.0",
        "llvmorg-10.0.1",
        "llvmorg-10.0.0",
        "llvmorg-9.0.1",
        "llvmorg-9.0.0",
        "llvmorg-8.0.1",
        "llvmorg-8.0.0",
        "llvmorg-7.1.0",
        "llvmorg-7.0.1",
        "llvmorg-7.0.0",
        "llvmorg-6.0.1",
        "llvmorg-6.0.0",
        "llvmorg-5.0.2",
        "llvmorg-5.0.1",
        "llvmorg-5.0.0",
        "llvmorg-4.0.1",
        "llvmorg-4.0.0",
    ]

    config["llvm"] = llvm
    # ====== CSmith ======
    csmith: dict[str, Any] = {}
    csmith["max_size"] = 50000
    csmith["min_size"] = 10000
    if shutil.which("csmith"):
        csmith["executable"] = "csmith"
        res = utils.run_cmd("csmith --version")
        # $ csmith --version
        # csmith 2.3.0
        # Git version: 30dccd7
        version = res.split("\n")[0].split()[1]
        csmith["include_path"] = "/usr/include/csmith-" + version
    else:
        print(
            "Can't find csmith in $PATH. You have to specify the executable and the include path yourself"
        )
        csmith["executable"] = "???"
        csmith["include_path"] = "???"
    config["csmith"] = csmith

    # ====== Cpp programs ======

    find_binary(Binary.INSTRUMENTER, no_questions=True)
    config["dcei"] = "dead-instrument"

    print("Compiling callchain checker (ccc)...")
    os.makedirs("./callchain_checker/build", exist_ok=True)
    utils.run_cmd("cmake ..", working_dir=Path("./callchain_checker/build/"))
    utils.run_cmd("make -j", working_dir=Path("./callchain_checker/build/"))
    config["ccc"] = "./callchain_checker/build/bin/ccc"

    # ====== Rest ======
    config["patchdb"] = "./patches/patchdb.json"

    os.makedirs("logs", exist_ok=True)
    config["logdir"] = "./logs"

    config["cache_group"] = grp.getgrgid(os.getgid()).gr_name

    os.makedirs("compiler_cache", exist_ok=True)
    shutil.chown("compiler_cache", group=config["cache_group"])
    os.chmod("compiler_cache", 0o770 | stat.S_ISGID)
    config["cachedir"] = "./compiler_cache"

    config["creduce"] = "creduce"
    if not shutil.which("creduce"):
        print(
            "creduce was not found in $PATH. You have to specify the executable yourself"
        )
        config["creduce"] = "???"

    config["ccomp"] = "ccomp"
    if not shutil.which("ccomp"):
        print(
            "ccomp was not found in $PATH. You have to specify the executable yourself"
        )
        config["ccomp"] = "???"

    config["casedb"] = "./casedb.sqlite3"

    Path(config["casedb"]).touch()
    shutil.chown(config["casedb"], group=config["cache_group"])
    os.chmod(config["casedb"], 0o660)

    print("Saving config...")
    os.makedirs(path.parent, exist_ok=True)
    with open(path, "w") as f:
        json.dump(config, f, indent=4)

    print("Done!")


if __name__ == "__main__":
    main()
