#/bin/bash

#
#    This file is part of the Pi Entertainment System (PES).
#
#    PES provides an interactive GUI for games console emulators
#    and is designed to work on the Raspberry Pi.
#
#    Copyright (C) 2020 Neil Munday (neil@mundayweb.com)
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

# This script will compile and install gcc 5.4.
# This compiler version is required to compile mupen64plus-video-gles2n64
# due to this issue: https://github.com/ricrpi/mupen64plus-video-gles2n64/issues/25

# Before starting see the following notes:
#   - Set the amount of video RAM to 16MB
#   - Set the amount of swap to 1GB
#   - Make sure you have at least 4GB free space

functions=`realpath $( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )/../common/functions.sh`
source $functions || exit 1

pkgDir="$rootDir/src/packages/gcc54"
checkDir $pkgDir
cd $pkgDir

arch=`uname -m`
pkgFile="gcc54-5.4.0-1-${arch}.pkg.tar.xz"

if [ -e $pkgFile ]; then
  echo "$pkgFile already exists, exiting"
  exit 0
fi

run makepkg
checkFile $pkgFile
run sudo pacman -U $pkgFile
