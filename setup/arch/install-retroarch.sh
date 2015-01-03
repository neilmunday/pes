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

source /home/pi/pes/setup/arch/functions.sh

cd $buildDir

header "Downloading RetroArch"

rmSourceDir "RetroArch"

run git clone  git://github.com/libretro/RetroArch.git

checkDir "RetroArch"

header "Building RetroArch"

cd RetroArch

run mkdir -p $retroArchCoresDir
run mkdir -p $retroArchConfigDir

run ./configure --prefix="$retroArchInstallDir" --disable-udev --disable-ffmpeg --disable-netplay --disable-pulse
run make GLOBAL_CONFIG_DIR="$retroArchConfigDir"
run make GLOBAL_CONFIG_DIR="$retroArchConfigDir" install

