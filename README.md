# Finding Missed Optimizations through the Lens of Dead Code Elimination

*NOTE: This is 'Work in Progress'. Expect to encounter rough edges, especially with respect to the UX*

## Installation

### Prerequisites
The following programs must be installed
- `gcc`
- `clang`
- `csmith`
- `creduce`
- `cmake`
- `ccomp` (CompCert)
- `llvm 13.0.0` (for the include files)
- `compiler-rt` (for the sanitization libraries. It's also part of LLVM)

We are running on Arch Linux and have not tested any other distribution.

### Setup
Install the prerequisites.
Then run 
```
./init.py
```
`init.py` will:
- create a config file located at `~/.config/dead/config.json`
- Compile tooling to instrument and check programs: `dcei`, `static-annotator`, `ccc`
- Clone repositories of `gcc` and `llvm` into the local directory
- Create the `compiler_cache` directory
- Check if it can find the programs and paths required in the prerequisite-section and complain if not.

### Run
First run will take a long time due to having to compile the compilers.
This will gradually become faster as when the compiler cache is populated.
```
# Do all the things with all threads for LLVM, 
# put it into ./llvm_cases and tell me about it
./bisector.py -d ./llvm_cases\
              --generate\ # Find new cases using generator.py, checker.py etc.
              --targets llvm trunk 1 2 3 s z \ # Target compiler + optimization levels
              -ac llvm llvmorg-13.0.0\ # Additional/Attacking compilers
                  llvm llvmorg-12.0.1\
                  llvm llvmorg-11.1.0\
                  llvm llvmorg-10.0.1\
              -acdol 1 2 3 s z \ # Opt levels for additional/attacking compilers
              --log-level info # Tell what is happening
              
              # Other helpful options
              # --no-reducer     # Don't reduce case
              # --amount AMOUNT  # Stop after finding AMOUNT cases
              # --cores CORES    # Only use CORES threads

# No comment version to copy paste
./bisector.py -d ./llvm_cases\
              --generate\
              --targets llvm trunk 1 2 3 s z \
              -ac llvm llvmorg-13.0.0\
                  llvm llvmorg-12.0.1\
                  llvm llvmorg-11.1.0\
                  llvm llvmorg-10.0.1\
              -acdol 1 2 3 s z \
              --log-level info

# Same thing for gcc 
./bisector.py -d ./gcc_cases\
              --generate\
              --targets gcc trunk 1 2 3 s\
              -ac gcc releases/gcc-11.2.0\
                  gcc releases/gcc-10.3.0\
                  gcc releases/gcc-9.4.0\
                  gcc releases/gcc-8.5.0\
              -acdol 1 2 3 s\
              --log-level info
```

## File format
The cases will be saved in a `.tar`. You may not have to extract it to view its contents 
Try opening it in your favourite editor.

Contents:
- `code.c`: The original code found by the generator which exhibits a difference of the compiler.
- `marker.txt`: Which function is not elimiated in one compiler but the other.
- `interesting_settings.json`: Contains which compilers elimiate the marker and which not.
- `scenario.json`: What the settings were in which the case was found.
- `reduced_code_X.c`: Reduced code from `code.c`. Does not exist if case was not reduced.
- `bisection_X.c`: Where the case bisects to. Does not exist if case was not bisected.


## Overview of important files
- `bisector.py`: Bisects a given interesting case.
- `builder.py`: Builds the compiler.
- `checker.py`: Checks if a given case is interesting.
- `generator.py`: Finds new interesting cases.
- `patcher.py`: Automatically finds the region in the history where a patch needs to be applied.
- `reducer.py`: Reduce the code of a given.

## FAQ
### I want to do XYZ. How?
Maybe there's already an option for it. Consult the program with `--help` for all the options.

### Why don't I see anything?
Are you running with `-ll info`?

### The program got a commit that doesn't exist!
If you are checking things manually: Are you sure you are looking in the right repository?

If you are processing a case and `git` throws an exception, try pulling `llvm-project` and `gcc` so you are sure to have all the commits.

### Why does this case fail?
Try checking it with `./debugtool.py -di -f $CASE`. If it says everything is ok but it is not, you have encountered a bug. Please drop us an e-mail.

### What is `WARNING:root:Reminder: trunk/master/main/hauptzweig/principale is stale` supposed to mean?
It means that the `llvm-project` and `gcc` repo aren't updated/pulled automatically i.e. even if you write `-t llvm trunk`, you don't get upstream trunk but your local one.
