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

rmSourceDir "ppsspp"

header "Downloading Sony PSP emulator - ppsspp (standalone)"

installDir="$emulatorInstallDir/ppsspp"
run sudo mkdir -pv $installDir
run git clone git://github.com/hrydgard/ppsspp
checkDir "ppsspp"
cd ppsspp
run git submodule init
run git submodule update
# re-build ffmpeg libs
cd ffmpeg
patchDir="$rootDir/src/ppsspp-patches/ffmpeg"
checkDir $patchDir
for p in $patchDir/*.patch; do
	echo "Applying patch ${p}..."
	patch < $p
done
run ./linux_rpi.sh
cd ..
# apply SDL patches
cd SDL
patchDir="$rootDir/src/ppsspp-patches/SDL"
checkDir $patchDir
for p in $patchDir/*.patch; do
	echo "Applying patch ${p}..."
	patch < $p
done
cd ..
run mkdir build
cd build
cmake -D SDL2_LIBRARY:PATH=/opt/sdl2/default/lib/libSDL2.so \
-D SDL2_INCLUDE_DIR:PATH=/opt/sdl2/default/include/SDL2 \
-D CMAKE_INSTALL_PREFIX:PATH=$installDir \
-D CMAKE_TOOLCHAIN_FILE=../cmake/Toolchains/raspberry.armv7.cmake \
-D USING_X11_VULKAN=0 \
..
make -j 4
cd ..
checkFile build/PPSSPPSDL
checkDir build/assets
run sudo cp -rv build/assets $installDir
run sudo cp -v build/PPSSPPSDL $installDir
