#!/usr/bin/env bash

TEMP=$(getopt -o 'h' --long 'help' -n "$0" -- "$@")

usage(){
    echo "Usage: $0 [-h|--help] SIGDIR" 1>&2
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

if [ ! -d "$1" ]; then
    echo "$1 is not a directory" 1>&2
fi


find_missed(){
    file="$1"
    ./process_signature.py --cc gcc --across-versions --across-levels --across-compilers "$file" 
    ./process_signature.py --cc clang --across-versions --across-levels --across-compilers "$file" 
}

export -f find_missed

find "$1" -name '*.signature' | parallel --progress find_missed
