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

function run {
	"$@"
	local status=$?
	if [ $status -ne 0 ]; then
		echo "Error executing $@"
		exit 1
	fi
}

function header {
	echo ""
	echo "*******************************"
	echo "$1"
	echo "*******************************"
	echo ""
}

function checkDir {
	if [ ! -e $1 ]; then
		echo "Directory $1 does not exist"
		exit 1
	fi
}

function checkFile {
	if [ ! -e $1 ]; then
		echo "File $1 does not exist"
		exit 1
	fi
}

function rmSourceDir {
	d=$1
	if [ -e $d ]; then
		echo "Removing previous source build: $d"
		run rm -rfv $d
	fi
}

export baseDir=/home/pi/pes
export buildDir=$baseDir/build

if [ ! -e $buildDir ]; then
	run mkdir $buildDir
fi
