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

installDir="$baseDir/emulators"

if [ ! -e "$installDir" ]; then
	run mkdir $installDir
fi

cd $buildDir

header "Downloading RetroArch"

rmSourceDir "RetroArch"

run git clone  git://github.com/libretro/RetroArch.git

checkDir "RetroArch"

header "Building RetroArch"

cd RetroArch

retroArchInstallDir="$installDir/RetroArch"
retroArchConfigDir="$retroArchInstallDir/etc"
retroArchCoresDir="$retroArchInstallDir/lib"

run mkdir -p $retroArchCoresDir
run mkdir -p $retroArchConfigDir

run ./configure --prefix="$retroArchInstallDir" --disable-udev --disable-ffmpeg --disable-netplay --disable-pulse
run make GLOBAL_CONFIG_DIR="$retroArchConfigDir"
run make GLOBAL_CONFIG_DIR="$retroArchConfigDir" install

cd $buildDir

header "Downloading MegaDrive emulator"

rmSourceDir "picodrive"
run git clone https://github.com/libretro/picodrive.git
checkDir "picodrive"
cd picodrive 
run git submodule init
run git submodule update
run ./configure
#make -f Makefile.libretro
make -f Makefile.libretro platform=armv6e
run cp picodrive_libretro.so $retroArchCoresDir
cd $buildDir

rmSourceDir "Genesis-Plus-GX"
run git clone https://github.com/ekeeke/Genesis-Plus-GX.git
checkDir "Genesis-Plus-GX"
cd "Genesis-Plus-GX"
run make -f Makefile.libretro
checkFile genesis_plus_gx_libretro.so
run cp genesis_plus_gx_libretro.so $retroArchCoresDir
cd $buildDir

header "Downloading SNES emulator"
#rmSourceDir "snes9x-next"
#run git clone https://github.com/libretro/snes9x-next.git
#checkDir "snes9x-next"
#cd "snes9x-next"
#run ./compile_libretro.sh make
#checkFile snes9x_next_libretro.so
#run cp snes9x_next_libretro.so $retroArchCoresDir
#cd $buildDir

rmSourceDir "pocketsnes-libretro"
run git clone https://github.com/libretro/pocketsnes-libretro
checkDir pocketsnes-libretro
cd "pocketsnes-libretro"
run make
checkFile libretro.so
run cp libretro.so $retroArchCoresDir/pocketsnes_libretro.so
cd $buildDir

rmSourceDir "fceu-next"
header "Downloading NES emulator"
run git clone git://github.com/libretro/fceu-next.git
checkDir "fceu-next"
cd fceu-next
checkDir "fceumm-code"
cd fceumm-code
run make -f Makefile.libretro
checkFile "fceumm_libretro.so"
run cp fceumm_libretro.so $retroArchCoresDir
cd $buildDir

rmSourceDir "gambatte-libretro"
header "Downloading GameBoy/GameBoy Color emulator"
run git clone git://github.com/libretro/gambatte-libretro
checkDir "gambatte-libretro"
cd gambatte-libretro
checkDir libgambatte
cd libgambatte
checkFile Makefile.libretro
run make -f Makefile.libretro
checkFile gambatte_libretro.so
run cp gambatte_libretro.so $retroArchCoresDir
cd $buildDir

rmSourceDir "pcsx_rearmed"
header "Downloading PSX emulator"
run git clone https://github.com/notaz/pcsx_rearmed
checkDir "pcsx_rearmed"
cd pcsx_rearmed
run git submodule
run git submodule update
run ./configure --platform=libretro
run make
run cp libretro.so $retroArchCoresDir/pcsx_libretro.so
cd $buildDir


