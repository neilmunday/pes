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
#	pes.sh
#
#	This script is a launch wrapper for PES.
#	Upon exiting, pes.py will write to a file called "commands.sh".
#	Providing this file has been generated and pes.py exited ok,
#	this script will execute the commands in the file.
#	Usually, the commands written to the file will include the launch
#	command for an emulator and calling this script again.
#	By using this process we ensure that the python interpreter is not
#	left running in the background consuming system resources whilst the
#	emulator is running the chosen game.
#	

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

script="$DIR/commands.sh"

# remove previous script file
rm -f $script

# prevent console from power saving
setterm -blank 0

$DIR/pes.py $@

if [ $? -eq 0 ]; then
	if [ -e $script ]; then
		chmod 700 $script
		exec $script
	else
		echo "$script does not exist!"
		exit 1
	fi
else
	echo "PES experienced an error!"
	exit 1
fi

