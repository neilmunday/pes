#!/bin/bash

#
#    This file is part of the Pi Entertainment System (PES).
#
#    PES provides an interactive GUI for games console emulators
#    and is designed to work on the Raspberry Pi.
#
#    Copyright (C) 2019 Neil Munday (neil@mundayweb.com)
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

run sudo dnf install \
	alsa-lib-devel \
	bluez-libs-devel \
	boost-devel \
	dbus-devel \
	gcc \
	gcc-c++ \
	make \
	cmake \
	freetype-devel \
	kodi \
	libjpeg-turbo-devel \
	libpng-devel \
	libtiff-devel \
	libusb-devel \
	mesa-libGL-devel \
	mesa-libGLES-devel \
	mesa-libEGL-devel \
	openssl-devel \
	patch \
	pkgconfig \
	pulseaudio-libs-devel \
	python-devel \
	python-Levenshtein \
	python-pillow \
	python-pip \
	samba \
	scons \
	SDL-devel \
	systemd-devel \
	swig \
	wget \
	xz-devel \
	zlib-devel

run sudo pip2 install --upgrade pip
