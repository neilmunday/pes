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

#
# This script customises the OS to PES' needs.
#

source /home/pi/pes/setup/arch-rpi2/functions.sh

header "Setting timezone to London, UK"
run sudo timedatectl set-timezone Europe/London

header "Setting keyboard layout to UK"
run sudo localectl set-keymap --no-convert uk

header "Setting hostname"
run sudo hostnamectl set-hostname pes

header "Setting up groups for pi user"
run sudo usermod -a -G audio,input,video,users pi

header "Adding udev rules for USB control pads"

run sudo bash -c "cat > /etc/udev/rules.d/99-evdev.rules" << 'EOF'
KERNEL=="event*", NAME="input/%k", MODE="666"
EOF

header "Enabling bluetooth adapter at boot time..."
run sudo bash -c "cat > /etc/udev/rules.d/10-local.rules" << 'EOF'
ACTION=="add", KERNEL=="hci0", RUN+="/usr/bin/hciconfig hci0 up"
EOF

header "Disabling core files in /etc/systemd/system.conf"

if egrep -q "^DumpCore=no" /etc/systemd/system.conf; then
	echo "No need to disable - already done!"
else
	run sudo bash -c "echo \"DumpCore=no\" >> /etc/systemd/system.conf"
fi

header "Limiting journal file size to 50MB"

if egrep -q "^SystemMaxUse=50M" /etc/systemd/journald.conf ; then
	echo "No need to limit, already set!"
else
	if egrep -q "^SystemMaxUse=[0-9]+M" /etc/systemd/journald.conf ; then
		echo "Existing limit found, changing /etc/systemd/journald.conf"
		run sudo sed -r -i "s/^SystemMaxUse=[0-9]+M/SystemMaxUse=50M/" /etc/systemd/journald.conf
	else
		echo "Updating /etc/systemd/journald.conf"
		run sudo bash -c "echo \"SystemMaxUse=50M\" >> /etc/systemd/journald.conf"
	fi	
fi

header "Setting up swap"

swapfile="/swapfile"

if grep -q "$swapfile" /etc/fstab; then
	echo "Swap file already present in /etc/fstab"
else
	if [ -e $swapfile ]; then
		echo "Warning! $swapfile already exists - skipping swap file creation!"
	else
		echo "Creating swap file..."
		run sudo fallocate -l 128M $swapfile
		run sudo chmod 600 $swapfile
		run sudo mkswap $swapfile
		run sudo swapon $swapfile

		echo "Adding to /etc/fstab"
		run sudo bash -c "echo \"/swapfile              none          swap      defaults                        0      0\" >> /etc/fstab"
	fi
fi
