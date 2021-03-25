#!/bin/bash

#
#    This file is part of the Pi Entertainment System (PES).
#
#    PES provides an interactive GUI for games console emulators
#    and is designed to work on the Raspberry Pi.
#
#    Copyright (C) 2014-2014-2021 Neil Munday (neil@mundayweb.com)
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

# based on https://github.com/PIPplware/xbmc/blob/leia_backports/build_rpi_debian_packages.sh

functions=`realpath $( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )/../common/functions.sh`
source $functions || exit 1

cd $buildDir

header "Building Kodi"

# need to remove MESA to make build work
if pacman -Q mesa > /dev/null 2>&1; then
  run sudo pacman --noconfirm -R libglvnd mesa
fi

# install build dependencies
if ! pacman -Q jdk-openjdk > /dev/null 2>&1; then
  run sudo pacman --noconfirm -S jdk-openjdk ghostscript
fi

#rmSourceDir xbmc
if [ ! -d xbmc ]; then
  run git clone https://github.com/PIPplware/xbmc
  checkDir xbmc
  cd xbmc
  run git checkout leia_backports
else
  cd xbmc
fi

KODI_VERSION='18.9'

REPO_DIR=`pwd`
KODI_BUILD_DIR="${REPO_DIR}/build"

echo "repo dir: $REPO_DIR"
echo "build dir: $KODI_BUILD_DIR"

KODI_OPTS="\
-DVERBOSE=1 \
-DCORE_SYSTEM_NAME=linux \
-DCORE_PLATFORM_NAME=rbpi \
-DAPP_RENDER_SYSTEM=gles \
-DENABLE_MMAL=ON \
-DENABLE_OPENGL=OFF \
-DWITH_CPU=cortex-a7 \
-DCMAKE_PREFIX_PATH=/opt/vc \
-DENABLE_OPENGLES=ON \
-DCMAKE_BUILD_TYPE=Release \
-DCMAKE_INSTALL_PREFIX=/opt/kodi/${KODI_VERSION} \
-DENABLE_AIRTUNES=ON \
-DENABLE_ALSA=ON \
-DENABLE_AVAHI=ON \
-DENABLE_BLURAY=ON \
-DENABLE_CEC=ON \
-DENABLE_DBUS=ON \
-DENABLE_DVDCSS=ON \
-DENABLE_EGL=ON \
-DEGL_INCLUDE_DIR=/opt/vc/include/EGL \
-DEGL_LIBRARY=/opt/vc/lib/libbrcmEGL.so \
-DOPENGLES_INCLUDE_DIR=/opt/vc/include/GLES2 \
-DOPENGLES_gl_LIBRARY=/opt/vc/lib/libbrcmGLESv2.so \
-DENABLE_EVENTCLIENTS=ON \
-DENABLE_INTERNAL_CROSSGUID=ON \
-DENABLE_INTERNAL_FMT=ON \
-DENABLE_INTERNAL_FFMPEG=ON
-DENABLE_INTERNAL_RapidJSON=ON \
-DENABLE_INTERNAL_FLATBUFFERS=ON \
-DENABLE_MICROHTTPD=ON \
-DENABLE_MYSQLCLIENT=ON \
-DENABLE_NFS=ON \
-DENABLE_OPENSSL=ON \
-DENABLE_OPTICAL=ON \
-DENABLE_PULSEAUDIO=ON \
-DENABLE_SMBCLIENT=ON \
-DENABLE_SSH=ON \
-DENABLE_UDEV=ON \
-DENABLE_UPNP=ON \
-DENABLE_XSLT=ON \
-DENABLE_LIRC=ON \
-DENABLE_APP_AUTONAME=OFF \
-DENABLE_LCMS2=OFF \
-DENABLE_SNDIO=OFF \
-DENABLE_MDNS=OFF \
-DENABLE_INTERNAL_FSTRCMP=ON \
-DCEC_LIBRARY=/opt/libcec/current/lib/libcec.so \
-DCEC_INCLUDE_DIR=/opt/libcec/current/include
"

EXTRA_FLAGS="-Os -fomit-frame-pointer -I/opt/vc/include -I/opt/vc/include/interface/vcos/pthreads -I/opt/vc/include/interface/vmcs_host/linux -I/opt/vc/include/mmal -I/opt/vc/include/interface/vchiq_arm -I/opt/vc/include/IL -I/opt/vc/include/GLES2"

[ -d $KODI_BUILD_DIR ] || mkdir -p $KODI_BUILD_DIR || exit 1
cd $KODI_BUILD_DIR || exit 1

run rm -rf $KODI_BUILD_DIR/CMakeCache.txt $KODI_BUILD_DIR/CMakeFiles $KODI_BUILD_DIR/CPackConfig.cmake $KODI_BUILD_DIR/CTestTestfile.cmake $KODI_BUILD_DIR/cmake_install.cmake

CXXFLAGS=${EXTRA_FLAGS} CFLAGS=${EXTRA_FLAGS} LDFLAGS="-L/opt/vc/lib" cmake ${KODI_OPTS} ${REPO_DIR}/

run cmake --build . -v -j 3 

run sudo rm -rf /opt/kodi/${KODI_VERSION}
run sudo make install
run sudo rm -f /opt/kodi/current
run sudo ln -s /opt/kodi/${KODI_VERSION} /opt/kodi/current

# install additional components
components=
  'kodi-addon-dev' \
  'kodi-eventclients-dev' \
  'kodi-eventclients-common' \
  'kodi-eventclients-ps3' \
  'kodi-eventclients-kodi-send' \
  'kodi-tools-texturepacker'

for comp in $components; do
  run DESTDIR=/opt/kodi/${KODI_VERSION} cmake -DCMAKE_INSTALL_COMPONENT=$comp -P cmake_install.cmake
done

# remove build dependencies
run sudo pacman --noconfirm -R \
	jdk-openjdk \
	java-environment-common \
	java-runtime-common \
	jre-openjdk \
	jre-openjdk-headless \
	libnet \
	ghostscript \
	ijs \
	libpaper \
	run-parts

# put mesa back
run sudo pacman --noconfirm -S mesa

echo "Done"
