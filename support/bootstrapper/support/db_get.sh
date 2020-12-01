#!/bin/sh -e

# Source debconf library.
. /usr/share/debconf/confmodule

db_get stabile/$1
echo $RET
