#!/bin/bash

#
#    This file is part of the Pi Entertainment System (PES).
#
#    PES provides an interactive GUI for games console emulators
#    and is designed to work on the Raspberry Pi.
#
#    Copyright (C) 2014 Neil Munday (neil@mundayweb.com)
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

source /home/pi/pes/setup/arch-rpi2/functions.sh

cd $buildDir

rmSourceDir "pocketsnes-libretro"

header "Downloading NES emulator - fceu-next"

rmSourceDir "fceu-next"
header "Downloading NES emulator"
run git clone git://github.com/libretro/fceu-next.git
checkDir "fceu-next"
cd fceu-next
checkDir "fceumm-code"
cd fceumm-code
export CFLAGS="-mcpu=cortex-a7 -mfpu=neon-vfpv4 -mfloat-abi=hard -O3"
export CXXFLAGS=$CFLAGS
run make -f Makefile.libretro -j
checkFile "fceumm_libretro.so"
run cp fceumm_libretro.so $retroArchCoresDir

