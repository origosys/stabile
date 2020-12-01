#! /bin/bash
find /var/www/orellana.org/stabile -name '._*' -print | xargs -t rm
# Handle spaces
# find /Volumes/Your_NetworkVolume -name '._*' -print0 | xargs -t0 rm
