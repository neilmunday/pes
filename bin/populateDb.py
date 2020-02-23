#!/usr/bin/env python3

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

import argparse
import configparser
import pes
import pes.retroachievement
from pes.common import pesExit, ConsoleSettings
import pes.sql
import logging
from sqlalchemy.orm import sessionmaker

import os
import sys

if __name__ == "__main__":

	parser = argparse.ArgumentParser(description='Script to pre-populate PES database', add_help=True)
	parser.add_argument('-v', '--verbose', help='Turn on debug messages', dest='verbose', action='store_true')
	parser.add_argument('-f', '--force', help='If database already exists, delete it', dest='force', action='store_true')
	parser.add_argument('-c', '--console-config', dest='consoleConfig', help='Path to consoles.ini', required=True)
	parser.add_argument('-l', '--log', help='File to log messages to', type=str, dest='logfile')
	args = parser.parse_args()

	logLevel = logging.INFO
	if args.verbose:
		logLevel = logging.DEBUG

	if args.logfile:
		logging.basicConfig(format='%(asctime)s:%(levelname)s: %(message)s', datefmt='%Y/%m/%d %H:%M:%S', level=logLevel, filename=args.logfile)
	else:
		logging.basicConfig(format='%(asctime)s:%(levelname)s: %(message)s', datefmt='%Y/%m/%d %H:%M:%S', level=logLevel)

	if os.path.exists(pes.userDb):
		if not args.force:
			pesExit("%s already exists, use --force to delete database first" % pes.userDb, True)
		logging.info("deleting %s" % pes.userDb)
		os.remove(pes.userDb)

	if not os.path.exists(args.consoleConfig):
		pesExit("%s does not exist" % args.consoleConfig)

	logging.debug("connecting to database: %s" % pes.userDb)
	engine = pes.sql.connect()
	session = sessionmaker(bind=engine)()
	pes.sql.createAll(engine)

	logging.info("loading console definitions from: %s" % args.consoleConfig)
	consoleSettings = ConsoleSettings(args.consoleConfig)

	consoleRetroIds = []

	for c in consoleSettings.getSections():
		logging.debug("processing: %s" % c)
		options = consoleSettings.getOptions(c)
		if "achievement_id" in options and options["achievement_id"] not in consoleRetroIds:
			consoleRetroIds.append(options["achievement_id"])
			logging.info("gathering game data from RetroAchievements.org...")
			console = pes.sql.Console(name=c, gamesDbId=options["thegamesdb_id"], retroId=options["achievement_id"])
			session.add(console)
			session.commit() # force console's ID to be generated
			for gameId, data in pes.retroachievement.getGameHashes(int(options["achievement_id"])).items():
				retroGame = pes.sql.RetroAchievementGame(id=gameId, rasum=data['hash'], name=data['name'], consoleId=console.id)
				session.add(retroGame)
				logging.info("added: %s" % data['name'])
		else:
			console = pes.sql.Console(name=c, gamesDbId=options["thegamesdb_id"])
			session.add(console)

	session.commit()
