#!/usr/bin/env python3

import argparse
import datetime
import logging
import pes
from pes.common import *
from pes.gui import BackEnd, PESGuiApplication
import sdl2

if __name__ == "__main__":

	parser = argparse.ArgumentParser(description='Launch the Pi Entertainment System (PES)', add_help=True)
	parser.add_argument('-w', '--window', help='Run PES in a window', dest='window', action='store_true')
	parser.add_argument('-v', '--verbose', help='Turn on debug messages', dest='verbose', action='store_true')
	parser.add_argument('-l', '--log', help='File to log messages to', type=str, dest='logfile')
	parser.add_argument('-p', '--profile', help='Turn on profiling', dest='profile', action='store_true')
	args = parser.parse_args()

	logLevel = logging.INFO
	if args.verbose:
		logLevel = logging.DEBUG

	if args.logfile:
		logging.basicConfig(format='%(asctime)s:%(levelname)s: %(message)s', datefmt='%Y/%m/%d %H:%M:%S', level=logLevel, filename=args.logfile)
	else:
		logging.basicConfig(format='%(asctime)s:%(levelname)s: %(message)s', datefmt='%Y/%m/%d %H:%M:%S', level=logLevel)

	logging.debug("PES %s, date: %s, author: %s" % (pes.VERSION_NUMBER, pes.VERSION_DATE, pes.VERSION_AUTHOR))
	logging.debug("base dir: %s" % pes.baseDir)
	checkDir(pes.baseDir)
	checkFile(pes.qmlMain)
	checkDir(pes.qmlDir)
	logging.debug("config dir: %s" % pes.confDir)
	checkDir(pes.confDir)
	logging.debug("user dir: %s" % pes.userDir)
	mkdir(pes.userDir)
	mkdir(pes.userBiosDir)
	mkdir(pes.userConfDir)
	mkdir(pes.userRetroArchConfDir)
	mkdir(pes.userRetroArchJoysticksConfDir)
	mkdir(pes.userViceConfDir)
	initConfig()

	checkFile(pes.userPesConfigFile)
	checkFile(pes.userGamesCatalogueFile)
	checkFile(pes.userConsolesConfigFile)
	checkFile(pes.userGameControllerFile)
	checkFile(pes.rasumExe)

	logging.info("loading settings...")
	checkFile(pes.userPesConfigFile)
	settings = Settings()
	covertArtDir = settings.get("settings", "coverartDir")
	if covertArtDir == None:
		pesExit("Could not find \"coverartDir\" parameter in \"settings\" section in %s" % pes.userPesConfigFile)
	logging.debug("cover art dir: %s" % covertArtDir)
	mkdir(covertArtDir)
	badgeDir = settings.get("settings", "badgeDir")
	if badgeDir == None:
		pesExit("Could not find \"badgeDir\" parameter in \"settings\" section in %s" % pes.userPesConfigFile)
	logging.debug("badge dir: %s" % badgeDir)
	mkdir(badgeDir)
	romsDir = settings.get("settings", "romsDir")
	if romsDir == None:
		pesExit("Could not find \"romsDir\" parameter in \"settings\" section in %s" % pes.userPesConfigFile)
	logging.debug("ROMs dir: %s" % romsDir)
	mkdir(romsDir)

	romScraper = settings.get("settings", "romScraper")
	if romScraper == None:
		logging.warning("Could not find \"romScraper\" parameter in \"settings\" section in %s. Will use \"%s\" for this session." % (userPesConfigFile, romScrapers[0]))
		settings.set("settings", "romScraper", romScrapers[0])
	elif romScraper not in pes.romScrapers:
		logging.error("Unknown romScraper value: \"%s\" in \"settings\" section in %s. Will use \"%s\" instead for this session." % (romScraper, userPesConfigFile, romScrapers[0]))

	if sdl2.SDL_Init(sdl2.SDL_INIT_JOYSTICK | sdl2.SDL_INIT_GAMECONTROLLER) != 0:
		pesExit("Failed to initialise SDL")

	logging.debug("loading SDL2 control pad mappings from: %s" % pes.userGameControllerFile)
	mappingsLoaded = sdl2.SDL_GameControllerAddMappingsFromFile(pes.userGameControllerFile.encode())
	if mappingsLoaded == -1:
		pes.common.pesExit("failed to load SDL2 control pad mappings from: %s" % pes.userGameControllerFile)
	logging.debug("loaded %d control pad mappings" % mappingsLoaded)

	app = PESGuiApplication(sys.argv)
	app.run()
