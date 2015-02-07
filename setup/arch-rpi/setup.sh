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

source /home/pi/pes/setup/arch-rpi/functions.sh

setupDir="$baseDir/setup/arch"

header "Updating OS..."
run sudo pacman -Syu

header "Installing additional packages..."
run $setupDir/install-packages.sh

header "Customising OS..."
run $setupDir/customise-os.sh

header "Setting up auto login..."
run $setupDir/auto-login.sh

header "Setting up PS3 Bluetooth control pad support.."
run $setupDir/install-qtsixad.sh

header "Installing SDL2..."
run $setupDir/install-sdl2.sh

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

header "Setting up Samba..."
run $setupDir/install-samba.sh

header "Setting up PESPad..."
run $setupDir/install-pespad.sh

header "Done!"
exit 0
