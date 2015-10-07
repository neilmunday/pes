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

setupDir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

if [ ! -e $setupDir/functions.sh ]; then
	echo "Error! $setupDir/functions does not exist!"
	exit 1
fi

source $setupDir/functions.sh

header "Updating OS..."

run sudo pacman -Syu

header "Installing additional packages..."
run $setupDir/install-packages.sh

header "Customising OS..."
run $setupDir/customise-os.sh

header "Setting up PS3 Bluetooth control pad support.."
run $setupDir/install-qtsixad.sh

header "Installing SDL2..."
run $setupDir/install-sdl2.sh

header "Installing libcec and Python bindings"
run $setupDir/install-libcec.sh

header "Installing up RetroArch..."
run $setupDir/install-retroarch.sh

header "Installing emulator cores..."
run $setupDir/install-fceu-next.sh
run $setupDir/install-gambatte.sh
run $setupDir/install-Genesis-Plus-GX.sh
run $setupDir/install-picodrive.sh
run $setupDir/install-pocketsnes.sh
run $setupDir/install-psx_rearmed.sh
run $setupDir/install-gpsp.sh
run $setupDir/install-mupen64plus.sh
run $setupDir/install-fuse-libretro.sh
run $setupDir/install-fba-libretro.sh
run $setupDir/install-imame4all.sh
run $setupDir/install-stella-libretro.sh

header "Setting up Samba..."
run $setupDir/install-samba.sh

header "Setting up auto login..."
run $setupDir/auto-login.sh

header "Done!"
exit 0
