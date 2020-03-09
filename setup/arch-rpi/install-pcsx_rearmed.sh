#!/bin/bash

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

cd $buildDir

rmSourceDir "pcsx_rearmed"
header "Downloading PSX emulator - pcsx_rearmed"
run git clone https://github.com/libretro/pcsx_rearmed
checkDir "pcsx_rearmed"
cd pcsx_rearmed
git checkout 20a09b8ce3c86e1ebc97b260e32ef78abd508844
export CFLAGS="-mfpu=vfp -mfloat-abi=hard -march=armv6zk -mtune=arm1176jzf-s"
export CXXFLAGS=$CFLAGS
run make -f Makefile.libretro HAVE_NEON=0 BUILTIN_GPU=peops ARCH=arm USE_DYNAREC=1
run sudo cp pcsx_rearmed_libretro.so $retroArchCoresDir/
