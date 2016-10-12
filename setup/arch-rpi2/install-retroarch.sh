#!/bin/bash

#
#    This file is part of the Pi Entertainment System (PES).
#
#    PES provides an interactive GUI for games console emulators
#    and is designed to work on the Raspberry Pi.
#
#    Copyright (C) 2016 Neil Munday (neil@mundayweb.com)
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

retroarchDir=RetroArch

rmSourceDir $retroarchDir

run git clone  git://github.com/libretro/RetroArch.git
checkDir $retroarchDir

header "Building RetroArch"

cd $retroarchDir

run sudo mkdir -p $retroArchCoresDir
run sudo mkdir -p $retroArchConfigDir

export CFLAGS="-mcpu=cortex-a7 -mfpu=neon-vfpv4 -mfloat-abi=hard -O3"
export CXXFLAGS=$CFLAGS
#export PKG_CONFIG_PATH=/opt/sdl2/default/lib/pkgconfig

run ./configure --prefix="$retroArchInstallDir" --enable-udev --disable-ffmpeg --enable-netplay --disable-pulse --disable-x11 --enable-sdl --enable-neon --enable-floathard
run make GLOBAL_CONFIG_DIR="$retroArchConfigDir" V=1
run sudo make GLOBAL_CONFIG_DIR="$retroArchConfigDir" V=1 install

