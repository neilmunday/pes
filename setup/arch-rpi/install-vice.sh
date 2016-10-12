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

functions=`realpath $( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )/../common/functions.sh`
source $functions || exit 1

version=2.4

cd $buildDir

rmSourceDir "vice-${version}"

PREFIX=$emulatorInstallDir/vice
tarFile=$srcDir/vice-${version}.tar.gz

header "Building C64 emulator - vice"

patchFile="$rootDir/src/vice-patches/gifdrv.patch"
checkFile $patchFile

if [ ! -e $tarFile ]; then
	run wget -O $tarFile http://sourceforge.net/projects/vice-emu/files/releases/vice-${version}.tar.gz/download
fi

run tar xvfz $tarFile
checkDir vice-${version}
cd vice-${version}

# apply patches
checkDir src/gfxoutputdrv
cd src/gfxoutputdrv
patch < $patchFile

cd ../..

run ./configure --prefix=$PREFIX --enable-sdlui
run make
run sudo make install

# now copy over data files
run sudo cp -vr data $PREFIX/
run sudo rm $PREFIX/data/Makefile*
