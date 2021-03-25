#
#    This file is part of the Pi Entertainment System (PES).
#
#    PES provides an interactive GUI for games console emulators
#    and is designed to work on the Raspberry Pi.
#
#    Copyright (C) 2014-2021 Neil Munday (neil@mundayweb.com)
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

thisDir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

export rootDir=`realpath "$thisDir/../../"`
export buildDir=$HOME/pes-build
export srcDir=$HOME/src
export pesDir="/opt/pes"
export pesUserDir="$HOME/pes"
export pesBiosDir="$pesUserDir/BIOS"
export emulatorInstallDir="$pesDir/emulators"
export retroArchInstallDir="$emulatorInstallDir/RetroArch"
export retroArchConfigDir="$retroArchInstallDir/etc"
export retroArchCoresDir="$retroArchInstallDir/lib"

if [ ! -e $buildDir ]; then
	run mkdir -p $buildDir
fi

if [ ! -e $pesDir ]; then
	run sudo mkdir -p $pesDir
fi

if [ ! -e $srcDir ]; then
	run mkdir $srcDir
fi

if [ ! -e $emulatorInstallDir ]; then
	run sudo mkdir -p $emulatorInstallDir
fi

if [ ! -e $pesUserDir ]; then
	run mkdir -p $pesUserDir
fi

if [ ! -e $pesBiosDir ]; then
	run mkdir -p $pesBiosDir
fi
