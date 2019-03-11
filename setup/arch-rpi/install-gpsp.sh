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

cd $buildDir

rmSourceDir "gpsp"
header "Downloading GameBoy Advance emulator - gpsp"

run git clone https://github.com/libretro/gpsp
checkDir gpsp
cd gpsp

export CFLAGS="-mfpu=vfp -mfloat-abi=hard -march=armv6zk -mtune=arm1176jzf-s"
export CXXFLAGS=$CFLAGS

run make
checkFile gpsp_libretro.so
run sudo cp -v gpsp_libretro.so $retroArchCoresDir
