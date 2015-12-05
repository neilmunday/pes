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
userPesDb = userDir + os.sep + 'pes.db'
