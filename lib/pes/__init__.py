import os
import shutil
import sys
import logging

VERSION_NUMBER = '2.0 (ALPHA)'
VERSION_DATE = '2015-12-04'
VERSION_AUTHOR = 'Neil Munday'

baseDir = os.path.abspath(os.path.dirname(os.path.realpath(__file__)) + os.sep + '../../')
confDir = baseDir + os.sep + 'conf.d'
userDir = os.path.expanduser('~') + os.sep + '.pes'
userConfDir = userDir + os.sep + 'conf.d'
userPesConfDir = userConfDir + os.sep + 'pes'
userPesConfigFile = userPesConfDir + os.sep + 'pes.ini'
userConsolesConfigFile = userPesConfDir + os.sep + 'consoles.ini'
userGamesCatalogueFile = userPesConfDir + os.sep + 'games_catalogue.ini'
userPesDb = userDir + os.sep + 'pes.db'

def checkDir(dir):
	if not os.path.exists(dir):
		pesExit("Error: %s does not exist!" % dir, True)
	if not os.path.isdir(dir):
		pesExit("Error: %s is not a directory!" % dir, True)

def checkFile(file):
	if not os.path.exists(file):
		pesExit("Error: %s does not exist!" % file, True)
	if not os.path.isfile(file):
		pesExit("Error: %s is not a file!" % file, True)
		
def initConfig():
	logging.debug("initialising config...")
	checkDir(userConfDir)
	for root, dirs, files in os.walk(confDir):		
		userRoot = root.replace(baseDir, userDir)
		for d in dirs:
			dest = userRoot + os.sep + d
			if not os.path.exists(dest):
				mkdir(dest)
				
		for f in files:
			dest = userRoot + os.sep + f
			source = root + os.sep + f
			if not os.path.exists(dest):
				logging.debug("copying %s to %s" % (source, dest))
				shutil.copy(source, dest)
			
		
def mkdir(path):
	if not os.path.exists(path):
		logging.debug("creating directory: %s" % path)
		os.mkdir(path)
		return True
	elif not os.path.isdir(path):
		pesExit("Error: %s is not a directory!" % path, True)
	elif not os.access(path, os.W_OK):
		pesExit("Error: %s is not writeable!" % path, True)
	# did not have to make directory so return false
	return False
		
def pesExit(msg = None, error = False):
	if error:
		if msg:
			logging.error(msg)
		else:
			logging.error("Unrecoverable error occurred, exiting!")
		sys.exit(1)
	if msg:
		logging.info(msg)
	else:
		logging.info("Exiting...")
	sys.exit(0)