#!/bin/bash

wget=/usr/bin/wget

URL_BASE="http://localhost"
WGET_OPTS='-q -O'

while [ "$1" != "" ]; do
    case $1 in
        -p | --path )           shift
                                pathname=$1
                                ;;
    esac
    shift
done


if [ ! -x "$wget" ]; then
  echo "ERROR: No wget." >&2
  exit 1
fi

# wget1 to download VERSION file (replaces WGET1)
if ! $wget $WGET_OPTS - $URL_BASE/$pathname; then
  echo "ERROR: can't wget" >&2
  exit 1
fi