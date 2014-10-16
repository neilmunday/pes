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

setupDir="$baseDir/setup/arch"

header "Updating OS..."
run sudo pacman -Syu

header "Installing additional packages..."
run $setupDir/install-packages.sh

header "Setting up PS3 Bluetooth control pad support.."
run $setupDir/install-ps3-control-pad.sh

header "Setting up RetroArch..."
run $setupDir/install-retroarch.sh

header "Setting up auto login..."
run $setupDir/auto-login.sh

header "Setting up Samba..."
run $setupDir/install-samba.sh

header "Setting up PESPad..."
run $setupDir/install-pespad.sh

header "Done!"
exit 0
