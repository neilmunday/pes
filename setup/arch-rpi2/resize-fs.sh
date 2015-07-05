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

echo "This script is now obsolete!"

exit

if [ "$USER" != "root" ]; then
	echo "This script must be run as root. Try running: \"sudo ./resize-fs.sh\" instead."
	exit 1
fi

read -p "Are you sure you want to automically resize your root partition? [y/n]" response
if [ "$response" == "y" ]; then
        echo "Running fdisk.."
	#echo -e "d\n2\nn\ne\n2\n\n\nn\nl\n\nw" | fdisk /dev/mmcblk0

	fdisk /dev/mmcblk0 <<EOF
d
5
d
2
n
e
2


n
l


w
EOF
	echo "You now need to reboot the system"
	echo "You can ignore any errors above about the kernel still having the file system in memory, this is normal"
	echo "Once rebooted run: sudo resize2fs /dev/mmcblk0p5"
else
        echo "No changes made."
fi

