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

VERSION="2.0.10"

sdl2Tar=$srcDir/SDL2-${VERSION}.tar.gz
sdl2Dir=$buildDir/SDL2-${VERSION}
prefix=/opt/sdl2/$VERSION

#export CFLAGS="-mcpu=cortex-a7 -mfpu=neon-vfpv4 -mfloat-abi=hard"
#export CXXFLAGS="-mcpu=cortex-a7 -mfpu=neon-vfpv4 -mfloat-abi=hard"

header "Downloading SDL2"

run cd $srcDir

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

./configure --prefix=$prefix --enable-assertions=disabled --disable-video-opengl --disable-video-x11 --disable-pulseaudio --disable-esd --enable-video-opengles --enable-libudev --disable-video-rpi --enable-video-kmsdrm

run make -j 4
run sudo make install

run sudo rm -f /opt/sdl2/default
run sudo ln -s $prefix /opt/sdl2/default

header "Downloading SDL2 Image"
sdl2ImageVersion=2.0.5
sdl2ImageTar=$srcDir/SDL2_image-${sdl2ImageVersion}.tar.gz
sdl2ImageDir=$buildDir/SDL2_image-${sdl2ImageVersion}

run cd $srcDir

if [ ! -e $sdl2ImageTar ]; then
	echo "Downloading SDL2 Image ${sdl2ImageVersion}..."
	run wget https://www.libsdl.org/projects/SDL_image/release/SDL2_image-${sdl2ImageVersion}.tar.gz
fi

checkFile $sdl2ImageTar

if [ -e $sdl2ImageDir ]; then
	echo "Removing previously used source..."
	run rm -rfv $sdl2ImageDir
fi

run cd $buildDir
run tar xvfz $sdl2ImageTar
checkDir $sdl2ImageDir
run cd $sdl2ImageDir
./configure --prefix=$prefix --with-sdl-prefix=$prefix
run make -j 4
run sudo make install

header "Downloading SDL2 TTF"
sdl2TTFVersion=2.0.15
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

# apply patches
#patchDir="$rootDir/src/sdl2_ttf-patches"
#checkDir $patchDir
#for p in $patchDir/*.patch; do
#	echo "Applying patch ${p}..."
#	patch < $p
#done

./autogen.sh
./configure --prefix=$prefix --with-sdl-prefix=$prefix
run make -j 4
run sudo make install

header "Download SDL GFX"
sdl2GFXVersion=1.0.3
sdl2GFXTar=$srcDir/SDL2_gfx-${sdl2GFXVersion}.tar.gz
sdl2GFXDir=$buildDir/SDL2_gfx-${sdl2GFXVersion}

run cd $srcDir

if [ ! -e $sdl2GFXTar ]; then
	echo "Downloading SDL2 GFX ${sdl2GFXVersion}..."
	run wget http://www.ferzkopp.net/Software/SDL2_gfx/SDL2_gfx-${sdl2GFXVersion}.tar.gz
fi

checkFile $sdl2GFXTar

if [ -e $sdl2GFXDir ]; then
	echo "Removing previously used source..."
	run rm -rfv $sdl2GFXDir
fi

run cd $buildDir
run tar xvfz $sdl2GFXTar
checkDir $sdl2GFXDir
run cd $sdl2GFXDir
./configure --prefix=$prefix --with-sdl-prefix=$prefix --disable-mmx
run make -j 4
run sudo make install

header "Installing PySDL2"

run sudo pip2 install PySDL2
