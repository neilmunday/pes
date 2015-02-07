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

cd $buildDir

installDir="/opt/pespad"

header "Downloading PESPad"

git clone git://github.com/neilmunday/pespad

checkDir pespad

run cd pespad

checkFile systemd/pespad.service

if [ ! -e $pespad ]; then
	header "Making $installDir"
	run sudo mkdir -v /opt/pespad
fi

header "Copying files"

run cp -rv pespad.py web $installDir

header "Adding kernel module to system boot"

sudo bash -c "cat > /etc/modules-load.d/uinput.conf" << 'EOF'
uinput

EOF

header "Adding service"

run cp -v systemd/pespad.service /etc/systemd/system/pespad.service

run sudo systemctl enable pespad.service

header "Starting service"

run sudo systemctl start pespad.service

