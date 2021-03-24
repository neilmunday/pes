#!/bin/bash

#
#    This file is part of the Pi Entertainment System (PES).
#
#    PES provides an interactive GUI for games console emulators
#    and is designed to work on the Raspberry Pi.
#
#    Copyright (C) 2014-2021 Neil Munday (neil@mundayweb.com)
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

export CFLAGS="-mfpu=neon -mtune=cortex-a72 -march=armv8-a"
export CXXFLAGS=$CFLAGS

PREFIX=$emulatorInstallDir/mupen64plus
SDL2_CONFIG=/opt/sdl2/default/bin/sdl2-config

header "Building N64 emulator - mupenplus64"

checkFile $SDL2_CONFIG

#
# core
#

cd $buildDir

component=mupen64plus-core

rmSourceDir $component

header "Downloading $component"
git clone https://github.com/mupen64plus/$component
checkDir $component
cd $component

set APIDIR=`pwd`/src/api
SDL_CFLAGS=`$SDL2_CONFIG --cflags`
SDL_LDLIBS=`$SDL2_CONFIG --libs`

checkDir projects/unix
cd projects/unix

run make -j 4 PREFIX=$PREFIX USE_GLES=1 VFP=1 NEON=1 VFP_HARD=1 SDL_CFLAGS="$SDL_CFLAGS" SDL_LDLIBS="$SDL_LDLIBS" V=1 -j all
run sudo make PREFIX=$PREFIX USE_GLES=1 VFP=1 NEON=1 VFP_HARD=1 SDL_CFLAGS="$SDL_CFLAGS" SDL_LDLIBS="$SDL_LDLIBS" V=1 -j install

unset APIDIR

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
run make -j 4 PREFIX=$PREFIX SDL_CFLAGS="$SDL_CFLAGS" SDL_LDLIBS="$SDL_LDLIBS" V=1 -j all
run sudo make PREFIX=$PREFIX SDL_CFLAGS="$SDL_CFLAGS" SDL_LDLIBS="$SDL_LDLIBS" V=1 -j install

#
# audio SDL
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
run make PREFIX=$PREFIX SDL_CFLAGS="$SDL_CFLAGS" SDL_LDLIBS="$SDL_LDLIBS" V=1 -j 4 all
run sudo make PREFIX=$PREFIX SDL_CFLAGS="$SDL_CFLAGS" SDL_LDLIBS="$SDL_LDLIBS" V=1 install

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
run make PREFIX=$PREFIX SDL_CFLAGS="$SDL_CFLAGS" SDL_LDLIBS="$SDL_LDLIBS" V=1 -j 4 all
run sudo make PREFIX=$PREFIX SDL_CFLAGS="$SDL_CFLAGS" SDL_LDLIBS="$SDL_LDLIBS" V=1 install

#
# rsp-hle
#

cd $buildDir

component=mupen64plus-rsp-hle

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
run make PREFIX=$PREFIX V=1 -j 4 all
run sudo make PREFIX=$PREFIX V=1 install

#
# video-rice
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
run make PREFIX=$PREFIX SDL_CFLAGS="$SDL_CFLAGS" SDL_LDLIBS="$SDL_LDLIBS" V=1 USE_GLES=1 -j 4 all
run sudo make PREFIX=$PREFIX SDL_CFLAGS="$SDL_CFLAGS" SDL_LDLIBS="$SDL_LDLIBS" V=1 USE_GLES=1 install

#
# video-gles2n64
#

cd $buildDir

component=mupen64plus-video-gles2n64

if [ ! -e $component ]; then
	header "Downloading $component"
	run git clone https://github.com/ricrpi/$component
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
run make -j 4 SDL_CFLAGS="$SDL_CFLAGS" SDL_LDLIBS="$SDL_LDLIBS" PREFIX=$PREFIX V=1 -j 4 all
run sudo make SDL_CFLAGS="$SDL_CFLAGS" SDL_LDLIBS="$SDL_LDLIBS" PREFIX=$PREFIX V=1 install
# remove shared installation of gles2n64.conf so that PES' copy takes precedence
run sudo rm -fv $PREFIX/share/mupen64plus/gles2n64.conf

#
# launcher script
#

launchScript="$PREFIX/bin/mupen64plus-launcher.sh"
tmpScript="$buildDir/mupen64plus-launcher"

run echo "#!/bin/bash" > $tmpScript
run echo "$PREFIX/bin/mupen64plus --corelib $PREFIX/lib/libmupen64plus.so.2 --datadir $PREFIX/share/mupen64plus --plugindir $PREFIX/lib/mupen64plus --configdir \$HOME/pes/conf.d/mupen64plus \"\$1\"" >> $tmpScript
run sudo cp $tmpScript $launchScript
run rm -f $tmpScript
run sudo chmod 755 $launchScript
