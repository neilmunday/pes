#!/usr/bin/env python2

import argparse
import logging
import os
import shutil
import sqlite3
import sys
from pes import *
from pes.data import Console
from pes.gui import *

def processColour(colour):
	if len(colour) != 3:
		logging.error("processColour: colour array does not contain 3 elements!")
		return None
	rtn = []
	for c in colour:
		try:
			rtn.append(int(c))
		except ValueError, e:
			logging.error("processColour: %s is not an integer!" % c)
			return None
	return rtn

if __name__ == '__main__':
	parser = argparse.ArgumentParser(description='Launch the Pi Entertainment System (PES)', add_help=True)
	parser.add_argument('-w', '--window', help='Run PES in a window', dest='window', action='store_true')
	parser.add_argument('-v', '--verbose', help='Turn on debug messages', dest='verbose', action='store_true')
	parser.add_argument('-l', '--log', help='File to log messages to', type=str, dest='logfile')
	args = parser.parse_args()
	
	logLevel = logging.INFO
	if args.verbose:
		logLevel = logging.DEBUG

	if args.logfile:
		logging.basicConfig(format='%(asctime)s:%(levelname)s: %(message)s', datefmt='%Y/%m/%d %H:%M:%S', level=logLevel, filename=args.logfile)
	else:
		logging.basicConfig(format='%(asctime)s:%(levelname)s: %(message)s', datefmt='%Y/%m/%d %H:%M:%S', level=logLevel)
		
	dimensions = (0, 0)
	if args.window:
		dimensions = (900, 600)
	
	logging.debug("PES %s, date: %s, author: %s" % (VERSION_NUMBER, VERSION_DATE, VERSION_AUTHOR))
	
	try:
		logging.debug("PES base dir: %s" % baseDir)
		checkDir(baseDir)
		logging.debug("PES config dir: %s" % confDir)
		checkDir(confDir)
		logging.debug("PES user dir: %s" % userDir)
		
		mkdir(userDir)
		mkdir(userConfDir)
		initConfig()
		
		checkFile(userPesConfigFile)
		checkFile(userGamesCatalogueFile)
		checkFile(userConsolesConfigFile)
		
		logging.info("loading settings...")
		checkFile(userPesConfigFile)
		configParser = ConfigParser.ConfigParser()
		configParser.read(userPesConfigFile)
		
		if not configParser.has_section("colours"):
			pesExit("%s has no \"colours\" section!" % userPesConfigFile)
		
		romsDir = None
		coverartDir = None
		fontFile = None
		backgroundColour = None
		menuBackgroundColour = None
		headerBackgroundColour = None
		lineColour = None
		textColour = None
		
		userHome = os.path.expanduser('~')
		
		try:
			# pes settings
			fontFile = configParser.get('settings', 'fontFile').replace('%%BASE%%', baseDir)
			romsDir = configParser.get('settings', 'romsDir').replace('%%HOME%%', userHome)
			coverartDir = configParser.get('settings', 'coverartDir').replace('%%HOME%%', userHome)
			# colour settings
			backgroundColour = processColour(configParser.get("colours", "background").split(','))
			if backgroundColour == None:
				pesExit("invalid background colour in %s" % userPesConfigFile)
			menuBackgroundColour = processColour(configParser.get("colours", "menuBackground").split(','))
			headerBackgroundColour = processColour(configParser.get("colours", "headerBackground").split(','))
			lineColour = processColour(configParser.get("colours", "line").split(','))
			menuTextColour = processColour(configParser.get("colours", "menuText").split(','))
			menuSelectedTextColour = processColour(configParser.get("colours", "menuSelectedText").split(','))
			textColour = processColour(configParser.get("colours", "text").split(','))
		except ConfigParser.NoOptionError, e:
			pesExit("Error parsing config file %s: %s" % (userPesConfigFile, e.message), True)
			
		mkdir(romsDir)
		mkdir(coverartDir)
		
		# create database (if needed)
		con = None
		logging.debug('connecting to database: %s' % userPesDb)
		try:
			con = sqlite3.connect(userPesDb)
			con.row_factory = sqlite3.Row
			cur = con.cursor()
			cur.execute('CREATE TABLE IF NOT EXISTS `games`(`game_id` INTEGER PRIMARY KEY, `api_id` INT, `exists` INT, `console_id` INT, `name` TEXT, `cover_art` TEXT, `game_path` TEXT, `overview` TEXT, `released` INT, `last_played` INT, `favourite` INT(1), `play_cself.__exitount` INT, `size` INT )')
			cur.execute('CREATE INDEX IF NOT EXISTS "games_index" on games (game_id ASC)')
			cur.execute('CREATE TABLE IF NOT EXISTS `consoles`(`console_id` INTEGER PRIMARY KEY, `api_id` INT, `name` TEXT)')
			cur.execute('CREATE INDEX IF NOT EXISTS "console_index" on consoles (console_id ASC)')
			cur.execute('CREATE TABLE IF NOT EXISTS `games_catalogue` (`short_name` TEXT, `full_name` TEXT)')
			cur.execute('CREATE INDEX IF NOT EXISTS "games_catalogue_index" on games_catalogue (short_name ASC)')
			
			# is the games catalogue populated?
			cur.execute('SELECT COUNT(*) AS `total` FROM `games_catalogue`')
			row = cur.fetchone()
			if row['total'] == 0:
				logging.info("populating games catalogue using file: %s" % userGamesCatalogueFile)
				catalogueConfigParser = ConfigParser.ConfigParser()
				catalogueConfigParser.read(userGamesCatalogueFile)
				
				for section in catalogueConfigParser.sections():
					if catalogueConfigParser.has_option(section, 'full_name'):
						fullName = catalogueConfigParser.get(section, 'full_name')
						logging.debug("inserting game into catalogue: %s -> %s" % (section, fullName))
						cur.execute('INSERT INTO `games_catalogue` (`short_name`, `full_name`) VALUES ("%s", "%s");' % (section, fullName))
					else:
						logging.error("games catalogue section \"%s\" has no \"full_name\" option!" % section)
						
			con.commit()
		except sqlite3.Error, e:
			pesExit("Error: %s" % e.args[0], True)
		finally:
			if con:
				con.close()
		
		# read in console settings
		consoles = []
		configParser = ConfigParser.ConfigParser()
		configParser.read(userConsolesConfigFile)
		supportedConsoles = configParser.sections()
		supportedConsoles.sort()
		for c in supportedConsoles:
			# check the console definition from the config file
			try:
				consolePath = romsDir + os.sep + c
				mkdir(consolePath)
				consoleCoverartDir = coverartDir + os.sep + c
				mkdir(consoleCoverartDir)
				extensions = configParser.get(c, 'extensions').split(' ')
				command = configParser.get(c, 'command').replace('%%BASE%%', baseDir)
				consoleImg = configParser.get(c, 'image').replace('%%BASE%%', baseDir)
				emulator = configParser.get(c, 'emulator')
				checkFile(consoleImg)
				nocoverart = configParser.get(c, 'nocoverart').replace('%%BASE%%', baseDir)
				checkFile(nocoverart)
				consoleApiId = configParser.getint(c, 'api_id')
				consoleId = None
				# have we already saved this console to the database?
				try:
					con = sqlite3.connect(userPesDb)
					con.row_factory = sqlite3.Row
					cur = con.cursor()
					cur.execute('SELECT `console_id` FROM `consoles` WHERE `name` = "%s";' % c)
					row = cur.fetchone()
					if row:
						consoleId = int(row['console_id'])
				except sqlite3.Error, e:
					pesExit("Error: %s" % e.args[0], True)
				finally:
					if con:
						con.close()
				
				console = Console(c, consoleId, consoleApiId, extensions, consolePath, command, userPesDb, consoleImg, nocoverart, consoleCoverartDir, emulator)
				if configParser.has_option(c, 'ignore_roms'):
					for r in configParser.get(c, 'ignore_roms').split(','):
						console.addIgnoreRom(r.strip())
				if console.isNew():
					console.save()
				consoles.append(console)
			except ConfigParser.NoOptionError, e:
				pesExit('Error parsing config file %s: %s' % (userConsolesConfigFile, e.message), True)
		
		logging.info("loading GUI...")
		app = PESApp(dimensions, fontFile, backgroundColour, menuBackgroundColour, headerBackgroundColour, lineColour, textColour, menuTextColour, menuSelectedTextColour, consoles)
		app.run()
	except Exception, e:
		logging.exception(e)
		sys.exit(1)