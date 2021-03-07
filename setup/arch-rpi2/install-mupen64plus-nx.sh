#/bin/bash

#
#    This file is part of the Pi Entertainment System (PES).
#
#    PES provides an interactive GUI for games console emulators
#    and is designed to work on the Raspberry Pi.
#
#    Copyright (C) 2020 Neil Munday (neil@mundayweb.com)
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

header "Building N64 emulator - mupenplus64"

cd $buildDir
rmSourceDir "mupen64plus-libretro-nx"
run git clone https://github.com/libretro/mupen64plus-libretro-nx
checkDir mupen64plus-libretro-nx
cd mupen64plus-libretro-nx
run git checkout b494ebf2da202f67dbd88c3c915262bb58f1c6ba 
run make -j 2 WITH_DYNAREC=arm platform=rpi2 V=1
checkFile mupen64plus_next_libretro.so
run sudo cp -v mupen64plus_next_libretro.so $retroArchCoresDir
