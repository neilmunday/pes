#!/bin/bash

#
#    This file is part of the Pi Entertainment System (PES).
#
#    PES provides an interactive GUI for games console emulators
#    and is designed to work on the Raspberry Pi.
#
#    Copyright (C) 2018 Neil Munday (neil@mundayweb.com)
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
#	Utility script to switch video mode to 4:3 ratio as this is required
#	by some emulators, e.g. imame4all and FBA
#

if [ -z $1 ]; then
	echo "No command line parameters supplied!"
	exit 1
fi

/opt/vc/bin/tvservice -e "CEA 2"
# give time for the display device to switch modes
sleep 5
# reset frame buffer
fbset -depth 8 && fbset -depth 16
# execute the command
$1
# reset display device back to its preferred video mode
/opt/vc/bin/tvservice -p
# give time for the display device to switch modes
sleep 5
# reset frame buffer
fbset -depth 8 && fbset -depth 16
