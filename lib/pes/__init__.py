#
#    This file is part of the Pi Entertainment System (PES).
#
#    PES provides an interactive GUI for games console emulators
#    and is designed to work on the Raspberry Pi.
#
#    Copyright (C) 2016 Neil Munday (neil@mundayweb.com)
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
VERSION_DATE = '2016-02'
VERSION_AUTHOR = 'Neil Munday'

baseDir = os.path.abspath('%s%s../../' % (os.path.dirname(os.path.realpath(__file__)), os.sep))
resourceDir = '%s%sresources' % (baseDir, os.sep)
defaultFontFile = '%s%sverdana.ttf' % (resourceDir, os.sep)
confDir = '%s%sconf.d' % (baseDir, os.sep)
userDir = '%s%s.pes' % (os.path.expanduser('~'), os.sep)
userConfDir = '%s%sconf.d' % (userDir, os.sep)
userPesConfDir = '%s%spes' % (userConfDir, os.sep)
userPesConfigFile = '%s%spes.ini' % (userPesConfDir, os.sep)
userConsolesConfigFile = '%s%sconsoles.ini' % (userPesConfDir, os.sep)
userGamesCatalogueFile = '%s%sgames_catalogue.ini' % (userPesConfDir, os.sep)
userGameControllerFile = '%s%sgamecontrollerdb.txt' % (userPesConfDir, os.sep)
userPesDb = '%s%spes.db' % (userDir, os.sep)
