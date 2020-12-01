#!/bin/bash

# Install build dependencies
i="$(dpkg-checkbuilddeps 2>&1 | sed -e 's/.*dependencies: //;t;d')"
[ -n "$i" ] && sudo apt-get install $i

# Build package files
dpkg-buildpackage

