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

# install packages

run sudo pacman -S bluez bluez-libs bluez-plugins bluez-utils \
	gcc git make patch pkg-config scons vim wget \
	libusb-compat linuxconsole libcec-rpi \
	python2 python2-pygame python2-levenshtein python2-pip python2-imaging \
	ntp \
	parted \
	rsync \
	samba \
	sdl sdl_mixer sdl_ttf sdl_image \
	fbset mesa mesa-libgl alsa-utils \
	zip unzip

run sudo pip2 install --upgrade pip
run sudo pip2 install python-uinput
run sudo pip2 install cec
run sudo pip2 install reparted
run sudo pip2 install fstab

# enable services
run sudo systemctl enable ntpd.service
run sudo systemctl start ntpd.service


