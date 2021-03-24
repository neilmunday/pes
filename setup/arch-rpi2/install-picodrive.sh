#!/bin/bash

#
#    This file is part of the Pi Entertainment System (PES).
#
#    PES provides an interactive GUI for games console emulators
#    and is designed to work on the Raspberry Pi.
#
#    Copyright (C) 2014-2014-2021 Neil Munday (neil@mundayweb.com)
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

header "Downloading MegaDrive emulator - PicoDrive"

rmSourceDir "picodrive"
run git clone https://github.com/libretro/picodrive.git
checkDir "picodrive"
cd picodrive 
run git submodule init
run git submodule update
run ./configure
export CFLAGS="-marm -mword-relocations -fomit-frame-pointer -ffast-math -mcpu=cortex-a7 -mfpu=neon-vfpv4 -mfloat-abi=hard -O3"
export CXXFLAGS=$CFLAGS
make -f Makefile.libretro platform=armv ARM_ASM=1 use_fame=0 use_cyclone=1 use_sh2drc=1 use_svpdrc=1 use_cz80=1 use_drz80=0
run sudo cp picodrive_libretro.so $retroArchCoresDir

