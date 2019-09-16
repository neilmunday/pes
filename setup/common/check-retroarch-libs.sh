#!/bin/bash

#
#    This file is part of the Pi Entertainment System (PES).
#
#    PES provides an interactive GUI for games console emulators
#    and is designed to work on the Raspberry Pi.
#
#    Copyright (C) 2019 Neil Munday (neil@mundayweb.com)
#
#    PES is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    PES is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with PES.  If not, see <http://www.gnu.org/licenses/>.
#

functions=`realpath $( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )/../common/functions.sh`
source $functions || exit 1

cores="
genesis_plus_gx_libretro.so
mednafen_pce_fast_libretro.so
bluemsx_libretro.so
fbalpha_libretro.so
fceumm_libretro.so
fuse_libretro.so
gambatte_libretro.so
gpsp_libretro.so
mame2000_libretro.so
mame2003_libretro.so
mupen64plus_libretro.so
snes9x2002_libretro.so
snes9x2010_libretro.so
stella_libretro.so
"

for f in $cores; do
        path="$retroArchCoresDir/$f"
        echo -n "checking: $path: "
        if [ -e $path ]; then
                echo "OK"
        else
                echo "MISSING!"
        fi
done
