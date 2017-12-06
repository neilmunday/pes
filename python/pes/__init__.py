#    PES provides an interactive GUI for games console emulators
#    and is designed to work on the Raspberry Pi.
#
#    Copyright (C) 2017 Neil Munday (neil@mundayweb.com)
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

VERSION_NUMBER = '3.0 (ALPHA)'
VERSION_DATE = '2017-08-10'
VERSION_AUTHOR = 'Neil Munday'

romScrapers = ['theGamesDb.net'] # list of ROM scrapers, default scraper is assumed to be at index 0

baseDir = os.path.abspath('%s%s../../' % (os.path.dirname(os.path.realpath(__file__)), os.sep))
rasumExe = os.path.join("%s/bin/rasum" % baseDir)
confDir = os.path.join(baseDir, 'conf.d')
themeDir = os.path.join(baseDir, 'themes')
userHomeDir = os.path.expanduser('~')
userDir = os.path.join(userHomeDir, 'pes')
userDb = os.path.join(userDir, 'pes.db')
userBiosDir = os.path.join(userDir, 'BIOS')
userLogDir = os.path.join(userDir, 'log')
userConfDir = os.path.join(userDir, 'conf.d')
userRetroArchConfDir = os.path.join(userConfDir, 'retroarch')
userRetroArchJoysticksConfDir = os.path.join(userRetroArchConfDir, 'joysticks')
userRetroArchCheevosConfFile = os.path.join(userRetroArchConfDir, 'cheevos.cfg')
userMupen64PlusConfDir = os.path.join(userConfDir, 'mupen64plus')
userMupen64PlusConfFile = os.path.join(userMupen64PlusConfDir, 'mupen64plus.cfg')
userGles2n64ConfFile = os.path.join(userMupen64PlusConfDir, 'gles2n64.conf')
userViceConfDir = os.path.join(userConfDir, 'vice')
userViceJoystickConfFile = os.path.join(userViceConfDir, 'sdl-joymap-C64.vjm')
userKodiConfDir = os.path.join(userHomeDir, '.kodi')
userPesConfDir = os.path.join(userConfDir, 'pes')
userPesConfigFile = os.path.join(userPesConfDir, 'pes.ini')
userConsolesConfigFile = os.path.join(userPesConfDir, 'consoles.ini')
userGamesCatalogueFile = os.path.join(userPesConfDir, 'games_catalogue.ini')
userGameControllerFile = os.path.join(userPesConfDir, 'gamecontrollerdb.txt')
scriptFile = os.path.join(userDir, 'commands.sh')
cecEnabled = False
screenSaverTimeout = 0
