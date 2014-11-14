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
	echo -e "\tGiving time for network interface to start..." >> ~/.bash_pes
        echo -e "for i in `seq 1 10`; do" >> ~/.bash_pes
        echo -e "\t\techo \"Wating for \${i}s\"" >> ~/.bash_pes
	echo -e "\t\tsleep 1" >> ~/.bash_pes
        echo -e "\tdone" >> ~/.bash_pes
	echo "Truncating log file..." >> ~/.bash_pes
	echo "> $baseDir/log/pes.log" >> ~/.bash_pes
        echo "Starting PES..." >> ~/.bash_pes
	echo -e "\tpython2 ~/pes/bin/pes.sh -v -l $baseDir/log/pes.log" >> ~/.bash_pes
	echo "fi" >> ~/.bash_pes
fi

if [[ `egrep "^source ~/.bash_pes" ~/.bashrc` ]]; then
	echo "No need to modify bash profile"
else
	echo "Modifying ~/.bashrc ..."
	echo "source ~/.bash_pes" >> ~/.bashrc
fi
