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

# install packages

# initialise pacman keyring
run sudo  pacman-key --populate archlinuxarm

run sudo pacman -S bluez-libs bluez-utils \
	autoconf automake bison byacc flex gcc git cmake make patch pkg-config scons swig vim wget xa \
	libusb-compat linuxconsole \
	python2 python2-pip python2-imaging \
	freetype2 \
	dosfstools parted \
	mc \
	rsync \
	samba \
	fbset mesa mesa-libgl alsa-utils \
	crda iw wpa_supplicant \
	p7zip zip unzip \
	sdl \
	mkinitcpio \
	fakeroot

# don't use use Arch Linux package for Kodi on Raspberry Pi 2/3
# the Arch Linux package for this platform uses Kodi 19 which requires KMS overlay
if [ `uname -m` != "armv7l" ]; then
	run sudo pacman kodi-rbp kodi-rbp-eventclients kodi-rbp-tools-texturepacker kodi-rbp-dev kodi-platform
fi

run sudo pip2 install --upgrade pip
run sudo pip2 install python-Levenshtein
run sudo pip2 install reparted
run sudo pip2 install fstab
run sudo pip2 install pyalsaaudio
