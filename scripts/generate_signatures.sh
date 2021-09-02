#!/usr/bin/env bash

TEMP=$(getopt -o 'h,:m:,c:,o:' --long 'help,cc:,marker:,corpus:,args:,output:' -n "$0" -- "$@")

usage(){
    echo "Usage: $0 [-h|--help] --cc CCDIR [--args CC_ARGS] --marker|-m MARKER -c|--corpus INPUTDIR -o|--output OUTPUTDIR" 1>&2
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
		'--cc')
            CCDIR="$2"
			shift 2
			continue
		;;
        '--args')
            ARGS="$2"
            shift 2
            continue
        ;;
        '-m'|'--marker')
            MARKER="$2"
            shift 2
            continue
        ;;
        '-c'|'--corpus')
            CORPUSDIR="$2"
            shift 2
            continue
        ;;
        '-o'|'--output')
            OUTPUTDIR="$2"
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
            echo "Unknown argument $1" 1>&2
            usage
			exit 1
		;;
	esac
done


if [ -z "$CCDIR" ]; then
    echo 'No compiler directory was specified (passed with --cc)' 1>&2
    exit 1
fi
if [ -z "$MARKER" ]; then
    echo 'The marker was not specified (passed with -m or --marker)' 1>&2
    exit 1
fi
if [ -z "$CORPUSDIR" ]; then
    echo 'The input corpus directory was not specified (passed with -c or --corpus)' 1>&2
    exit 1
fi
if [ -z "$OUTPUTDIR" ]; then
    echo 'The output directory was not specified (passed with -o or --output)' 1>&2
    exit 1
fi

if [ $# -ne 0 ]; then
    echo 'Remaining arguments not processed:' 1>&2
    for arg; do
        echo "--> '$arg'" 1>&2
    done
    exit 1
fi


gen_sig(){
    file="$1"
    outpufile="$OUTPUTDIR"/$(basename "${file%.*}").signature
    args="--cc $CCDIR -m $MARKER -f $file" 
    if [ ! -z "$ARGS" ]
    then
        args+=" --args \"$ARGS\""
    fi
    eval "./generate_marker_signature_data.sh $args" > "$outpufile"
}

export OUTPUTDIR
export CCDIR
export MARKER
export ARGS
export -f gen_sig

mkdir -p "$OUTPUTDIR"


find "$CORPUSDIR" -name '*.c' | parallel --progress gen_sig
