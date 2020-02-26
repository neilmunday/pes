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

"""
This script initialises the PES database with console and game
data for use by PES.

By creating a cache of game data this aids adding user games to
the database.
"""

import argparse
import configparser
import json
import pes
import pes.retroachievement
from pes.common import checkDir, checkFile, pesExit, ConsoleSettings
import pes.sql
import logging
from sqlalchemy.orm import sessionmaker

import os
import sys

if __name__ == "__main__":

	parser = argparse.ArgumentParser(description='Script to pre-populate PES database', add_help=True)
	parser.add_argument('-v', '--verbose', help='Turn on debug messages', dest='verbose', action='store_true')
	parser.add_argument('-f', '--force', help='If database already exists, delete it', dest='force', action='store_true')
	parser.add_argument('-d', '--data-dir', dest='dataDir', help='Path to data directory', required=True)
	parser.add_argument('-l', '--log', help='File to log messages to', type=str, dest='logfile')
	parser.add_argument('-u', '--update', dest='update', help='Update cached data', action='store_true')
	args = parser.parse_args()

	logLevel = logging.INFO
	if args.verbose:
		logLevel = logging.DEBUG

	if args.logfile:
		logging.basicConfig(format='%(asctime)s:%(levelname)s: %(message)s', datefmt='%Y/%m/%d %H:%M:%S', level=logLevel, filename=args.logfile)
	else:
		logging.basicConfig(format='%(asctime)s:%(levelname)s: %(message)s', datefmt='%Y/%m/%d %H:%M:%S', level=logLevel)

	checkDir(args.dataDir)
	pesDb = os.path.join(args.dataDir, 'pes.db')

	if os.path.exists(pesDb):
		if not args.force:
			pesExit("%s already exists, use --force to delete database first" % pesDb, True)
		logging.info("deleting %s" % pesDb)
		os.remove(pesDb)

	consoleJSON = os.path.join(args.dataDir, "consoles.json")
	checkFile(consoleJSON)

	mameJSON = os.path.join(args.dataDir, "mame.json")
	checkFile(mameJSON)

	retroGameJSON = os.path.join(args.dataDir, "retro_games.json")

	logging.debug("connecting to database: %s" % pesDb)
	engine = pes.sql.connect(pesDb)
	session = sessionmaker(bind=engine)()
	pes.sql.createAll(engine)

	logging.info("loading MAME dictionary from: %s" % mameJSON)
	with open(mameJSON, 'r') as f:
		data = json.load(f)
		for mame in data["games"]:
			game = pes.sql.MameGame(name=mame["name"], shortName=mame["shortname"])
			session.add(game)
	session.commit()
	logging.info("MAME dictionary saved to database")

	retroJSONCache = None
	if not args.update:
		if os.path.exists(retroGameJSON):
			with open(retroGameJSON, "r") as f:
				retroJSONCache = json.load(f)
		else:
			pesExit("%s does not exist" % retroGameJSON)

	logging.info("loading console definitions from: %s" % consoleJSON)
	with open(consoleJSON, 'r') as consoleJSONFile:
		consoleData = json.load(consoleJSONFile)
		consoleRetroIds = []
		retroDic = {}
		for c in consoleData["consoles"]:
			logging.info("processing: %s" % c["name"])
			if "retroId" in c and c["retroId"] not in consoleRetroIds:
				consoleRetroIds.append(c["retroId"])
				retroDic[c["retroId"]] = []
				logging.info("gathering game data for %s from RetroAchievements.org..." % c["name"])
				console = pes.sql.Console(name=c["name"], gamesDbId=c["gamesDbId"], retroId=c["retroId"])
				session.add(console)
				session.commit() # force console's ID to be generated
				if args.update:
					for gameId, data in pes.retroachievement.getGameHashes(int(c["retroId"])).items():
						retroDic[c["retroId"]].append({"id": gameId, "rasum": data["hash"], "name": data["name"]})
						retroGame = pes.sql.RetroAchievementGame(id=gameId, rasum=data["hash"], name=data["name"], consoleId=console.id)
						session.add(retroGame)
						logging.info("added: %s" % retroGame.name)
				else:
					for retroGame in retroJSONCache[str(c["retroId"])]:
						retroGame = pes.sql.RetroAchievementGame(id=retroGame["id"], rasum=retroGame["rasum"], name=retroGame["name"], consoleId=console.id)
						session.add(retroGame)
						logging.info("added from cache: %s" % retroGame.name)
			else:
				console = pes.sql.Console(name=c["name"], gamesDbId=c["gamesDbId"])
				session.add(console)
		if args.update:
			logging.info("saving RetroAchievement game info to: %s" % retroGameJSON)
			with open(retroGameJSON, "w") as retroGameJSONFile:
				retroGameJSONFile.write("%s\n" % json.dumps(retroDic))
	session.commit()

	#consoles = session.query(pes.sql.Console).all()
	#for c in consoles:
	#	print(c.name)
	#	print(c.retrogames)
