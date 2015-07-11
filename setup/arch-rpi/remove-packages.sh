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

source /home/pi/pes/setup/arch-rpi/functions.sh

# remove packages to reduce the size of the root partition

packages="binutils
gcc
libyaml
lua
make
patch
pkg-config
python2-pip
ruby
scons
vim
vim-runtime
wget"

for p in $packages; do
	echo "Removing $p"
	sudo pacman -R $p
done

exit 0
