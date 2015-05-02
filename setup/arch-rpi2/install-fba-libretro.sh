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
rmSourceDir "libretro-fba"

header "Downloading Final Burn Alpha emulator"

run git clone git://github.com/libretro/libretro-fba
checkDir libretro-fba
cd libretro-fba
checkFile makefile.libretro
run make -f makefile.libretro platform=rpi2 profile=performance
checkFile fb_alpha_libretro.so
run cp fb_alpha_libretro.so $retroArchCoresDir
