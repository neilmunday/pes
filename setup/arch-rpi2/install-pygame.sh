#!/bin/bash

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

pygameTar=$baseDir/src/pygame-1.9.1release.tar.gz
pygameDir=$buildDir/pygame-1.9.1release
pygamePatchDir=$baseDir/src/pygame-patches

header "Downloading pygame..."

run cd $baseDir/src

if [ ! -e $pygameTar ]; then
	echo "Downloading pygame..."
	run wget http://www.pygame.org/ftp/pygame-1.9.1release.tar.gz
fi

checkFile $pygameTar

if [ -e $pygameDir ]; then
	echo "Removing previously used source..."
	run rm -rvf $pygameDir
fi

run cd $buildDir
run tar xvfz $pygameTar
run cd $pygameDir

header "Patching pygame..."

run find . -type f -exec sed -i 's#/usr/bin/env python#/usr/bin/env python2#' {} +

run cd src
run patch -i "$pygamePatchDir/joystick.c.patch"
run cd ..
run patch -p0 -i "$pygamePatchDir/config.patch"
run patch -p1 -i "$pygamePatchDir/pygame-v4l.patch"

run python2 config.py -auto
run sudo python2 setup.py build
run sudo python2 setup.py install --prefix=/opt/python2
