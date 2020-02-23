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
rmSourceDir "mupen64plus-libretro"
run git clone https://github.com/libretro/mupen64plus-libretro
checkDir mupen64plus-libretro
cd mupen64plus-libretro

RPI_FLAGS="-fgcse-after-reload -finline-functions -fipa-cp-clone -funswitch-loops -fpredictive-commoning -ftree-loop-distribute-patterns -ftree-vectorize -mfpu=vfp -mfloat-abi=hard -march=armv6zk -mtune=arm1176jzf-s -D__ARM_PCS_VFP"

CFLAGS="$RPI_FLAGS" CXXFLAGS="$RPI_FLAGS" LDFLAGS="$RPI_FLAGS" make WITH_DYNAREC=arm platform=rpi V=1
checkFile mupen64plus_libretro.so
run cp -v mupen64plus_libretro.so $retroArchCoresDir
