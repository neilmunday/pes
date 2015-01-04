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
#    THIS IS A WORK IN PROGRESS!
#

source /home/pi/pes/setup/arch/functions.sh

header "THIS IS A WORK IN PROGRESS!"

PREFIX=$emulatorInstallDir/mupen64plus

header "Building N64 emulator - mupenplus64"

#
# core
#

cd $buildDir

component=mupen64plus-core

#rmSourceDir $component

if [ ! -e $component ]; then
	header "Downloading $component"
	run git clone https://github.com/ricrpi/$component
	checkDir $component
	cd $component
	run git remote add upstream https://github.com/mupen64plus/$component
	run git checkout ric_dev
else
	header "Updating $component"
	cd $component
	run git pull origin ric_dev
fi

set APIDIR=`pwd`/src/api
set SDL_CFLAGS=`sdl-config --cflags`
set SDL_LDFLAGS=`sdl-config --libs`

checkDir projects/unix
cd projects/unix
echo "Fixing Makefile..."
run sed -r -i "s/else if/else ifeq/" Makefile

#run make USE_GLES=1 VFP=1 clean
run make PREFIX=$PREFIX USE_GLES=1 VFP=1 RPIFLAGS="-I/opt/vc/include -I/opt/vc/include/interface/vcos/pthreads -L/opt/vc/lib -D__ARM_PCS_VFP -fgcse-after-reload -finline-functions -fipa-cp-clone -funswitch-loops -fpredictive-commoning -ftree-loop-distribute-patterns -ftree-vectorize -mfpu=vfp -mfloat-abi=hard -march=armv6zk -mtune=arm1176jzf-s" install

unset APIDIR

#
# ui-console
#

cd $buildDir

component=mupen64plus-ui-console

if [ ! -e $component ]; then
	header "Downloading $component"
	run git clone https://github.com/mupen64plus/$component
	checkDir $component
	cd $component
else
	header "Updating $component"
	cd $component
	run git pull origin master
fi

checkDir projects/unix
cd projects/unix
#run make clean
run make PREFIX=$PREFIX install

#
# audio-omx
#

cd $buildDir

component=mupen64plus-audio-omx

if [ ! -e $component ]; then
	header "Downloading $component"
	run git clone https://github.com/ricrpi/$component
	checkDir $component
	cd $component
else
	header "Updating $component"
	cd $component
	run git pull origin master
fi

checkDir projects/unix
cd projects/unix
#run make clean
run make PREFIX=$PREFIX install

#
# input-sdl
#

cd $buildDir

component=mupen64plus-input-sdl

if [ ! -e $component ]; then
	header "Downloading $component"
	run git clone https://github.com/mupen64plus/$component
	checkDir $component
	cd $component
else
	header "Updating $component"
	cd $component
	run git pull origin master
fi

checkDir projects/unix
cd projects/unix
#run make clean
run make PREFIX=$PREFIX install

#
# rsp-hle
#

cd $buildDir

component=mupen64plus-rsp-hle

if [ ! -e $component ]; then
	header "Downloading $component"
	run git clone https://github.com/ricrpi/$component
	checkDir $component
	cd $component
	run git remote add upstream https://github.com/mupen64plus/$component
	run git checkout master
else
	header "Updating $component"
	cd $component
	run git pull origin master
fi

checkDir projects/unix
cd projects/unix
#run make clean
run make PREFIX=$PREFIX install

#
# video-gles2rice
#

cd $buildDir

component=mupen64plus-video-gles2rice

if [ ! -e $component ]; then
	header "Downloading $component"
	run git clone https://github.com/ricrpi/$component
	checkDir $component
	cd $component
else
	header "Updating $component"
	cd $component
	run git pull origin master
fi

#echo "Fixing CNvTNTCombiner.cpp"
#run sed -r -i "s/#include <GL\/gl.h>/#include <GLES\/gl.h>/" src/CNvTNTCombiner.cpp
#run sed -r -i "s/#include <GL\/glext.h>/#include <GLES\/glext.h>/" src/CNvTNTCombiner.cpp
#run sed -r -i "s/GL_SUBTRACT_ARB/GL_SUBTRACT/" src/CNvTNTCombiner.cpp
#echo "Fixing OGLExtensions.h"
#run sed -r -i "s/#include <GL\/gl.h>/#include <GLES\/gl.h>/" src/OGLExtensions.h
#run sed -r -i "s/#include <GL\/glext.h>/#include <GLES\/glext.h>/" src/OGLExtensions.h

checkDir projects/unix
cd projects/unix
#run make GL_CLFLAGS="-I/opt/vc/include -I/opt/vc/include/interface/vcos/pthreads -I/opt/vc/include/interface/vmcs_host/linux" GL_LDLIBS="-L/opt/vc/lib -lGLESv2 -lEGL -lbcm_host" clean
run make PREFIX=$PREFIX GL_CLFLAGS="-I/opt/vc/include -I/opt/vc/include/interface/vcos/pthreads -I/opt/vc/include/interface/vmcs_host/linux" GL_LDLIBS="-L/opt/vc/lib -lGLESv2 -lEGL -lbcm_host" install

#
# video-gles2n64
#

cd $buildDir

component=mupen64plus-video-gles2n64

if [ ! -e $component ]; then
	header "Downloading $component"
	run git clone https://github.com/ricrpi/$component
	checkDir $component
	cd $component
else
	header "Updating $component"
	cd $component
	run git pull origin master
fi

checkDir projects/unix
cd projects/unix
run make clean
run make PREFIX=$PREFIX install

#
# rom
#

#cd $buildDir

#component=mupen64plus-rom

#if [ ! -e $component ]; then
#	header "Downloading $component"
#	run git clone https://github.com/mupen64plus/$component
#	checkDir $component
#	cd $component
#else
#	header "Updating $component"
#	cd $component
#	run git pull origin master
#fi

#checkDir projects/unix
#cd projects/unix
#run make clean
#run make PREFIX=$PREFIX install

