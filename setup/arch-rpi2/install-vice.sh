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

version=3.1

SDL2_CONFIG=/opt/sdl2/default/bin/sdl2-config
SDL_CFLAGS="-I/opt/sdl2/default/include -I/opt/vc/include -I/opt/vc/include/interface/vcos/pthreads -I/opt/vc/include/interface/vmcs_host/linux -D_REENTRANT -mcpu=cortex-a7 -mfpu=neon-vfpv4 -mfloat-abi=hard "
SDL_LDLIBS=`$SDL2_CONFIG --libs`

cd $buildDir

rmSourceDir "vice-${version}"

PREFIX=$emulatorInstallDir/vice
tarFile=$srcDir/vice-${version}.tar.gz

header "Building C64 emulator - vice"

if [ ! -e $tarFile ]; then
	run wget -O $tarFile https://sourceforge.net/projects/vice-emu/files/releases/vice-${version}.tar.gz/download
fi

run tar xvfz $tarFile
checkDir vice-${version}
cd vice-${version}

export CFLAGS="$SDL_CFLAGS"
export LDFLAGS="$SDL_LDLIBS"

#run ./configure --prefix=$PREFIX --enable-sdlui2 --disable-sdlui --enable-fullscreen --with-uithreads --with-sdlsound --without-oss --without-pulse
run ./configure --prefix=$PREFIX --enable-sdlui2 --disable-sdlui --enable-fullscreen 
run make -j 2 V=1 
run sudo make install

# now copy over data files
run sudo cp -vr data $PREFIX/
run sudo rm $PREFIX/data/Makefile*
