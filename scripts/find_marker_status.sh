#!/usr/bin/env bash

TEMP=$(getopt -o 'h,m:,f:,O:' --long 'help,cc:,marker:,file:,args:' -n "$0" -- "$@")
usage(){
    echo "Usage: $0 [-h|--help] [--cc CC]+ [--args CC_ARGS] [-O OPT_LEVEL]+ --marker|-m MARKER -f|--file FILE" 1>&2
}

if [ $? -ne 0 ]; then
	echo 'Terminating...' >&2
    usage
	exit 1
fi

eval set -- "$TEMP"
unset TEMP

declare -a OPT_LEVELS
declare -a CCS

while true; do
	case "$1" in
		'--cc')
            CCS+=("$2")
			shift 2
			continue
		;;
        '-O')
            OPT_LEVELS+=("$2")
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


if [ ${#CCS[*]} -eq 0 ]; then
    echo 'No compiler was not specified (passed with --cc)' 1>&2
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
if [ ${#OPT_LEVELS[*]} -eq 0 ]; then
    echo 'No optimization level(s) specified (use -O)' 1>&2
    exit 1
fi

if [ $# -ne 0 ]; then
    echo 'Remaining arguments not processed:' 1>&2
    for arg; do
        echo "--> '$arg'" 1>&2
    done
    exit 1
fi

readonly TMPDIRECTORY=$(mktemp -d)
trap '{ rm -rf -- "$TMPDIRECTORY"; }' EXIT
readonly TMPAsm=$(mktemp --tmpdir="$TMPDIRECTORY")
readonly TMPAlive=$(mktemp --tmpdir="$TMPDIRECTORY")
readonly TMPDead=$(mktemp --tmpdir="$TMPDIRECTORY")
readonly TMPJson=$(mktemp --tmpdir="$TMPDIRECTORY")

echo "{\"CCs\": [], \"file\":\"$FILE\"}" | jq . > "$TMPJson"
for CC in "${CCS[@]}"; do
    jq ".CCs += [{\"CC\": \"$CC\", \"opt_level\":[]}]" "$TMPJson" | sponge "$TMPJson" 
    for opt in "${OPT_LEVELS[@]}"; do
        eval $CC -S -w -O"$opt" "$ARGS" "$FILE" -o "$TMPAsm"
        grep --color=never "$MARKER"  "$TMPAsm" | grep -E "call|jmp" | sort -u | awk '{print $2}' | cut -d'@' -f 1| sort -u > "$TMPAlive"
        diff --unchanged-line-format="" --new-line-format="" <(grep --color=never "void $MARKER" "$FILE" | cut -d ' ' -f 2 | cut -d '(' -f 1 | sort -u) "$TMPAlive" > "$TMPDead"
        awk '{ printf "\"%s\"\n", $0}' $TMPAlive | paste -s -d ',' - | sponge "$TMPAlive"
        awk '{ printf "\"%s\"\n", $0}' $TMPDead | paste -s -d ',' - | sponge "$TMPDead"
        jq ".CCs[-1].opt_level += [{\"level\":\"$opt\", \"alive_markers\":[$(cat $TMPAlive)], \"dead_markers\":[$(cat $TMPDead)]}]" "$TMPJson" | sponge "$TMPJson"  
    done
done

jq . "$TMPJson"
