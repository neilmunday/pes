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
rmSourceDir "libcec"

version=4.0.4

header "Downloading libcec"

run git clone https://github.com/Pulse-Eight/libcec
checkDir libcec
cd libcec
run git checkout tags/libcec-${version}
run mkdir build
cd build
run cmake -DRPI_INCLUDE_DIR=/opt/vc/include -DRPI_LIB_DIR=/opt/vc/lib -DCMAKE_INSTALL_PREFIX=/opt/libcec/$version -DPYTHON_INCLUDE_DIR=/usr/include/python2.7 -DPYTHON_LIBRARY=/usr/lib/libpython2.7.so ..
run make
run sudo make install
run sudo rm -f /opt/libcec/current
run sudo ln -s /opt/libcec/$version /opt/libcec/current
run sudo mv /opt/libcec/${version}/lib/python2.7/site-packages/cec.py  /opt/libcec/${version}/lib/python2.7/site-packages/cec/__init__.py
