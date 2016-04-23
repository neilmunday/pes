#!/bin/bash

#
#    This file is part of the Pi Entertainment System (PES).
#
#    PES provides an interactive GUI for games console emulators
#    and is designed to work on the Raspberry Pi.
#
#    Copyright (C) 2015 Neil Munday (neil@mundayweb.com)
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

PREFIX=$emulatorInstallDir/mupen64plus
SDL2_CONFIG=`which sdl2-config`

if [ ! -x $SDL2_CONFIG ]; then
	echo "Error! sdl2-config could not be found!"
fi

header "Building N64 emulator - mupenplus64"

checkFile $SDL2_CONFIG

#
# core - use my fork for now as this adds hot key support
#

cd $buildDir

component=mupen64plus-core

rmSourceDir $component

header "Downloading $component"
run git clone https://github.com/neilmunday/$component
checkDir $component
cd $component
run git remote add upstream https://github.com/mupen64plus/$component
run git checkout ric_dev

set APIDIR=`pwd`/src/api
SDL_CFLAGS=`$SDL2_CONFIG --cflags`
SDL_LDLIBS=`$SDL2_CONFIG --libs`

checkDir projects/unix
cd projects/unix
run sudo make PREFIX=$PREFIX SDL_CFLAGS="$SDL_CFLAGS" SDL_LDLIBS="$SDL_LDLIBS" V=1 -j install

# add extra privileges to generated binary for task scheduling
sudo setcap cap_sys_nice+ep $PREFIX/bin/mupen64plus

unset APIDIR

export CFLAGS="-O3"
export CXXFLAGS=$CFLAGS

#
# ui-console
#

cd $buildDir

component=mupen64plus-ui-console

if [ ! -e $component ]; then
	header "Downloading $component"
	run git clone https://github.com/mupen64plus/$component
	checkDir $component
	cd $component
else
	header "Updating $component"
	cd $component
	run git pull origin master
fi

checkDir projects/unix
cd projects/unix
run make clean
run sudo make PREFIX=$PREFIX SDL_CFLAGS="$SDL_CFLAGS" SDL_LDLIBS="$SDL_LDLIBS" V=1 -j install

#
# audio-omx
#

cd $buildDir

component=mupen64plus-audio-sdl

if [ ! -e $component ]; then
	header "Downloading $component"
	run git clone https://github.com/mupen64plus/$component
	checkDir $component
	cd $component
else
	header "Updating $component"
	cd $component
	run git pull origin master
fi

checkDir projects/unix
cd projects/unix
run make clean
run sudo make PREFIX=$PREFIX V=1 VC=1 -j install

#
# input-sdl
#

cd $buildDir

component=mupen64plus-input-sdl

if [ ! -e $component ]; then
	header "Downloading $component"
	run git clone https://github.com/mupen64plus/$component
	checkDir $component
	cd $component
else
	header "Updating $component"
	cd $component
	run git pull origin master
fi

checkDir projects/unix
cd projects/unix
run make clean
run sudo make PREFIX=$PREFIX SDL_CFLAGS="$SDL_CFLAGS" SDL_LDLIBS="$SDL_LDLIBS" V=1 -j install

#
# rsp-hle
#

cd $buildDir

component=mupen64plus-rsp-hle

if [ ! -e $component ]; then
	header "Downloading $component"
	run git clone https://github.com/ricrpi/$component
	checkDir $component
	cd $component
	run git remote add upstream https://github.com/mupen64plus/$component
	run git checkout master
else
	header "Updating $component"
	cd $component
	run git pull origin master
fi

checkDir projects/unix
cd projects/unix
run make clean
run sudo make PREFIX=$PREFIX V=1 -j install

#
# video-gles2rice
#

cd $buildDir

component=mupen64plus-video-rice

if [ ! -e $component ]; then
	header "Downloading $component"
	run git clone https://github.com/mupen64plus/$component
	checkDir $component
	cd $component
else
	header "Updating $component"
	cd $component
	run git pull origin master
fi

checkDir projects/unix
cd projects/unix
run make clean
run sudo make PREFIX=$PREFIX SDL_CFLAGS="$SDL_CFLAGS" SDL_LDLIBS="$SDL_LDLIBS" V=1 install

#
# launcher script
#

launchScript="$PREFIX/bin/mupen64plus-launcher.sh"

run echo "#!/bin/bash" > $launchScript
run echo "$PREFIX/bin/mupen64plus --corelib $PREFIX/lib/libmupen64plus.so.2 --datadir $PREFIX/share/mupen64plus --plugindir $PREFIX/lib/mupen64plus --configdir \$HOME/pes/conf.d/mupen64plus \"\$1\"" >> $launchScript
run chmod 755 $launchScript

