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

header "Enabling Pi auto-login"

sudo mkdir -p /etc/systemd/system/getty@tty1.service.d

sudo bash -c "cat > /etc/systemd/system/getty@tty1.service.d/autologin.conf" << 'EOF'
[Service]
ExecStart=
ExecStart=-/usr/bin/agetty --autologin pi --noclear %I 38400 linux
Type=idle
EOF

if [ ! -e ~/.bash_pes ]; then
	echo "Creating ~/.bash_pes ..."
	echo "if [ ! -n \"\$SSH_CONNECTION\" ] && [ ! -n \"\$DESKTOP_SESSION\" ]; then" > ~/.bash_pes
	echo -e "\tif [ ! -d /data/roms ]; then" >> ~/.bash_pes
	echo -e "\t\techo \"Setting up /data partition - this will use all available space on your SD card!\"" >> ~/.bash_pes
	echo -e "\t\tsudo /opt/sbin/make_rom_partition.py -v -d /dev/mmcblk0" >> ~/.bash_pes
	echo -e "\t\tsudo systemctl restart smbd.service" >> ~/.bash_pes
	echo -e "\tfi" >> ~/.bash_pes
	echo -e "\techo \"Giving time for network interface to start...\"" >> ~/.bash_pes
	echo -e "\tfor i in \`seq 1 10\`; do" >> ~/.bash_pes
	echo -e "\t\ts=\$((10-i))" >> ~/.bash_pes
	echo -e "\t\techo -e -n \"Wating for \${s}s \\\r\"" >> ~/.bash_pes
	echo -e "\t\tsleep 1" >> ~/.bash_pes
	echo -e "\tdone" >> ~/.bash_pes
	echo -e "\techo \"Truncating log file...\"" >> ~/.bash_pes
	echo -e "\t> $baseDir/log/pes.log" >> ~/.bash_pes
    echo -e "\techo \"Starting PES...\"" >> ~/.bash_pes
	echo -e "\t~/pes/bin/pes.sh -l $baseDir/log/pes.log" >> ~/.bash_pes
	echo "fi" >> ~/.bash_pes
fi

if [[ `egrep "^source ~/.bash_pes" ~/.bashrc` ]]; then
	echo "No need to modify bash profile"
else
	echo "Modifying ~/.bashrc ..."
	echo "source ~/.bash_pes" >> ~/.bashrc
fi
