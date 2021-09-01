#!/usr/bin/env bash

TEMP=$(getopt -o 'h,p:,b:' --long 'help,prefix:,build' -n "$0" -- "$@")
usage(){
    echo "Usage: $0 [-h|--help] -b|--build BUILD_DIR  -p|--prefix DIR" 1>&2
}

if [ $? -ne 0 ]; then
	echo 'Terminating...' >&2
    usage
	exit 1
fi

eval set -- "$TEMP"
unset TEMP

while true; do
	case "$1" in
        '-p'|'--prefix')
            PREFIX="$2"
            shift 2
            continue
        ;;
        '-b'|'--build')
            BUILDDIR="$2"
            shift 2
            continue
        ;;
		'--')
			shift
			break
		;;
        '-h'|'--help')
            usage
			exit 0
        ;;
		*)
            usage
			exit 1
		;;
	esac
done

if [ -z "$PREFIX" ]; then
    echo 'The installation prefix was not specified (passed with -p or --prefix)'
    exit 1
fi

if [ -z "$BUILDDIR" ]; then
    echo 'The build directory was not specified (passed with -b or --build)'
    exit 1
fi

if [ ! -d "$BUILDDIR" ]; then
    echo "The specified build directory ($BUILDDIR) does not exist"
    exit 1
fi

if [ "$PREFIX" == "$BUILDDIR" ]; then
    echo "The prefix ($PREFIX) and build ($BUILDDIR) directories must be different"
    exit 1
fi
 

declare -A llvm_versions
llvm_versions[main]=llvm-trunk
llvm_versions[llvmorg-12.0.1]=llvm-12.0.1
llvm_versions[llvmorg-12.0.0]=llvm-12.0.0
llvm_versions[llvmorg-11.1.0]=llvm-11.1.0
llvm_versions[llvmorg-11.0.1]=llvm-11.0.1
llvm_versions[llvmorg-11.0.0]=llvm-11.0.0
llvm_versions[llvmorg-11.0.0]=llvm-11.0.0
llvm_versions[llvmorg-10.0.1]=llvm-10.0.1
llvm_versions[llvmorg-10.0.0]=llvm-10.0.0

cd "$BUILDDIR"
rm -rf llvm-project
git clone -n https://github.com/llvm/llvm-project.git
pushd llvm-project

for version in "${!llvm_versions[@]}"
do
    name="${llvm_versions["$version"]}"
    prefix="$PREFIX"/"$name"
    if [ -d "$prefix"  ]; then
        continue
    fi
    git worktree add ../"$name" "$version" -f
    pushd ../"$name" 
    mkdir build
    cd build
    CC=clang CXX=clang++ cmake -G Ninja -DCMAKE_BUILD_TYPE=Release -DLLVM_ENABLE_PROJECTS="clang"\
        -DLLVM_INCLUDE_BENCHMARKS=OFF -DLLVM_INCLUDE_TESTS=OFF -DLLVM_USE_NEWPM=ON\
        -DLLVM_TARGETS_TO_BUILD=X86 -DCMAKE_INSTALL_PREFIX="$prefix" ../llvm
    ninja install
    popd
    rm -rf ../"$name"
done
popd
rm -rf llvm-project

declare -A gcc_versions
gcc_versions[master]=gcc-trunk
gcc_versions[releases/gcc-11.2.0]=gcc-11.2.0
gcc_versions[releases/gcc-11.1.0]=gcc-11.1.0
gcc_versions[releases/gcc-10.3.0]=gcc-10.3.0
gcc_versions[releases/gcc-10.2.0]=gcc-10.2.0
gcc_versions[releases/gcc-10.1.0]=gcc-10.1.0
gcc_versions[releases/gcc-9.4.0]=gcc-9.4.0
gcc_versions[releases/gcc-9.3.0]=gcc-9.3.0
gcc_versions[releases/gcc-9.2.0]=gcc-9.2.0
gcc_versions[releases/gcc-9.1.0]=gcc-9.1.0
gcc_versions[releases/gcc-8.5.0]=gcc-8.5.0
gcc_versions[releases/gcc-8.4.0]=gcc-8.4.0

cd "$BUILDDIR"
rm -rf gcc
git clone -n git://gcc.gnu.org/git/gcc.git
pushd gcc

for version in "${!gcc_versions[@]}"
do
    name="${gcc_versions["$version"]}"
    prefix="$PREFIX"/"$name"
    if [ -d "$prefix"  ]; then
        continue
    fi
    git worktree add ../"$name" "$version" -f
    pushd ../"$name" 
    ./contrib/download_prerequisites
    mkdir build
    cd build
    ../configure --disable-multilib --disable-bootstrap --enable-languages=c,c++ --prefix="$prefix"
    make -j
    make install
    popd
    rm -rf ../"$name"
done
popd
rm -rf gcc
