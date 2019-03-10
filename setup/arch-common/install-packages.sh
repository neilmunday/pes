#!/bin/bash

#
#    This file is part of the Pi Entertainment System (PES).
#
#    PES provides an interactive GUI for games console emulators
#    and is designed to work on the Raspberry Pi.
#
#    Copyright (C) 2018 Neil Munday (neil@mundayweb.com)
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

# Note: as of PES 2.3, bluez and bluez-plugins are provided by the
# bluez-ps3 package from the AUR - see install-bluez-ps.sh

# initialise pacman keyring
run sudo  pacman-key --populate archlinuxarm

run sudo pacman -S bluez-libs bluez-utils \
	autoconf automake bison byacc flex gcc git cmake make patch pkg-config scons swig vim wget \
	libusb-compat linuxconsole libplatform \
	python2 python2-levenshtein python2-pip python2-imaging \
	freetype2 \
	dosfstools parted \
	rsync \
	samba \
	fbset mesa mesa-libgl alsa-utils \
	crda iw wpa_supplicant \
	p7zip zip unzip \
	sdl \
	mkinitcpio \
	kodi-rbp kodi-rbp-eventclients kodi-rbp-tools-texturepacker kodi-rbp-dev kodi-platform \
	fakeroot

run sudo pip2 install --upgrade pip
run sudo pip2 install reparted
run sudo pip2 install fstab
