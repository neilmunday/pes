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

# remove packages to reduce the size of the root partition

packages="
autoconf
gcc
vim
vim-runtime
ruby
binutils
cmake
gcc
libyaml
lua
jsoncpp
make
patch
pkg-config
python2-pip
scons
wget
bison
byacc
flex
m4
kodi-rbp-dev
fakeroot
raspberrypi-firmware-examples
"

for p in $packages; do
	echo "Removing $p"
	sudo pacman --noconfirm -R $p
done

exit 0
