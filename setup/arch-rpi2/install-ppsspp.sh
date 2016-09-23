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

setupDir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

if [ ! -e $setupDir/functions.sh ]; then
	echo "Error! $setupDir/functions does not exist!"
	exit 1
fi

source $setupDir/functions.sh

cd $buildDir

rmSourceDir "ppsspp"

header "Downloading Sony PSP emulator - ppsspp (standalone)"

installDir="$emulatorInstallDir/ppsspp"
run sudo mkdir -pv $installDir
#run git clone git://github.com/hrydgard/ppsspp
run git clone git://github.com/neilmunday/ppsspp
checkDir "ppsspp"
cd ppsspp
run git submodule init
run git submodule update
checkFile b.sh
export CMAKE_ARGS="-D SDL2_LIBRARY:PATH=/opt/sdl2/default/lib/libSDL2.so -D SDL2_INCLUDE_DIR:PATH=/opt/sdl2/default/include/SDL2 -D CMAKE_INSTALL_PREFIX:PATH=$installDir"
export CFLAGS="-ffast-math -march=armv7-a -mtune=cortex-a7 -mfpu=neon-vfpv4 -mfloat-abi=hard"
run ./b.sh
checkDir build
checkFile build/PPSSPPSDL
checkDir build/assets
run sudo cp -rv build/assets $installDir
run sudo cp -v build/PPSSPPSDL $installDir
