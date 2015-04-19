#!/bin/bash
0
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

VERSION="2.0.3"

sdl2Tar=$baseDir/src/SDL2-${VERSION}.tar.gz
sdl2Dir=$baseDir/build/SDL2-${VERSION}
prefix=/opt/sdl2/$VERSION

export CFLAGS="-mcpu=cortex-a7 -mfpu=neon-vfpv4 -mfloat-abi=hard"
export CXXFLAGS="-mcpu=cortex-a7 -mfpu=neon-vfpv4 -mfloat-abi=hard"

header "Downloading SDL2"

run cd $baseDir/src

if [ ! -e $sdl2Tar ]; then
	echo "Downloading SDL2-${VERSION}..."
	run wget http://www.libsdl.org/release/SDL2-${VERSION}.tar.gz
fi

checkFile $sdl2Tar

if [ -e $sdl2Dir ]; then
	echo "Removing previously used source..."
	run rm -rvf $sdl2Dir
fi
run cd $buildDir
run tar xvfz $sdl2Tar
checkDir $sdl2Dir
run cd $sdl2Dir

./configure --prefix=$prefix --host=arm-raspberry-linux-gnueabihf --disable-video-opengl --disable-video-x11 --disable-pulseaudio --disable-esd --enable-video-opengles --enable-libudev

run make 
run sudo make  install

run sudo rm -f /opt/sdl2/default
run sudo ln -s $prefix /opt/sdl2/default
