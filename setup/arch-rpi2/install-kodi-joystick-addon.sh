#!/bin/bash

#
#    This file is part of the Pi Entertainment System (PES).
#
#    PES provides an interactive GUI for games console emulators
#    and is designed to work on the Raspberry Pi.
#
#    Copyright (C) 2021 Neil Munday (neil@mundayweb.com)
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

header "Building Kodi joystick add on"

# must use corresponding Kodi version, e.g. Leia
version=1.4.9-Leia
srcTar=$srcDir/${version}.tar.gz

if [ ! -e $srcTar ]; then
  cd $srcDir
  run wget https://github.com/xbmc/peripheral.joystick/archive/refs/tags/${version}.tar.gz
fi

cd $buildDir
rmSourceDir $version

run tar xvf $srcTar
checkDir peripheral.joystick-$version
cd peripheral.joystick-$version

run mkdir -p build
cd build

CFLAGS="-I/opt/kodi/current/include" CXXFLAGS="-I/opt/kodi/current/include" cmake \
  -DCMAKE_VERBOSE_MAKEFILE:BOOL=ON \
  -DCMAKE_INSTALL_PREFIX=/opt/kodi/current \
  -DCMAKE_BUILD_TYPE=Release \
  -DBUILD_SHARED_LIBS=1 \
  -DUSE_LTO=1  \
  ..

run make -j 4
run sudo make -j 4 DESTDIR=/opt/kodi/current install

