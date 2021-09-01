#!/usr/bin/env bash

TEMP=$(getopt -o 'h,:m:,f:' --long 'help,cc:,marker:,file:,args:' -n "$0" -- "$@")
usage(){
    echo "Usage: $0 [-h|--help] --cc CCDIR [--args CC_ARGS] --marker|-m MARKER -f|--file FILE" 1>&2
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
        '-f'|'--file')
            FILE="$2"
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


if [ -z "$CCDIR" ]; then
    echo 'No compiler directory was specified (passed with --cc)' 1>&2
    exit 1
fi
if [ -z "$MARKER" ]; then
    echo 'The marker was not specified (passed with -m or --marker)' 1>&2
    exit 1
fi
if [ -z "$FILE" ]; then
    echo 'The input file was not specified (passed with -f or --file)' 1>&2
    exit 1
fi

if [ $# -ne 0 ]; then
    echo 'Remaining arguments not processed:' 1>&2
    for arg; do
        echo "--> '$arg'" 1>&2
    done
    exit 1
fi

while read cc; do
    cc_args+=" --cc $cc"
done <<< "$(find "$CCDIR" -name 'clang' -path '*bin*')"

while read cc; do
    cc_args+=" --cc $cc"
done <<< "$(find "$CCDIR" -name 'gcc' -path '*bin*')"


cmd="./find_marker_status.sh -f $FILE $cc_args -m $MARKER -O1 -O2 -O3 -Os --args \"$ARGS\""

eval "$cmd"
