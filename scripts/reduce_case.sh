#!/usr/bin/env bash

set -e

TEMP=$(getopt -o 'h,m:,f:,o:,j:' --long 'help,cc-bad:,cc-badO:,cc-good:,cc-goodO:,marker:,mm:,file:,flags:,output:' -n "$0" -- "$@")
usage(){
    echo "Usage: $0 [-h|--help] --cc-bad CC --cc-badO OPT_LEVEL --cc-good CC --cc-goodO OPT_LEVEL --flags CC_FLAGS  --marker|-m MARKER -mm MISSED_MARKER -j N_CREDUCE_JOBS -f|--file FILE -o|--output OUTPUT_DIR" 1>&2
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
		'--cc-good')
            CCGOOD="$2"
			shift 2
			continue
		;;
		'--cc-bad')
            CCBAD="$2"
			shift 2
			continue
		;;
        '--cc-goodO')
            OPT_LEVEL_GOOD="$2"
            shift 2
            continue
		;;
        '--cc-badO')
            OPT_LEVEL_BAD="$2"
            shift 2
            continue
		;;
        '-j')
            J="$2"
            shift 2
            continue
		;;
        '--flags')
            FLAGS="$2"
            shift 2
            continue
        ;;
        '-m'|'--marker')
            MARKER="$2"
            shift 2
            continue
        ;;
        '--mm')
            MMARKER="$2"
            shift 2
            continue
        ;;
        '-f'|'--file')
            FILE="$2"
            shift 2
            continue
        ;;
        '-o'|'--output')
            OUTPUT_DIR="$2"
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


if [ -z "$CCGOOD" ]; then
    echo 'No good compiler was not specified (passed with --cc-good)' 1>&2
    exit 1
fi
if [ -z "$CCBAD" ]; then
    echo 'No bad compiler was not specified (passed with --cc-bad)' 1>&2
    exit 1
fi
if [ -z "$MARKER" ]; then
    echo 'The marker was not specified (passed with -m or --marker)' 1>&2
    exit 1
fi
if [ -z "$MMARKER" ]; then
    echo 'The missed marker was not specified (passed with --mm)' 1>&2
    exit 1
fi

if [ -z "$FILE" ]; then
    echo 'The input file was not specified (passed with -f or --file)' 1>&2
    exit 1
fi
if [ -z "$OPT_LEVEL_GOOD" ]; then
    echo 'No optimization level for the good compiler specified (use --good-ccO)' 1>&2
    exit 1
fi
if [ -z "$OPT_LEVEL_BAD" ]; then
    echo 'No optimization level for the bad compiler specified (use --bad-ccO)' 1>&2
    exit 1
fi
if [ -z "$OUTPUT_DIR" ]; then
    echo 'No output directory specified (use -o or --output)' 1>&2
    exit 1
fi

if [ $# -ne 0 ]; then
    echo 'Remaining arguments not processed:' 1>&2
    for arg; do
        echo "--> '$arg'" 1>&2
    done
    exit 1
fi


if [ -z "$J" ]; then
    J=$(grep -c '^processor' /proc/cpuinfo)
fi


if [ -d "$OUTPUT_DIR" ]; then
    echo "$OUTPUT_DIR already exists"
    exit 1
fi

SCRIPTPATH="$( cd -- "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P )"

mkdir -p "$OUTPUT_DIR" 

cp "$FILE" "$OUTPUT_DIR"

reduce_script="$OUTPUT_DIR"/$(basename "${FILE%.*}")_"$MMARKER".sh


echo "#/usr/bin/env bash" >> "$reduce_script"
echo "$SCRIPTPATH/dce_reduction_check.py $CCBAD --cc-bad-flags=\"-O$OPT_LEVEL_BAD\"" \
     "$CCGOOD --cc-good-flags=\"-O$OPT_LEVEL_GOOD\"  $(basename $FILE) $MMARKER" \
     " --common-flags=\"$FLAGS\" -m $MARKER " >> "$reduce_script"

chmod +x "$reduce_script"

cd "$OUTPUT_DIR"
creduce $(basename "$reduce_script") $(basename "$FILE") --n "$J"
