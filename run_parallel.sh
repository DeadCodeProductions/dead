#!/bin/sh

function run_gcc(){
    ./main.py -ll info --cores $CORES_PER_JOB run \
        --no-parallel-generation\
        -t gcc trunk 1 2 3 s\
        -ac gcc releases/gcc-11.2.0\
            gcc releases/gcc-10.3.0\
            gcc releases/gcc-9.4.0\
            gcc releases/gcc-8.5.0\
            gcc releases/gcc-7.5.0\
        -acdol 1 2 3 s\
        --no-reducer &>> split_$1.log
}

function run_llvm(){

    # Don't compile LLVM with less than 8 cores.
    if [[ $CORES_PER_JOB -lt 8 ]]; then
        CORES_PER_JOB=8
    fi
    ./main.py -ll info --cores $CORES_PER_JOB run \
        --no-parallel-generation\
        -t llvm trunk 1 2 3 s z\
        -ac llvm llvmorg-13.0.0\
            llvm llvmorg-12.0.1\
            llvm llvmorg-11.1.0\
            llvm llvmorg-10.0.1\
            llvm llvmorg-7.1.0\
            llvm llvmorg-6.0.1\
            llvm llvmorg-5.0.2\
            llvm llvmorg-4.0.1\
        -acdol 1 2 3 s z\
        --no-reducer &>> split_$1.log
}

export -f run_llvm
export -f run_gcc

PROJECT=$1
TOTAL_CORES=$2
JOBS=$3
export CORES_PER_JOB=$(expr $TOTAL_CORES / $JOBS)

if [ $PROJECT = "llvm" ]; then
    RUN_CMD='run_llvm "{}"'
elif [ $PROJECT = "clang" ]; then
    RUN_CMD='run_llvm "{}"'
else
    RUN_CMD='run_gcc "{}"'
fi

seq $JOBS | xargs --max-procs=$JOBS -I {} sh -c $RUN_CMD
