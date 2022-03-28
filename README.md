# DEAD: Dead Code Elimination based Automatic Differential Testing

DEAD is a tool to find and process compiler regressions and other missed optimizations automatically to produce reports.

For a list of reported bugs look at [bugs.md](./bugs.md).

## Setup
### Setup with Docker
```
./build_docker.sh 

# Enter the container
docker run -it -v deadpersistent:/persistent deaddocker
```
Continue by reading the [Run Section](##Run).

### Local Setup
The following programs or libraries must be installed:
- `python >= 3.9`
- `gcc`
- `clang`
- `csmith`
- `creduce`
- `cmake`
- `ccomp` (CompCert)
- `llvm 13.0.0` (for the include files)
- `compiler-rt` (for the sanitization libraries. It's also part of LLVM)
- `boost`
- `ninja`

Optional programs:
- `entr`

We are running on Arch Linux and have not (yet) tested any other distribution.

To achieve this in Arch with `yay` as AUR overlay helper, you can run:
```
yay -Sy --noconfirm python\
                    python-pip\
                    gcc\
                    clang\
                    llvm\
                    compiler-rt\
                    cmake\
                    boost\
                    ninja\
                    csmith\
                    creduce-git\
                    compcert-git
```

Then run:
```
# Create python environment
python3 -m venv ./deadenv
source ./deadenv/bin/activate
pip install requests

# Initialize DEAD
./init.py
```
`init.py` will:
- create a config file located at `~/.config/dead/config.json`
- Compile tooling to instrument and check programs: `dcei`, `static-annotator`, `ccc`
- Clone repositories of `gcc` and `llvm` into the local directory
- Create the `compiler_cache` and `logs` directory
- Check if it can find the programs and paths required in the prerequisite-section and complain if not.


## Run
As DEAD is based on differential testing, it requires two informations to be able to run:
- Which compilers to find missed optimizations in. These are called *target* compilers. This is typically the current `trunk`.
- Which compilers to use as a comparison to find missed optimizations in the target compilers. These are called *additional* or *attacking* compilers.

A compiler on the CLI is specified by writing `PROJECT REVISION [OPT_LEVEL ...]`. For example, to get `gcc 11.2.0` with all optimizations, write `gcc releases/gcc-11.2.0 1 2 3 s`. This can be repeated to specify more compilers.

```sh
# Don't run it yet
./main.py run --targets gcc trunk 1 2 3 s\
              --additional-compilers\
                   gcc releases/gcc-11.2.0 1 2 3 s\
                   gcc releases/gcc-10.3.0 1 2 3 s
```
To not have to repeat oneself, it is possible to specify default optimization levels.
The resulting used optimizations for a specified compiler is the union of the default levels and the specifically specified optimization levels.
The flags are `--additional_compilers_default_opt_levels` and `--targets_default_opt_levels` or `-acdol` and `-tdol` respectively.


```sh
# Don't run it yet
./main.py run --targets gcc trunk 1 2 3 s\
              --additional-compilers\
                   gcc releases/gcc-11.2.0 \ # Opt levels: 3,s
                   gcc releases/gcc-10.3.0 1\ # Opt levels: 1,3,s
              -acdol 3 s # Additional compilers 
```

DEAD consists of three parts which are: 
- Generator, which finds missed optimizations from the given target and attacking compilers. We call such a missed optimization and any additional information related to it a *case*.
- Bisector, which finds the introducing commit of the found case.
- Reducer, which extracts a small part of the code, which still exhibits the missed optimization found.

By default, the Reducer is only enabled for cases which have a new bisection commit, as reducing takes long and is often not necessary.
It can be enabled for all cases with `--reducer` and completely disabled with `--no-reducer`.

The last two important options are `--cores POSITIVE_INT` and `--log-level debug|info|warning|error|critical`. 
When not specified, `--cores` will equal to the amount of logical cores on the machine.
The default verbosity level is `warning`. However, to have a sense of progress, we suggest setting it to `info`.

Finally, to find missed optimizations in `trunk`, run
```sh
# For GCC
./main.py -ll info\
          --cores $CORES\
          run --targets gcc trunk 1 2 3 s\ 
              --additional-compilers\
                   gcc releases/gcc-11.2.0\
                   gcc releases/gcc-10.3.0\
                   gcc releases/gcc-9.4.0\
                   gcc releases/gcc-8.5.0\
                   gcc releases/gcc-7.5.0\
              -acdol 1 2 3 s
              #--amount N # Terminate after finding N cases

# For LLVM
./main.py -ll info\
          --cores $CORES\
          run --targets llvm trunk 1 2 3 s z\ 
              --additional-compilers\
                   llvm llvmorg-13.0.0\
                   llvm llvmorg-12.0.1\
                   llvm llvmorg-11.1.0\
                   llvm llvmorg-10.0.1\
                   llvm llvmorg-9.0.1\
                   llvm llvmorg-8.0.1\
                   llvm llvmorg-7.1.0\
                   llvm llvmorg-6.0.1\
                   llvm llvmorg-5.0.2\
                   llvm llvmorg-4.0.1\
              -acdol 1 2 3 s z
              #--amount N # Terminate after finding N cases
```

Please run `./main.py run -h` and `./main.py -h` to see more options.

### Performance considerations
Assigning all cores of the machine to just one instance of DEAD can lead to less than optimal machine utilization. Some parts of the pipeline can not always use all cores.

- The Bisector is written in a single threaded way and only requires multiple cores when building a new compiler.
As the cache grows and many regression have already been found, the cache hit rate increases drastically, making the Bisector essentially a single threaded part.
- GCC compilation includes several single-threaded parts. Compiling with sufficiently many cores will make it look like a mostly single-threaded task due to Amdahl's law. LLVM compilation also includes some single-threaded parts, but these are way less noticeable.
- The Reducer uses `creduce` to shrink the case. `creduce` also does not perfectly utilize the machine all the time, when using a lot of threads.

Just oversubscribing the machine is not an option, as some checks are time dependent. Failing these checks will especially impact the throughput of the Reducer.

One fairly good solution is to run multiple smaller instances in parallel.

For the Reducer, 8 logical cores per pipeline did yield good results.

Finding new cases in parallel has the big caveat that the instances wait on each other when one is building a compiler that the other needs. This dependence is very common when the cache is not populated enough. Running multiple instances in parallel too early is detrimental to machine utilization!

Pinpointing when the switch to multiple instances is beneficial is difficult. 
For this reason we provide `run_parallel.sh` which spawns multiple instances with the appropriate amount of cores assigned.
```sh
./run_parallel.sh llvm|gcc TOTAL_CORES AMOUNT_JOBS
```

## Generating a report

Imagine DEAD ran for some time and it is now time to create a bug report.

Not-yet-reported cases can be explored with the `unreported` sub-command.

```sh
$ ./main.py unreported
ID       Bisection                                     Count
----------------------------------------------------------------
2        0b92cf305dcf34387a8e2564e55ca8948df3b47a      45
...
39       008e7397dad971c03c08fc1b0a4a98fddccaaed8      1
----------------------------------------------------------------
ID       Bisection                                     Count
```
On the left you see an ID for a case that has the bisection commit shown in the bisection column.
Often times, many cases are found which bisect to the same commit. How many cases that bisected to this particular commit have been found is displayed in the 'Count' column. 
Note that a fix for a reported case may not fix all cases of the bisection!

Select one of the IDs and check if there is already a bug report which includes its bisection commit.

If this is not the case, run
```sh
./main.py report $ID > report.txt
```

It will pull the compiler project of the case, build `trunk` and test if the missed optimization can still be observed. 
You can disable pulling with `--no-pull`.
If so, it will output a copy-and-pasteable report into `report.txt` (don't forget to remove the title if there is one) and `case.txt`[^1],  a copy of the reported code.
[^1]: It is `.txt` instead of `.c` because GitHub does not allow `.c` files to be attached to issues.

When you have submitted the bug report, you can save the link to the report via
```
./main.py set link $ID $LINK
```
so that the bisection isn't displayed anymore.

Hopefully, the missed optimization gets fixed. When this is the case, you can extract the case ID from the bug report and note down the fixing commit. Then save it with
```
./main.py set fixed $ID $COMMIT
```

Inspecting reported cases can be done via
```
./main.py reported
```

### Massaging workflow
Sometimes it is possible to further reduce the automatically reduced code manually. We call this step *massaging*, the product of which is *massaged code*.

Instead of directly generating the report after having selected an ID and checked if the bisection commit was already reported, get the reduced code and try to make it smaller.
```sh
./main.py get rcode $ID > rcode.c
```
To continuously check if the changes still exhibit the missed optimization, open a separate terminal in the same directory and run 
```sh
echo rcode.c | entr -c ./main.py checkreduced $ID ./rcode.c
```
This will rerun some checks whenever `rcode.c` is saved.

When the massaging is done, save it into DEAD with
```sh
./main.py set mcode $ID ./rcode.c
```
DEAD will check if the massaged code still bisects to the same commit as before and will reject the change if not.
Empirically, changes to cases who's bisection is rarely found often don't allow any further massaging.

## Subcommand overview of `main.py`

- `run`: Find new regressions/missed optimizations.
- `tofile ID`: Save a case into a tar-file.
- `absorb PATH`: Read tar-files into the database of DEAD.
- `report ID`: Generate a report for a given case.
- `rereduce ID FILE`: Reduce a file (again) w.r.t. a case.
- `diagnose`: Run a set of tests when something seems odd with a case.
- `checkreduced ID FILE`: Run some lightweight tests based on a case on a piece of code.
- `cache`: Cache related functionality.
- `asm ID`: Generate assembly for all code of a case. 
- `set | get {link,fixed,mcode,rcode,ocode,bisection}`: Set or get the specified field of a case.
- `build PROJECT REV`: Build `REV` of compiler project `PROJECT`.
- `reduce ID`: Reduce case `ID`.
- `edit`: Open DEADs configuration in `$EDITOR`
- `unreported`: List unreported cases grouped by bisection commit.
- `reported`: List reported cases.
- `findby`: Find case ID given some part of the case.

## Overview of important files
- `bisector.py`: Bisects a given interesting case.
- `builder.py`: Builds the compiler.
- `checker.py`: Checks if a given case is interesting.
- `generator.py`: Finds new interesting cases.
- `patcher.py`: Automatically finds the region in the history where a patch needs to be applied.
- `reducer.py`: Reduce the code of a given.

## Q&A for potential issues
### I set flag X which I found in the help, but DEAD says the option does not exist!
Sadly, flags are position dependent. You have to put it after the command whose help you found the flag in and before any other subcommand.
### I want to do XYZ. How?
Maybe there's already an option for it. Consult the program with `--help` for all the options.

### Why don't I see anything?
Are you running with `-ll info`?

### DEAD wants to work with a commit that doesn't exist!
If you are checking things manually: Are you sure you are looking in the right repository?

If you are processing a case and `git` throws an exception, try pulling `llvm-project` and `gcc` so you are sure to have all the commits.

### Why does this case fail?
Maybe `./main.py diagnose -ci $ID` can illuminate the situation.

### This case does not reduce but `diagnose` says everything is fine!
Try throwing your whole machine at it (`./main.py reduce ID`).
