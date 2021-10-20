#!/bin/sh
OLD=libsanitizer/sanitizer_common/sanitizer_platform_limits_posix.cc
NEW=libsanitizer/sanitizer_common/sanitizer_platform_limits_posix.cpp

INPLACE="-i"
if [ "$1" = "--check" ]; then
    INPLACE=""
fi


if [ -f "$OLD" ]; then
    #https://stackoverflow.com/a/15966279
    sed '/CHECK_SIZE_AND_OFFSET(ipc_perm, mode)/{s//\/\/CHECK_SIZE_AND_OFFSET(ipc_perm, mode)/;h};${x;/./{x;q0};x;q1}' \
        $INPLACE $OLD > /dev/null
elif [ -f "$NEW" ]; then
    sed '/CHECK_SIZE_AND_OFFSET(ipc_perm, mode)/{s//\/\/CHECK_SIZE_AND_OFFSET(ipc_perm, mode)/;h};${x;/./{x;q0};x;q1}' \
        $INPLACE $NEW > /dev/null
else
    exit 1
fi
