#
#    This file is part of the Pi Entertainment System (PES).
#
#    PES provides an interactive GUI for games console emulators
#    and is designed to work on the Raspberry Pi.
#
#    Copyright (C) 2015 Neil Munday (neil@mundayweb.com)
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

VERSION_NUMBER = '2.0 (ALPHA)'
VERSION_DATE = '2015-12-04'
VERSION_AUTHOR = 'Neil Munday'

baseDir = os.path.abspath(os.path.dirname(os.path.realpath(__file__)) + os.sep + '../../')
resourceDir = baseDir + os.sep + 'resources'
defaultFontFile = resourceDir + os.sep + 'verdana.ttf'
confDir = baseDir + os.sep + 'conf.d'
userDir = os.path.expanduser('~') + os.sep + '.pes'
userConfDir = userDir + os.sep + 'conf.d'
userPesConfDir = userConfDir + os.sep + 'pes'
userPesConfigFile = userPesConfDir + os.sep + 'pes.ini'
userConsolesConfigFile = userPesConfDir + os.sep + 'consoles.ini'
userGamesCatalogueFile = userPesConfDir + os.sep + 'games_catalogue.ini'
userGameControllerFile = userPesConfDir + os.sep + 'gamecontrollerdb.txt'
userPesDb = userDir + os.sep + 'pes.db'
