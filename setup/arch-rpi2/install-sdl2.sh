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

VERSION="2.0.4"

sdl2Tar=$srcDir/SDL2-${VERSION}.tar.gz
sdl2Dir=$buildDir/SDL2-${VERSION}
prefix=/opt/sdl2/$VERSION

export CFLAGS="-mcpu=cortex-a7 -mfpu=neon-vfpv4 -mfloat-abi=hard"
export CXXFLAGS="-mcpu=cortex-a7 -mfpu=neon-vfpv4 -mfloat-abi=hard"

# header "Downloading SDL2"
# 
# run cd $srcDir
# 
# if [ ! -e $sdl2Tar ]; then
# 	echo "Downloading SDL2-${VERSION}..."
# 	run wget http://www.libsdl.org/release/SDL2-${VERSION}.tar.gz
# fi
# 
# checkFile $sdl2Tar
# 
# if [ -e $sdl2Dir ]; then
# 	echo "Removing previously used source..."
# 	run rm -rvf $sdl2Dir
# fi
# run cd $buildDir
# run tar xvfz $sdl2Tar
# checkDir $sdl2Dir
# run cd $sdl2Dir
# 
# ./configure --prefix=$prefix --host=arm-raspberry-linux-gnueabihf --disable-video-opengl --disable-video-x11 --disable-pulseaudio --disable-esd --enable-video-opengles --enable-libudev
# 
# run make 
# run sudo make -j 2 install
# 
# run sudo rm -f /opt/sdl2/default
# run sudo ln -s $prefix /opt/sdl2/default

# SDL image
# header "Downloading SDL2 Image"
# sdl2ImageVersion=2.0.1
# sdl2ImageTar=$srcDir/SDL2_image-${sdl2ImageVersion}.tar.gz
# sdl2ImageDir=$buildDir/SDL2_image-${sdl2ImageVersion}
# 
# run cd $srcDir
# 
# if [ ! -e $sdl2ImageTar ]; then
# 	echo "Downloading SDL2 Image ${sdl2ImageVersion}..."
# 	run wget https://www.libsdl.org/projects/SDL_image/release/SDL2_image-${sdl2ImageVersion}.tar.gz
# fi
# 
# checkFile $sdl2ImageTar
# 
# if [ -e $sdl2ImageDir ]; then
# 	echo "Removing previously used source..."
# 	run rm -rfv $sdl2ImageDir
# fi
# 
# run cd $buildDir
# run tar xvfz $sdl2ImageTar
# checkDir $sdl2ImageDir
# run cd $sdl2ImageDir
# ./configure --prefix=$prefix --host=arm-raspberry-linux-gnueabihf --with-sdl-prefix=$prefix
# run make -j 2
# run sudo make install

# SDL TTF
header "Downloading SDL2 TTF"
sdl2TTFVersion=2.0.14
sdl2TTFTar=$srcDir/SDL2_ttf-${sdl2TTFVersion}.tar.gz
sdl2TTFDir=$buildDir/SDL2_ttf-${sdl2TTFVersion}

run cd $srcDir

if [ ! -e $sdl2TTFTar ]; then
	echo "Downloading SDL2 TTF ${sdl2TTFVersion}..."
	run wget https://www.libsdl.org/projects/SDL_ttf/release/SDL2_ttf-${sdl2TTFVersion}.tar.gz
fi

checkFile $sdl2TTFTar

if [ -e $sdl2TTFDir ]; then
	echo "Removing previously used source..."
	run rm -rfv $sdl2TTFDir
fi

run cd $buildDir
run tar xvfz $sdl2TTFTar
checkDir $sdl2TTFDir
run cd $sdl2TTFDir
./configure --prefix=$prefix --host=arm-raspberry-linux-gnueabihf --with-sdl-prefix=$prefix
run make -j 2
run sudo make install
