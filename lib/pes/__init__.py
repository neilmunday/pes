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

import os
import shutil
import sys
import logging

VERSION_NUMBER = '2.6'
VERSION_DATE = '2019-07-19'
VERSION_AUTHOR = 'Neil Munday'

baseDir = os.path.abspath('%s%s../../' % (os.path.dirname(os.path.realpath(__file__)), os.sep))
rasumExe = os.path.join("%s/bin/rasum" % baseDir)
resourceDir = os.path.join(baseDir, 'resources')
defaultFontFile = os.path.join(resourceDir, 'verdana.ttf')
gamepadImageFile = os.path.join(resourceDir, 'gamepad.png')
gamepadLayoutImageFile = os.path.join(resourceDir, 'gamepad-layout.png')
networkImageFile = os.path.join(resourceDir, 'network.png')
remoteImageFile = os.path.join(resourceDir, 'remote.png')
confDir = os.path.join(baseDir, 'conf.d')
userHomeDir = os.path.expanduser('~')
userDir = os.path.join(userHomeDir, 'pes')
userLogDir = os.path.join(userDir, 'log')
userConfDir = os.path.join(userDir, 'conf.d')
userRetroArchConfDir = os.path.join(userConfDir, 'retroarch')
userRetroArchJoysticksConfDir = os.path.join(userRetroArchConfDir, 'joysticks')
userRetroArchCheevosConfFile = os.path.join(userRetroArchConfDir, 'cheevos.cfg')
userMupen64PlusConfDir = os.path.join(userConfDir, 'mupen64plus')
userMupen64PlusConfFile =  os.path.join(userMupen64PlusConfDir, 'mupen64plus.cfg')
userGles2n64ConfFile =  os.path.join(userMupen64PlusConfDir, 'gles2n64.conf')
userViceConfDir = os.path.join(userConfDir, 'vice')
userViceJoystickConfFile = os.path.join(userViceConfDir, 'sdl-joymap-C64.vjm')
userKodiConfDir = os.path.join(userHomeDir, '.kodi')
userPesConfDir = os.path.join(userConfDir, 'pes')
userPesConfigFile = os.path.join(userPesConfDir, 'pes.ini')
userConsolesConfigFile = os.path.join(userPesConfDir, 'consoles.ini')
userGamesCatalogueFile = os.path.join(userPesConfDir, 'games_catalogue.ini')
userGameControllerFile = os.path.join(userPesConfDir, 'gamecontrollerdb.txt')
userPesDb = os.path.join(userDir, 'pes.db')
scriptFile = os.path.join(userDir, 'commands.sh')
cecEnabled = False
screenSaverTimeout = 0
