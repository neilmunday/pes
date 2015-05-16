#
#    This file is part of the Pi Entertainment System (PES).
#
#    PES provides an interactive GUI for games console emulators
#    and is designed to work on the Raspberry Pi.
#
#    Copyright (C) 2014 Neil Munday (neil@mundayweb.com)
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
import sys
import math
import threading
import pygame
import ConfigParser
from pygame.locals import *
from datetime import datetime
import time
import glob
import subprocess
import sqlite3
import urllib
import urllib2
import csv
import socket
import fcntl
import struct
from PIL import Image
from collections import OrderedDict
from Levenshtein import *
from xml.etree import ElementTree
from xml.etree.ElementTree import Element, SubElement
import logging

# HDMI-CEC codes
CEC_UP = 1
CEC_DOWN = 2
CEC_LEFT = 3
CEC_RIGHT = 4
CEC_ENTER = 0
CEC_EXIT = 13
CEC_RETURN = 145

# PES event codes
EVENT_DATABASE_UPDATED = 1
EVENT_JOYSTICKS_UPDATED = 2
EVENT_MESSAGE_BOX_OK = 3
EVENT_LOAD_GAME_INFO = 4
EVENT_WARNING = 5

# axis codes used for event handling
AXIS_PRESSED = 1
AXIS_RELEASED = 2
AXIS_INITIALISED = 3

VERSION_NUMBER = '1.3 (development version)'
VERSION_DATE = '2015-05-16'
VERSION_AUTHOR = 'Neil Munday'

verbose = False

def get_default_if(): 
    f = open('/proc/net/route') 
    for i in csv.DictReader(f, delimiter="\t"): 
        if long(i['Destination'], 16) == 0: 
            return i['Iface'] 
    return None

def getHumanReadableSize(x):
	if x < 1024:
		return "%diB"
	if x < 1048576:
		return "%.1fKiB" % (x / 1024.0)
	if x < 1073741824:
		return "%.1fMiB" % (x / 1048576.0)
	return "%.1fGiB" % (x / 1073741824.0)

def get_ip_address(ifname): 
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) 
    return socket.inet_ntoa(fcntl.ioctl(s.fileno(), 0x8915, struct.pack('256s', ifname[:15]))[20:24])

def scaleImage(img, (bx,by)):
	"""
	Original author: Frank Raiser (crashchaos@gmx.net)
	URL: http://www.pygame.org/pcr/transform_scale
	Modified by Neil Munday
	"""
	ix, iy = img.get_size()
	if ix > iy:
		# fit to width
		scale_factor = bx/float(ix)
		sy = scale_factor * iy
		if sy > by:
			scale_factor = by/float(iy)
			sx = scale_factor * ix
			sy = by
		else:
			sx = bx
	else:
		# fit to height
		scale_factor = by/float(iy)
        	sx = scale_factor * ix
		if sx > bx:
			scale_factor = bx/float(ix)
			sx = bx
			sy = scale_factor * iy
		else:
			sy = by
	return pygame.transform.scale(img, (int(sx),int(sy)))

#
#	StringMatcher class sourced from https://github.com/ztane/python-Levenshtein/blob/master/StringMatcher.py
#	Author: Antti Haapala <antti@haapala.name>
#
class StringMatcher:
    """A SequenceMatcher-like class built on the top of Levenshtein"""

    def _reset_cache(self):
        self._ratio = self._distance = None
        self._opcodes = self._editops = self._matching_blocks = None

    def __init__(self, seq1='', seq2=''):
        self._str1, self._str2 = seq1, seq2
        self._reset_cache()

    def set_seqs(self, seq1, seq2):
        self._str1, self._str2 = seq1, seq2
        self._reset_cache()

    def set_seq1(self, seq1):
        self._str1 = seq1
        self._reset_cache()

    def set_seq2(self, seq2):
        self._str2 = seq2
        self._reset_cache()

    def get_opcodes(self):
        if not self._opcodes:
            if self._editops:
                self._opcodes = opcodes(self._editops, self._str1, self._str2)
            else:
                self._opcodes = opcodes(self._str1, self._str2)
        return self._opcodes

    def get_editops(self):
        if not self._editops:
            if self._opcodes:
                self._editops = editops(self._opcodes, self._str1, self._str2)
            else:
                self._editops = editops(self._str1, self._str2)
        return self._editops

    def get_matching_blocks(self):
        if not self._matching_blocks:
            self._matching_blocks = matching_blocks(self.get_opcodes(),
                                                    self._str1, self._str2)
        return self._matching_blocks

    def ratio(self):
        if not self._ratio:
            self._ratio = ratio(self._str1, self._str2)
        return self._ratio

    def quick_ratio(self):
        # This is usually quick enough :o)
        if not self._ratio:
            self._ratio = ratio(self._str1, self._str2)
        return self._ratio

    def real_quick_ratio(self):
        len1, len2 = len(self._str1), len(self._str2)
        return 2.0 * min(len1, len2) / (len1 + len2)

    def distance(self):
        if not self._distance:
            self._distance = distance(self._str1, self._str2)
        return self._distance

class PES(object):

	def __init__(self, window, commandFile):
		self.__fontColour = (255, 255, 0)
		self.__bgColour = (0, 0, 0)
		self.__screenMarginLeft = 30
		self.__screenMarginRight = 30
		self.__screenMarginTop = 20
		self.__screenMarginBottom = 20
		self.__headerHeight = 30
		self.__footerHeight = 30
		self.__headerMaginBottom = 30
		self.__name = 'Pi Entertainment System'
		self.__temp = 0

		# work out IP
		self.__ip = None 
		defaultInterface = get_default_if()
		if defaultInterface:
			self.__ip = get_ip_address(defaultInterface)
		if self.__ip == None:
			self.__ip = '127.0.0.1'

		# do sanity checks first before we draw the screen
		self.__userDir = os.path.expanduser('~') + os.sep + '.pes'
		self.__userDb = self.__userDir + os.sep + 'pes.db'
		self.__imgCacheDir = self.__userDir + os.sep + 'cache'
		self.__baseDir = os.path.abspath(os.path.dirname(os.path.realpath(__file__)) + os.sep + '../')
		self.__confDir = self.__baseDir + os.sep + 'conf.d' + os.sep + 'pes'
		self.__checkDir(self.__confDir)
		self.__retroarchJoysticksDir = self.__baseDir + os.sep + 'conf.d' + os.sep + 'retroarch' + os.sep + 'joysticks'
		self.__mupen64plusConfigFile = self.__baseDir + os.sep + 'conf.d' + os.sep + 'mupen64plus' + os.sep + 'mupen64plus.cfg'
		self.__pesConfigFile = self.__confDir + os.sep + 'pes.ini'
		self.__checkFile(self.__pesConfigFile)
		self.__consolesConfigFile = self.__confDir + os.sep + 'consoles.ini'
		self.__checkFile(self.__consolesConfigFile)
		self.__joysticksConfigFile = self.__confDir + os.sep + 'joysticks.ini'
                self.__checkFile(self.__joysticksConfigFile)
		self.__commandFile = commandFile

		# read in program settings
		configParser = ConfigParser.ConfigParser()
		configParser.read(self.__pesConfigFile)
		try:
			self.__fontFile = os.path.abspath(self.__baseDir + os.sep + configParser.get('pes', 'fontFile'))
			self.__romsDir = configParser.get('pes', 'romsDir')
			self.__favImage = os.path.abspath(self.__baseDir + os.sep + configParser.get('pes', 'favImage'))
			self.__rebootCommand = configParser.get('pes', 'rebootCommand')
			self.__shutdownCommand = configParser.get('pes', 'shutdownCommand')
			self.__tempCommand = configParser.get('pes', 'tempCommand')
			#self.__gamesCatalogueFile = configParser.get('pes', 'gamesCatalogueFile')
		except ConfigParser.NoOptionError, e:
			self.__exit('Error parsing config file %s: %s' % (self.__pesConfigFile, e.message), True)
		
		self.__checkFile(self.__favImage)
		self.__checkFile(self.__fontFile)
		self.__checkDir(self.__romsDir)
		#self.__checkFile(self.__gamesCatalogueFile)

		# check for user settings
		if not os.path.exists(self.__userDir):
			os.mkdir(self.__userDir)
		elif not os.path.isdir(self.__userDir):
			self.__exit("Error: %s is not a directory!" % self.__userDir, True)
		elif not os.access(self.__userDir, os.W_OK):
			self.__exit("Error: %s is not writable!" % self.__userDir, True)

		if not os.path.exists(self.__imgCacheDir):
			os.mkdir(self.__imgCacheDir)
		elif not os.path.isdir(self.__imgCacheDir):
			self.__exit("Error: %s is not a directory!" % self.__imgCacheDir, True)
		elif not os.access(self.__imgCacheDir, os.W_OK):
			self.__exit("Error: %s is not writable!" % self.__imgCacheDir, True)

		# check for retroarch joysticks autoconfig dir
		if not os.path.exists(self.__retroarchJoysticksDir):
			os.mkdir(self.__retroarchJoysticksDir)
		elif not os.path.isdir(self.__retroarchJoysticksDir):
			self.__exit("Error: %s is not a directory!" % self.__retroarchJoysticksDir, True)
		elif not os.access(self.__retroarchJoysticksDir, os.W_OK):
			self.__exit("Error: %s is not writeable!" % self.__retroarchJoysticksDir, True)

		# create database (if needed)
		logging.debug('connecting to database: %s' % self.__userDb)
		try:
			con = sqlite3.connect(self.__userDb)
			con.row_factory = sqlite3.Row
			cur = con.cursor()
			cur.execute('CREATE TABLE IF NOT EXISTS `games`(`game_id` INTEGER PRIMARY KEY, `api_id` INT, `exists` INT, `console_id` INT, `name` TEXT, `cover_art` TEXT, `game_path` TEXT, `overview` TEXT, `released` INT, `last_played` INT, `favourite` INT(1), `play_count` INT, `size` INT )')
			cur.execute('CREATE INDEX IF NOT EXISTS "games_index" on games (game_id ASC)')
			cur.execute('CREATE TABLE IF NOT EXISTS `consoles`(`console_id` INTEGER PRIMARY KEY, `api_id` INT, `name` TEXT)')
			cur.execute('CREATE INDEX IF NOT EXISTS "console_index" on consoles (console_id ASC)')
			#cur.execute('CREATE TABLE IF NOT EXISTS `games_catalogue` (`short_name` TEXT, `full_name` TEXT)')
			#cur.execute('CREATE INDEX IF NOT EXISTS "games_catalogue_index" on games_catalogue (short_name ASC)')
			
			# is the games catalogue populated?
			#cur.execute('SELECT COUNT(*) AS `total` FROM `games_catalogue`')
			#row = cur.fetchone()
			#if row['total'] == 0:
			#	logging.info("populating games catalogue...")
			#	with open(self.__gamesCatalogueFile, 'r') as f:
			#		for line in f:
			#			fields = line.replace("\n", "").split('|')
			#			if len(fields) == 2:
			#				logging.debug("inserting game: %s -> %s" % (fields[0], fields[1]))
			#				cur.execute('INSERT OR REPLACE INTO `games_catalogue` (`short_name`, `full_name`) VALUES ("%s", "%s")' % (fields[0], fields[1]))		
			con.commit()
		except sqlite3.Error, e:
			self.__exit("Error: %s" % e.args[0], True)
		finally:
			if con:
				con.close()

		# read in console settings
		self.__consoles = [] # list of console objects
		configParser = ConfigParser.ConfigParser()
		configParser.read(self.__consolesConfigFile)
		self.__supportedConsoles = configParser.sections()
		self.__supportedConsoles.sort()
		for c in self.__supportedConsoles:
			# check the console definition from the config file
			try:
				consolePath = self.__romsDir + os.sep + c
				if not os.path.exists(consolePath):
					logging.debug("%s does not exist, creating..." % consolePath)
					os.mkdir(consolePath)
				extensions = configParser.get(c, 'extensions').split(' ')
				command = configParser.get(c, 'command').replace('%%BASE%%', self.__baseDir)
				consoleImg = configParser.get(c, 'image').replace('%%BASE%%', self.__baseDir)
				emulator = configParser.get(c, 'emulator')
				self.__checkFile(consoleImg)
				nocoverart = configParser.get(c, 'nocoverart').replace('%%BASE%%', self.__baseDir)
				self.__checkFile(nocoverart)
				consoleApiId = configParser.getint(c, 'api_id')
				consoleId = None
				# have we already saved this console to the database?
				try:
					con = sqlite3.connect(self.__userDb)
					con.row_factory = sqlite3.Row
					cur = con.cursor()
					cur.execute('SELECT `console_id` FROM `consoles` WHERE `name` = "%s";' % c)
					row = cur.fetchone()
					if row:
						consoleId = int(row['console_id'])
				except sqlite3.Error, e:
					self.__exit("Error: %s" % e.args[0], True)
				finally:
					if con:
						con.close()
				
				console = Console(c, consoleId, consoleApiId, extensions, consolePath, command, self.__userDb, consoleImg, nocoverart, self.__imgCacheDir, emulator)
				if console.isNew():
					console.save()
				self.__consoles.append(console)
			except ConfigParser.NoOptionError, e:
				self.__exit('Error parsing config file %s: %s' % (self.__pesConfigFile, e.message), True)

		# set-up pygame display
		pygame.init()
		if window == False:
			self.__screen = pygame.display.set_mode((0,0), pygame.FULLSCREEN)
		else:
			self.__screen = pygame.display.set_mode((1024, 768))
			pygame.display.set_caption("PES")
		self.__screenWidth = self.__screen.get_rect().width
		self.__screenHeight = self.__screen.get_rect().height
		self.__clock = self.clock = pygame.time.Clock()

		# set-up header
		self.__header = Header(self.__name, self.__screenWidth - 10, self.__headerHeight, self.__fontFile, 18, self.__fontColour, self.__bgColour)
		self.__header.setActive(True)

		# set-up footer
		self.__footer = Footer(self.__screenWidth - 10, self.__footerHeight, self.__fontFile, 14, self.__fontColour, self.__bgColour)
		self.__footer.setField("IP", self.__ip)
		self.__footer.setActive(True)

		# load joysticks
		self.loadJoysticks()

		# generate retroarch joystick configs
		for j in self.__joysticks:
			joystickFile = self.__retroarchJoysticksDir + os.sep + j.getName() + '.cfg'
			if not os.path.exists(joystickFile):
				logging.debug("creating: %s" % joystickFile)
				with open(joystickFile, 'w') as f:
					f.write(j.getRetroArchConfig())

		# detect joysticks
		self.detectJoysticks()

		# read initial temperature
		self.__checkTemp()

		# create settings menu
		menuItems = [MenuItem("Configure Joystick", self.__loadJoyStickConfiguration), MenuItem("Reset Database", self.__resetDb)]
                self.__settingsMenu = Menu(menuItems, self.__screenWidth, self.__screenHeight - (self.__footerHeight + self.__headerHeight), self.__fontFile, 20, self.__fontColour, self.__bgColour, [self.__screenMarginLeft, self.__screenMarginRight, self.__screenMarginTop, self.__screenMarginBottom])

		# create about menu
		self.__aboutMenu = None

		# create game info panel
		self.__gameInfoPanel = None
		
		# create consoles menu
		consoleMenuItems = []
		for c in self.__consoles:
			gameTotal = c.getGameTotal()
			consoleMenuItems.append(MenuImgItem("%s (%d)" % (c.getName(), gameTotal), c.getImg(), self.__loadGamesMenu, c))
		self.__consolesMenu = ThumbnailMenu(consoleMenuItems, self.__screenWidth, self.__screenHeight - (self.__footerHeight + self.__headerHeight), self.__fontFile, 20, self.__fontColour, self.__bgColour)
		self.__consolesMenu.setTitle('Games')

		# create main menu
		menuItems = []
		menuItems.append(MenuItem("Games", self.__loadConsolesMenu))	
		menuItems.append(MenuItem('Update Database', self.__updateDb))
		menuItems.append(MenuItem("Settings", self.__loadSettingsMenu))
		menuItems.append(MenuItem("Reboot", self.__reboot))
		menuItems.append(MenuItem("Power Off", self.__poweroff))
		menuItems.append(MenuItem("About", self.__loadAboutMenu))
		menuItems.append(MenuItem("Exit to command line", self.__exit))

		self.__mainMenu = Menu(menuItems, self.__screenWidth, self.__screenHeight - (self.__footerHeight + self.__headerHeight), self.__fontFile, 20, self.__fontColour, self.__bgColour, [self.__screenMarginLeft, self.__screenMarginRight, self.__screenMarginTop, self.__screenMarginBottom])
		self.__menuStack = [self.__mainMenu]
		self.__mainMenu.setActive(True)

	def __checkDir(self, dir):
		if not os.path.exists(dir):
			self.__exit("Error: %s does not exist!" % dir, True)
		if not os.path.isdir(dir):
			self.__exit("Error: %s is not a directory!" % dir, True)

	def __checkFile(self, file):
		if not os.path.exists(file):
			self.__exit("Error: %s does not exist!" % file, True)
		if not os.path.isfile(file):
			self.__exit("Error: %s is not a file!" % file, True)

	def __checkTemp(self):
		try:
			logging.debug("checking temp...")
			temp = float(subprocess.check_output(self.__tempCommand, shell=True)[:-1])
			temp /= 1000
			if self.__temp != temp:
				self.__temp = temp
				self.__footer.setField("Temp", "%.2fC" % temp)
			
		except subprocess.CalledProcessError, e:
			logging.error("unable to check temperature: %s", e.args)

	def detectJoysticks(self):
		logging.debug("looking for joysticks...")
		if pygame.joystick.get_init():
			pygame.joystick.quit()
		pygame.joystick.init()

		self.__js = None # PyGame joystick object
		self.__joystick = None # PES joystick object
		self.__joystickTotal = pygame.joystick.get_count()
		self.__joysticksConnected = {} # stores a dictionary of connected joysticks that are *recognised by PES*, the key is the js number and the value is a JoyStick object
		logging.debug("found %d joystick(s)" % self.__joystickTotal)
		if self.__joystickTotal > 0:
			primaryFound = False
			for i in range(0, self.__joystickTotal):
				js = pygame.joystick.Joystick(i)
				js.init()
				jsName = js.get_name()
				jsIndex = js.get_id()
				logging.debug("joystick %d: %s" % (jsIndex, jsName))
				matchFound = False
				for j in self.__joysticks:
					if j.isMatch(jsName):
						matchFound = True
						logging.debug("joystick recognised: %s" % jsName)
						self.__joysticksConnected[jsIndex] = j
						if not primaryFound:
							logging.debug("primary joystick is joystick: %d, %s" % (jsIndex, jsName))
							self.__joystick = j
							self.__js = js
							primaryFound = True
							#break
				if not matchFound:
					logging.debug("joystick not recognised!")

		self.__footer.setField("JoySticks", self.__joystickTotal)
		if self.__joystick == None:
			self.__footer.setField("Primary Joystick", "Disabled")
		else:
			self.__footer.setField("Primary Joystick", "Pad %d" % (self.__js.get_id() + 1))

	def __exit(self, msg = None, error = False):
		if msg:
			logging.error(msg)
		if error:
			logging.error('error exit!')
			sys.exit(1)

		with open(self.__commandFile, 'w') as f:
			f.write('exit')
		sys.exit(0)

	def __getActiveMenu(self):
		return self.__menuStack[len(self.__menuStack) - 1]

	def __goBack(self):
		activeMenu = self.__getActiveMenu()
		activeMenu.setActive(False)
		self.__menuStack.pop()
		activeMenu = self.__getActiveMenu()
		activeMenu.setActive(True)
		if activeMenu == self.__mainMenu:
			self.__header.setTitle(self.__name)
		else:
			self.__header.setTitle("%s: %s" % (self.__name, activeMenu.getTitle()))

	def __loadAboutMenu(self):
		if self.__aboutMenu == None:
			self.__aboutMenu = AboutPanel(self.__screenWidth, self.__screenHeight - (self.__footerHeight + self.__headerHeight), self.__fontFile, 18, self.__fontColour, self.__bgColour, [self.__screenMarginLeft, self.__screenMarginRight, self.__screenMarginTop, self.__screenMarginBottom])
		activeMenu = self.__getActiveMenu()
		activeMenu.setActive(False)
		activeMenu = self.__aboutMenu
		activeMenu.setActive(True)
		self.__menuStack.append(activeMenu)
		self.__header.setTitle('%s: %s' % (self.__name, activeMenu.getTitle()))

	def __loadConsolesMenu(self):
		activeMenu = self.__getActiveMenu()
		activeMenu.setActive(False)
		activeMenu = self.__consolesMenu
		activeMenu.setActive(True)
		self.__menuStack.append(activeMenu)
		self.__header.setTitle('%s: %s' % (self.__name, activeMenu.getTitle()))

	def __loadGameInfoPanel(self, console, game):
		activeMenu = self.__getActiveMenu()
		activeMenu.setActive(False)
		if self.__gameInfoPanel == None:
			self.__gameInfoPanel = GameInfoPanel(self.__screenWidth, self.__screenHeight - (self.__footerHeight + self.__headerHeight), self.__fontFile, 18, self.__fontColour, self.__bgColour, console, game, [self.__screenMarginLeft, self.__screenMarginRight, self.__screenMarginTop, self.__screenMarginBottom])
			activeMenu = self.__gameInfoPanel
		else:
			activeMenu = self.__gameInfoPanel
			self.__gameInfoPanel.setGame(console, game)
		activeMenu.setActive(True)
		self.__menuStack.append(activeMenu)
		self.__header.setTitle('%s: %s' % (self.__name, self.__gameInfoPanel.getTitle()))

	def __loadGamesMenu(self, args):
		console = args[0]
		console.refresh()
		if console.getGameTotal() > 0:
			activeMenu = self.__getActiveMenu()
			activeMenu.setActive(False)
			activeMenu = GamesMenu(console, self.__screenWidth, self.__screenHeight - (self.__footerHeight + self.__headerHeight), self.__fontFile, 18, self.__fontColour, self.__bgColour, self.__favImage)
			activeMenu.addListener(self)
			activeMenu.setActive(True)
			self.__menuStack.append(activeMenu)
			self.__header.setTitle('%s: %s' % (self.__name, activeMenu.getTitle()))
		else:
			self.__showMessageBox('No games have been added for %s' % console.getName())

	def loadJoysticks(self):
		self.__joysticks = []
		configParser = ConfigParser.ConfigParser()
		configParser.read(self.__joysticksConfigFile)
		for j in configParser.sections():
			self.__joysticks.append(JoyStick(j, configParser.items(j)))

	def __loadJoyStickConfiguration(self):
		activeMenu = self.__getActiveMenu()
		activeMenu.setActive(False)
		activeMenu = JoyStickConfigurationPanel(self.__screenWidth, self.__screenHeight - (self.__footerHeight + self.__headerHeight), self.__fontFile, 18, self.__fontColour, self.__bgColour, self.__joysticksConfigFile, self.__retroarchJoysticksDir)
		activeMenu.setActive(True)
		activeMenu.addListener(self)
		activeMenu.setActive(True)
		self.__menuStack.append(activeMenu)
		self.__header.setTitle('%s: %s' % (self.__name, 'JoyStick Configuration'))

	def __loadSettingsMenu(self):
                activeMenu = self.__getActiveMenu()
		activeMenu.setActive(False)
		activeMenu = self.__settingsMenu
		activeMenu.setActive(True)
		self.__menuStack.append(activeMenu)
		self.__header.setTitle('%s: Settings' % self.__name)

	def __poweroff(self):
                logging.info("shutting down...")
                subprocess.call(self.__shutdownCommand, shell=True)

        def __reboot(self):
                logging.info("rebooting...")
                subprocess.call(self.__rebootCommand, shell=True)

	def handleCecEvent(self, event, args):
		btn = args[0]
		dur = args[1]

		if dur == 0:
			if btn == CEC_DOWN:
				pygame.event.post(pygame.event.Event(KEYDOWN, {'key': K_DOWN}))
			elif btn == CEC_UP:
				pygame.event.post(pygame.event.Event(KEYDOWN, {'key': K_UP}))
			elif btn == CEC_RIGHT:
				pygame.event.post(pygame.event.Event(KEYDOWN, {'key': K_RIGHT}))
			elif btn == CEC_LEFT:
				pygame.event.post(pygame.event.Event(KEYDOWN, {'key': K_LEFT}))
			elif btn == CEC_ENTER:
				pygame.event.post(pygame.event.Event(KEYDOWN, {'key': K_RETURN}))
			elif btn == CEC_EXIT:
				#pygame.event.post(pygame.event.Event(KEYDOWN, {'key': K_ESCAPE}))
				pygame.event.post(pygame.event.Event(KEYDOWN, {'key': K_BACKSPACE}))
		elif dur == 500:
			if btn == CEC_RETURN:
				pygame.event.post(pygame.event.Event(KEYDOWN, {'key': K_BACKSPACE}))

	def processEvent(self, event, args=None):
		if event == EVENT_DATABASE_UPDATED:
			logging.debug("trapping PES event: database update")
			i = 0
			for c in self.__consoles:
				#c.getGames()
				self.__consolesMenu.setLabelText(i, "%s (%d)" % (c.getName(), c.getGameTotal()))
				i += 1
			
		elif event == EVENT_JOYSTICKS_UPDATED:
			self.loadJoysticks()
			self.detectJoysticks()
		elif event == EVENT_MESSAGE_BOX_OK:
			logging.debug("trapping PES event: Message Box OK")
			self.__getActiveMenu().removeListener(self)
			self.__goBack()
		elif event == EVENT_LOAD_GAME_INFO:
			logging.debug("trapping PES event: load game info for game: %d" % args[0].getId())
			self.__loadGameInfoPanel(args[0], args[1])
		elif event == EVENT_WARNING:
			logging.debug("trapping PES event: warning with message \"%s\"" % args[0])
			self.__showMessageBox(args[0])

	def __resetDb(self):
		con = sqlite3.connect(self.__userDb)
		try:
			cur = con.cursor()
			cur.execute('DELETE FROM `games`;')
			cur.execute('VACUUM;')
		except sqlite3.Error, e:
			self.__exit("Error: %s" % e.args[0], True)
		finally:
			if con:
				con.close()

		self.__showMessageBox("Database reset to defaults!")

		self.processEvent(EVENT_DATABASE_UPDATED)
			
	def run(self):
		pygame.mouse.set_visible(False)
		fps = 60
		ok = True
		rtn = None
		self.__screen.fill(self.__bgColour)
		frame = 0
		seconds = 0
		temp = '0C'

		while ok:
                        
			self.__clock.tick(fps)
			if frame == fps:
                                frame = 0
                                seconds += 1

                        if seconds == 10:
                                seconds = 0
                                self.detectJoysticks()
				self.__checkTemp()

			self.__header.draw(5, 0)

			activeMenu = self.__getActiveMenu()
			activeMenu.draw(0, self.__header.getHeight())

			self.__footer.draw(5, self.__screenHeight - self.__footerHeight)

			# handle pygame events
			for event in pygame.event.get():
				if event.type != pygame.KEYDOWN and event.type != pygame.JOYBUTTONDOWN and event.type != pygame.JOYAXISMOTION:
					pass
				elif event.type == pygame.QUIT:
					ok = False
				elif event.type == KEYDOWN:
					if event.key == K_ESCAPE:
						ok = False
					if event.key == K_BACKSPACE:
						if not activeMenu.isLocked() and len(self.__menuStack) > 1:
							self.__goBack()
					else:
						rtn = activeMenu.handleEvent(event)
						if rtn != None:
							ok = False
				elif activeMenu.handlesJoyStickEvents():
					activeMenu.handleEvent(event)
				elif self.__joystick and self.__js.get_id() == event.joy and (event.type == pygame.JOYBUTTONDOWN or event.type == pygame.JOYAXISMOTION):
					keyEvent = None
					if event.type == pygame.JOYAXISMOTION:
						keyEvent = self.__joystick.axisToKeyEvent(event)
					else:
						if self.__joystick.getButton(event.button) == JoyStick.BTN_EXIT:
							#ok = False
							pass
						elif self.__joystick.getButton(event.button) == JoyStick.BTN_B:
							if not activeMenu.isLocked() and len(self.__menuStack) > 1:
								self.__goBack()
						else:
							keyEvent = self.__joystick.buttonToKeyEvent(event.button)

					if keyEvent:
						rtn = activeMenu.handleEvent(keyEvent)
						if rtn != None:
							ok = False

                        frame += 1
			#pygame.display.update()
			pygame.display.flip()

		returnValue = None
			
		if rtn:
			(command, emulator) = rtn
			# hack for Mupen64plus joystick config update
			if emulator == 'Mupen64Plus':
				self.__updateMupen64plusConfig()
			returnValue = command
			
		pygame.display.quit()
		pygame.quit()
		return returnValue

	def __showMessageBox(self, message):
		activeMenu = self.__getActiveMenu()
		activeMenu.setActive(False)
		activeMenu = MessageBox(self.__screenWidth, self.__screenHeight - (self.__footerHeight + self.__headerHeight), self.__fontFile, 18, self.__fontColour, self.__bgColour, message)
		activeMenu.addListener(self)
		activeMenu.setActive(True)
		self.__menuStack.append(activeMenu)

	def __updateDb(self):
		activeMenu = self.__getActiveMenu()
		activeMenu.setActive(False)
		activeMenu = UpdateDbPanel(self.__screenWidth, self.__screenHeight - (self.__footerHeight + self.__headerHeight), self.__fontFile, 18, self.__fontColour, self.__bgColour, self.__userDb, self.__consoles, [self.__screenMarginLeft, self.__screenMarginRight, self.__screenMarginTop, self.__screenMarginBottom])
		activeMenu.addListener(self)
		activeMenu.setActive(True)
		self.__menuStack.append(activeMenu)
		self.__header.setTitle('%s: %s' % (self.__name, 'Update Database'))
		
	def __updateMupen64plusConfig(self):
		if self.__joystickTotal > 0 and os.path.exists(self.__mupen64plusConfigFile) and os.path.isfile(self.__mupen64plusConfigFile):
			logging.debug('loading Mupen64plus config file: %s' % self.__mupen64plusConfigFile)
			configParser = ConfigParser.SafeConfigParser()
			configParser.optionxform=str
			configParser.read(self.__mupen64plusConfigFile)
			if configParser.has_section('CoreEvents') and configParser.has_option('CoreEvents', 'Joy Mapping Stop'):
				exitBtn = self.__joystick.getButtonValue(JoyStick.BTN_EXIT)
				if exitBtn == None:
					msg = 'Warning: no exit button has been defined for %s!' % self.__joystick.getName()
					logging.info(msg)
					self.__showMessageBox(msg)
					configParser.set('CoreEvents', 'Joy Mapping Stop', '')
				else:
					configParser.set('CoreEvents', 'Joy Mapping Stop', 'J0B' + exitBtn)
				# loop through each joystick that is connected and save to button config file
				# note: max of 4 control pads for this emulator
				i = 0
				for jsNumber, js in self.__joysticksConnected.iteritems():
					jsName = js.getName()
					logging.debug('generating Mupen64Plus config for joystick %d: %s' % (jsNumber, jsName))
					section = 'Input-SDL-Control%d' % (i + 1)
					if configParser.has_section(section):
						configParser.set(section, 'device', str(i))
						configParser.set(section, 'name', '"%s"' % jsName)
						configParser.set(section, 'plugged', 'True')
						configParser.set(section, 'mouse', 'False')
						configParser.set(section, 'mode', '0') # this must be set to 0 for the following values to take effect
						configParser.set(section, 'DPad R', js.getMupen64PlusButtonValue(JoyStick.BTN_RIGHT))
						configParser.set(section, 'DPad L', js.getMupen64PlusButtonValue(JoyStick.BTN_LEFT))
						configParser.set(section, 'DPad D', js.getMupen64PlusButtonValue(JoyStick.BTN_DOWN))
						configParser.set(section, 'DPad U', js.getMupen64PlusButtonValue(JoyStick.BTN_UP))
						configParser.set(section, 'Start', js.getMupen64PlusButtonValue(JoyStick.BTN_START))
						configParser.set(section, 'Z Trig', js.getMupen64PlusButtonValue(JoyStick.BTN_SHOULDER_LEFT))
						configParser.set(section, 'B Button', js.getMupen64PlusButtonValue(JoyStick.BTN_Y))
						configParser.set(section, 'A Button', js.getMupen64PlusButtonValue(JoyStick.BTN_B))
						configParser.set(section, 'C Button R', js.getMupen64PlusButtonValue(JoyStick.BTN_RIGHT_AXIS_RIGHT))
						configParser.set(section, 'C Button L', js.getMupen64PlusButtonValue(JoyStick.BTN_RIGHT_AXIS_LEFT))
						configParser.set(section, 'C Button D', js.getMupen64PlusButtonValue(JoyStick.BTN_RIGHT_AXIS_DOWN))
						configParser.set(section, 'C Button U', js.getMupen64PlusButtonValue(JoyStick.BTN_RIGHT_AXIS_UP))
						configParser.set(section, 'R Trig', js.getMupen64PlusButtonValue(JoyStick.BTN_SHOULDER_LEFT2))
						configParser.set(section, 'L Trig', js.getMupen64PlusButtonValue(JoyStick.BTN_SHOULDER_RIGHT2))
						configParser.set(section, 'X Axis', js.getMupen64PlusButtonValue(JoyStick.BTN_LEFT_AXIS_LEFT))
						configParser.set(section, 'Y Axis', js.getMupen64PlusButtonValue(JoyStick.BTN_LEFT_AXIS_UP))
					
					if i == 3:
						break
					i += 1
					
				while i < 4:
					section = 'Input-SDL-Control%d' % (i + 1)
					if configParser.has_section(section):
						configParser.set(section, 'device', '-1') # no joystick connected
						configParser.set(section, 'name', '""')
					i += 3
				
				# and so begins some crap code to set empty values to "" as Python's ConfigParser strips these
				for s in configParser.sections():
					for k, v in configParser.items(s):
						if v == None or v == '':
							configParser.set(s, k, '""')
				
				logging.debug('saving Mupen64plus configuration: %s' % (self.__mupen64plusConfigFile))
				with open(self.__mupen64plusConfigFile, 'wb') as f:
					configParser.write(f)

class UpdateDbThread(threading.Thread):
	def __init__(self, db, consoles):
		threading.Thread.__init__(self)
		self.__db = db
		self.__consoles = consoles
		self.__progress = 'Initialising...'
		self.__downloading = ''
		self.__started = False
		self.__finished = False
		self.__stop = False
		logging.debug('UpdateDbThread created')

	def run(self):
		logging.debug('UpdateDbThread: started')
		self.__started = True
		url = 'http://thegamesdb.net/api/'

		headers = {'User-Agent': 'PES Scraper'}

		con = None
		cur = None

		try:
			con = sqlite3.connect(self.__db)
			con.row_factory = sqlite3.Row
			cur = con.cursor()
		except sqlite3.Error, e:
			if con:
				con.rollback()
			logging.error("Error: %s" % e.args[0])
			print "Error: %s" % e.args[0]
			sys.exit(1)

		for c in self.__consoles:
			consoleName = c.getName()
			consoleId = c.getId()

			urlLoaded = False
			consoleApiName = None

			try:
				# get API name for this console
				request = urllib2.Request("%sGetPlatform.php" % url, urllib.urlencode({ 'id':  c.getApiId() }), headers=headers)
				logging.debug('loading URL: %s?%s' % (request.get_full_url(), request.get_data()))
				response = urllib2.urlopen(request)
				urlLoaded = True
				xmlData = ElementTree.parse(response)
				consoleApiName = xmlData.find('Platform/Platform').text
				logging.debug("console API name: %s" % consoleApiName)
			except urllib2.URLError, e:
				logging.error("an error occurred whilst trying to open url: %s" % e.message)

			logging.debug('UpdateDbThread: processing games for %s' % consoleName)
			self.__progress = 'Processing games for %s' % consoleName

			if self.__stopCheck():
				return

			try:
				cur.execute('UPDATE `games` SET `exists` = 0 WHERE `console_id` = %d;' % consoleId)
				con.commit()

				for e in c.getExtensions():
					for f in glob.glob('%s%s*%s' % (c.getRomDir(), os.sep, e)):
						if os.path.isfile(f):

							if self.__stopCheck(con, cur):
								return

							name = os.path.split(c.getRomDir() + os.sep + f)[1]
							fileSize = os.path.getsize(f)
							for e in c.getExtensions():
								name = name.replace(e, '')

							self.__progress = 'Found game: %s' % name
							
							# look up name in games catalogue
							#cur.execute('SELECT `full_name` FROM `games_catalogue` WHERE `short_name` = "%s"' % name)
							#row = cur.fetchone()
							#if row:
							#	logging.debug("found match for %s in games catalogue: %s" % (name, row['full_name']))
							#	name = row['full_name']

							cur.execute('SELECT `game_id`, `name`, `cover_art`, `game_path`, `api_id` FROM `games` WHERE `game_path` = "%s";' % f)
							row = cur.fetchone()
							if row == None or (row['cover_art'] == "0" and row['api_id'] == -1):
								gameApiId = None
								bestName = name
								thumbPath = 0
								overview = ''
								released = -1
								if consoleApiName != None:
									self.__progress = 'Downloading data for game: %s' % name
									logging.debug('downloading game info for %s' % name)
									# now grab thumbnail
									obj = { 'name': '%s' % name, 'platform': consoleApiName }
									data = urllib.urlencode(obj)
									urlLoaded = False
									nameLower = name.lower()

									try:
										request = urllib2.Request("%sGetGamesList.php" % url, urllib.urlencode(obj), headers=headers)
										logging.debug('Loading URL: %s?%s' % (request.get_full_url(), request.get_data()))
										response = urllib2.urlopen(request)
										urlLoaded = True
									except urllib2.URLError, e:
										logging.error("an error occurred whilst trying to open url: %s" % e.message)

									if urlLoaded:
										bestResultDistance = -1
										xmlData = ElementTree.parse(response)
										for x in xmlData.findall("Game"):
											xname = x.find("GameTitle").text.encode('ascii', 'ignore')
											xid = int(x.find("id").text)
											logging.debug("potential result: %s (%d)" % (xname, xid))

											if xname.lower() == nameLower:
												logging.debug("exact match!")
												gameApiId = xid
												break

											stringMatcher = StringMatcher(str(nameLower), xname.lower())
											distance = stringMatcher.distance()
											logging.debug("string distance: %d" % distance)

											if bestResultDistance == -1 or distance < bestResultDistance:
												bestResultDistance = distance
												bestName = xname
												gameApiId = xid

								if self.__stopCheck(con, cur):
									return

								if gameApiId != None:
									self.__progress = 'Match found: %s' % bestName
									logging.debug("best match was: \"%s\" with a match rating of %d" % (bestName, bestResultDistance))
									urlLoaded = False
									try:
										request = urllib2.Request("%sGetGame.php" % url, urllib.urlencode({"id": gameApiId}), headers=headers)
										logging.debug('Loading URL: %s?%s' % (request.get_full_url(), request.get_data()))
										response = urllib2.urlopen(request)
										urlLoaded = True
									except urllib2.URLError, e:
										logging.debug("an error occurred whilst trying to open url: %s" % e.message)

									if urlLoaded:
										xmlData = ElementTree.parse(response)
										overviewElement = xmlData.find("Game/Overview")
										if overviewElement != None:
											overview = overviewElement.text.encode('ascii', 'ignore')
										releasedElement = xmlData.find("Game/ReleaseDate")
										if releasedElement != None:
											released = releasedElement.text.encode('ascii', 'ignore')
											# convert to Unix time stamp
											try:
												released = int(time.mktime(datetime.strptime(released, "%m/%d/%Y").timetuple()))
											except ValueError, e:
												# thrown if date is not valid
												logging.warning("release date: %s is not in m/d/Y format!" % released)
												released = -1
										boxartElement = xmlData.find("Game/Images/boxart[@side='front']")
										if boxartElement != None:
											imageSaved = False
											try:
												imgUrl = "http://thegamesdb.net/banners/%s" % boxartElement.text
												logging.debug("downloading cover art: %s" % imgUrl)
												self.__downloading = name
												self.__progress = 'Downloading cover art for %s' % name
												extension = imgUrl[imgUrl.rfind('.'):]
												thumbPath = c.getImgCacheDir() + os.sep + str(gameApiId) + extension
												request = urllib2.Request(imgUrl, headers=headers)
												response = urllib2.urlopen(request).read()
												output = open(thumbPath, 'wb')
												output.write(response)
												output.close()
												imageSaved = True
											except urllib2.URLError, e:
												logging.error("an error occurred whilst trying to open url: %s" % e.message)

											if imageSaved:
												# resize the image if it is too big
												img = Image.open(thumbPath)
												width, height = img.size
												if width > 300 or height > 300:
													# scale image
													self.__progress = 'Scaling cover art for %s' % name
													logging.debug("scaling image: %s" % thumbPath)
													ratio = min(float(400.0 / width), float(400.0 / height))
													newWidth = width * ratio
													newHeight = height * ratio
													img.thumbnail((newWidth, newHeight), Image.ANTIALIAS)
													img.save(thumbPath)
														
								else:
									self.__progress = 'Could not find game data for %s' % name
									logging.debug("could not find game info for %s " % name)
									gameApiId = -1

								if row == None:
									self.__progress = 'Adding %s to database...' % name
									logging.debug('inserting new game record into database...')
									cur.execute("INSERT INTO `games`(`exists`, `console_id`, `name`, `game_path`, `api_id`, `cover_art`, `overview`, `released`, `favourite`, `last_played`, `play_count`, `size`) VALUES (1, %d, '%s', '%s', %d, '%s', '%s', %d, 0, -1, 0, %d);" % (consoleId, name.replace("'", "''"), f.replace("'", "''"), gameApiId, thumbPath, overview.replace("'", "''"), released, fileSize))
								elif gameApiId != -1:
									self.__progress = 'Updating %s...' % name
									logging.debug('updating game record in database...')
									cur.execute("UPDATE `games` SET `api_id` = %d, `cover_art` = '%s', `overview` = '%s', `exists` = 1 WHERE `game_id` = %d;" % (gameApiId, thumbPath, overview.replace("'", "''"), row['game_id']))
								else:
									self.__progress = 'No need to update %s' % name
									logging.debug("no need to update - could not find %s in online database" % name)
									cur.execute('UPDATE `games` SET `exists` = 1 WHERE `game_id` = %d;' % row["game_id"])
									
								con.commit()
							else:
								self.__progress = 'No need to update %s' % name
								logging.debug("no need to update %s" % name)
								cur.execute('UPDATE `games` SET `exists` = 1 WHERE `game_id` = %d;' % row["game_id"])
								con.commit()

							if self.__stopCheck(con, cur):
								return

			except sqlite3.Error, e:
				logging.error('could not update database: %s' % e.args[0])
				if con:
					con.rollback()
				self.__progress = 'An error occurred whilst updating the database'
				self.__finished = True
				return

		try:
			logging.debug('purging missing games')
			cur.execute('DELETE FROM `games` WHERE `exists` = 0')
			con.commit()
			con.close()
		except sqlite3.Error, e:
			logging.error('could not delete missing games from database: %s' % e.args[0])
			if con:
				con.rollback()
			self.__progress = 'An error occurred whilst updating the database'
			self.__finished = True

		self.__progress = 'Update complete'
		self.__finished = True
		logging.debug('UpdateDbThread: finished')
		return

	def getProgress(self):
		return self.__progress

	def hasFinished(self):
		return self.__finished

	def hasStarted(self):
		return self.__started

	def stop(self):
		self.__stop = True

	def __stopCheck(self, con=None, cur=None):
		if self.__stop:
			if cur != None and con != None:
				try:
					cur.execute('DELETE FROM `games` WHERE `exists` = 0')
					con.commit()
					con.close()
				except sqlite3.Error, e:
					logging.error("Error: %s" % e.args[0])
				
			self.__progress = 'Update interrupted!'
			self.__finished = True
			logging.debug('UpdateDbThread: finished (interrupted)')
			return True
		return False

class JoyStick(object):

	BTN_START = 'btn_start'
	BTN_SELECT = 'btn_select'
	BTN_A = 'btn_a'
	BTN_B = 'btn_b'
	BTN_X = 'btn_x'
	BTN_Y = 'btn_y'
	BTN_LEFT = 'btn_left'
	BTN_RIGHT = 'btn_right'
	BTN_UP = 'btn_up'
	BTN_DOWN = 'btn_down'
	BTN_LEFT_AXIS_UP = 'btn_left_axis_up'
	BTN_LEFT_AXIS_DOWN = 'btn_left_axis_down'
	BTN_LEFT_AXIS_RIGHT = 'btn_left_axis_right'
	BTN_LEFT_AXIS_LEFT = 'btn_left_axis_left'
	BTN_RIGHT_AXIS_UP = 'btn_right_axis_up'
	BTN_RIGHT_AXIS_DOWN = 'btn_right_axis_down'
	BTN_RIGHT_AXIS_RIGHT = 'btn_right_axis_right'
	BTN_RIGHT_AXIS_LEFT = 'btn_right_axis_left'
	BTN_SHOULDER_LEFT = 'btn_shoulder_left'
	BTN_SHOULDER_RIGHT = 'btn_shoulder_right'
	BTN_SHOULDER_LEFT2 = 'btn_shoulder_left2'
	BTN_SHOULDER_RIGHT2 = 'btn_shoulder_right2'
	BTN_LEFT3 = 'btn_left3'
	BTN_RIGHT3 = 'btn_right3'
	BTN_SAVE_STATE = 'btn_save_state'
	BTN_LOAD_STATE = 'btn_load_state'
	BTN_EXIT = 'btn_exit'

	def __init__(self, name, buttons):
		#logging.debug("creating JoyStick object \"%s\" with buttons: %s" % (name, buttons))
		self.__name = name
		self.__matches = []
		self.__eventMap = {}
		self.__axisHistory = {}
		self.__btnMap = {}
		for b in buttons:
			(key, value) = b
			#print "%s = %s" % (key, value)
			if value != 'None':
				if key[0:4] == 'btn_':
					self.__eventMap[value] = key
					self.__btnMap[key] = value

	def axisToKeyEvent(self, event):
		if event.value == -1.0 or event.value == 1.0:
			# axis pressed
			if not self.__axisHistory.has_key(event.joy):
				self.__axisHistory[event.joy] = {}

			if not self.__axisHistory[event.joy].has_key(event.axis):
				self.__axisHistory[event.joy][event.axis] = (AXIS_PRESSED, event.value)
		
			if self.__axisHistory[event.joy][event.axis][0] != AXIS_PRESSED:
				self.__axisHistory[event.joy][event.axis] = (AXIS_PRESSED, event.value)
		elif event.value < 0.5 and event.value > -0.5:
			# axis released
			if not self.__axisHistory.has_key(event.joy):
				self.__axisHistory[event.joy] = {}

			if not self.__axisHistory[event.joy].has_key(event.axis):
				self.__axisHistory[event.joy][event.axis] = (AXIS_INITIALISED, 0.0)

			if self.__axisHistory[event.joy][event.axis][0] == AXIS_PRESSED:
				self.__axisHistory[event.joy][event.axis] = (AXIS_RELEASED, self.__axisHistory[event.joy][event.axis][1])

			if event.type == pygame.JOYAXISMOTION and self.__axisHistory[event.joy].has_key(event.axis):
				(action, axisValue) = self.__axisHistory[event.joy][event.axis]
				if action == AXIS_RELEASED:
					value = None
					if axisValue > 0:
						value = "+%d" % event.axis
					else:
						value = "-%d" % event.axis

					del self.__axisHistory[event.joy][event.axis] # remove from event history dictionary

					if value in self.__eventMap:
						if self.__eventMap[value] == JoyStick.BTN_A:
							return pygame.event.Event(KEYDOWN, {'key': K_RETURN})
						if self.__eventMap[value] == JoyStick.BTN_B:
							return pygame.event.Event(KEYDOWN, {'key': K_BACKSPACE})
						if self.__eventMap[value] == JoyStick.BTN_X:
							return pygame.event.Event(KEYDOWN, {'key': K_i})
						if self.__eventMap[value] == JoyStick.BTN_Y:
							return pygame.event.Event(KEYDOWN, {'key': K_f})
						if self.__eventMap[value] == JoyStick.BTN_EXIT:
							return pygame.event.Event(KEYDOWN, {'key': K_ESCAPE})
						if self.__eventMap[value] == JoyStick.BTN_LEFT:
							return pygame.event.Event(KEYDOWN, {'key': K_LEFT})
						if self.__eventMap[value] == JoyStick.BTN_RIGHT:
							return pygame.event.Event(KEYDOWN, {'key': K_RIGHT})
						if self.__eventMap[value] == JoyStick.BTN_UP:
							return pygame.event.Event(KEYDOWN, {'key': K_UP})
						if self.__eventMap[value] == JoyStick.BTN_DOWN:
							return pygame.event.Event(KEYDOWN, {'key': K_DOWN})
						if self.__eventMap[value] == JoyStick.BTN_SHOULDER_LEFT:
							return pygame.event.Event(KEYDOWN, {'key': K_PAGEUP})
						if self.__eventMap[value] == JoyStick.BTN_SHOULDER_RIGHT:
							return pygame.event.Event(KEYDOWN, {'key': K_PAGEDOWN})
						if self.__eventMap[value] == JoyStick.BTN_LEFT_AXIS_LEFT:
							return pygame.event.Event(KEYDOWN, {'key': K_LEFT})
						if self.__eventMap[value] == JoyStick.BTN_LEFT_AXIS_RIGHT:
							return pygame.event.Event(KEYDOWN, {'key': K_RIGHT})
						if self.__eventMap[value] == JoyStick.BTN_LEFT_AXIS_UP:
							return pygame.event.Event(KEYDOWN, {'key': K_UP})
						if self.__eventMap[value] == JoyStick.BTN_LEFT_AXIS_DOWN:
							return pygame.event.Event(KEYDOWN, {'key': K_DOWN})
						if self.__eventMap[value] == JoyStick.BTN_SELECT:
							return pygame.event.Event(KEYDOWN, {'key': K_s})	
		return None

	def buttonToKeyEvent(self, event):
		event = str(event)
		if event in self.__eventMap:
			if self.__eventMap[event] == JoyStick.BTN_A:
				return pygame.event.Event(KEYDOWN, {'key': K_RETURN})
			if self.__eventMap[event] == JoyStick.BTN_B:
				return pygame.event.Event(KEYDOWN, {'key': K_BACKSPACE})
			if self.__eventMap[event] == JoyStick.BTN_X:
				return pygame.event.Event(KEYDOWN, {'key': K_i})
			if self.__eventMap[event] == JoyStick.BTN_Y:
				return pygame.event.Event(KEYDOWN, {'key': K_f})
			if self.__eventMap[event] == JoyStick.BTN_EXIT:
				return pygame.event.Event(KEYDOWN, {'key': K_ESCAPE})
			if self.__eventMap[event] == JoyStick.BTN_LEFT:
				return pygame.event.Event(KEYDOWN, {'key': K_LEFT})
			if self.__eventMap[event] == JoyStick.BTN_RIGHT:
				return pygame.event.Event(KEYDOWN, {'key': K_RIGHT})
			if self.__eventMap[event] == JoyStick.BTN_UP:
				return pygame.event.Event(KEYDOWN, {'key': K_UP})
			if self.__eventMap[event] == JoyStick.BTN_DOWN:
				return pygame.event.Event(KEYDOWN, {'key': K_DOWN})
			if self.__eventMap[event] == JoyStick.BTN_SHOULDER_LEFT:
				return pygame.event.Event(KEYDOWN, {'key': K_PAGEUP})
			if self.__eventMap[event] == JoyStick.BTN_SHOULDER_RIGHT:
				return pygame.event.Event(KEYDOWN, {'key': K_PAGEDOWN})
			if self.__eventMap[event] == JoyStick.BTN_SELECT:
				return pygame.event.Event(KEYDOWN, {'key': K_s})
		return None

	def getAxisOrBtn(self, btn):
		if not btn in self.__btnMap or self.__btnMap[btn] == None:
			return 'btn'
		value = self.__btnMap[btn]
		if value[0:1] == '-' or value[0:1] == '+':
			return 'axis'
		return 'btn'
		
	def getButton(self, event):
		event = str(event)
		if event in self.__eventMap:
			return self.__eventMap[event]
		return None

	def getButtonValue(self, name):
		if name in self.__btnMap:
			return self.__btnMap[name]
		return None

	def getMupen64PlusButtonValue(self, btn):
		if not btn in self.__btnMap or self.__btnMap[btn] == None:
			return ''
		value = self.__btnMap[btn]
		if btn == JoyStick.BTN_LEFT_AXIS_LEFT or btn == JoyStick.BTN_LEFT_AXIS_UP:
			if value[0:1] == '-' or value[0:1] == '+':
				return '"axis(%s-,%s+)"' % (value[1:], value[1:])
			else:
				return '""'
		if value[0:1] == '-' or value[0:1] == '+':
			return '"axis(%s%s)"' % (value[1:], value[0:1])
		return '"button(%s)"' % value
		
	def getName(self):
		return self.__name

	def getRetroArchButtonValue(self, btn):
		if not btn in self.__btnMap or self.__btnMap[btn] == None:
			return 'nul'
		#try:
		#	b = int(self.__btnMap[btn])
		#	return b
		#except ValueError, e:
		#	return 'nul'
		return self.__btnMap[btn]

	def getRetroArchConfig(self):
		cfg = 'input_device = "%s"\n' % (self.__name)
		cfg += 'input_driver = "linuxraw\"\n'
		cfg += 'input_b_btn = "%s"\n' % (self.getRetroArchButtonValue(JoyStick.BTN_B))
		cfg += 'input_a_btn = "%s"\n' % (self.getRetroArchButtonValue(JoyStick.BTN_A))
		cfg += 'input_y_btn = "%s"\n' % (self.getRetroArchButtonValue(JoyStick.BTN_Y))
		cfg += 'input_x_btn = "%s"\n' % (self.getRetroArchButtonValue(JoyStick.BTN_X))
		cfg += 'input_l_%s = "%s"\n' % (self.getAxisOrBtn(JoyStick.BTN_SHOULDER_LEFT), self.getRetroArchButtonValue(JoyStick.BTN_SHOULDER_LEFT))
		cfg += 'input_r_%s = "%s"\n' % (self.getAxisOrBtn(JoyStick.BTN_SHOULDER_RIGHT), self.getRetroArchButtonValue(JoyStick.BTN_SHOULDER_RIGHT))
		cfg += 'input_l2_%s = "%s"\n' % (self.getAxisOrBtn(JoyStick.BTN_SHOULDER_LEFT2), self.getRetroArchButtonValue(JoyStick.BTN_SHOULDER_LEFT2))
		cfg += 'input_r2_%s = "%s"\n' % (self.getAxisOrBtn(JoyStick.BTN_SHOULDER_RIGHT2), self.getRetroArchButtonValue(JoyStick.BTN_SHOULDER_RIGHT2))
		cfg += 'input_l3_%s = "%s"\n' % (self.getAxisOrBtn(JoyStick.BTN_LEFT3), self.getRetroArchButtonValue(JoyStick.BTN_LEFT3))
		cfg += 'input_r3_%s = "%s"\n' % (self.getAxisOrBtn(JoyStick.BTN_RIGHT3), self.getRetroArchButtonValue(JoyStick.BTN_RIGHT3))
		cfg += 'input_start_btn = "%s"\n' % (self.getRetroArchButtonValue(JoyStick.BTN_START))
		cfg += 'input_select_btn = "%s"\n' % (self.getRetroArchButtonValue(JoyStick.BTN_SELECT))
		cfg += 'input_up_%s = "%s"\n' % (self.getAxisOrBtn(JoyStick.BTN_UP), self.getRetroArchButtonValue(JoyStick.BTN_UP))
		cfg += 'input_down_%s = "%s"\n' % (self.getAxisOrBtn(JoyStick.BTN_DOWN), self.getRetroArchButtonValue(JoyStick.BTN_DOWN))
		cfg += 'input_left_%s = "%s"\n' % (self.getAxisOrBtn(JoyStick.BTN_LEFT), self.getRetroArchButtonValue(JoyStick.BTN_LEFT))
		cfg += 'input_right_%s = "%s"\n' % (self.getAxisOrBtn(JoyStick.BTN_RIGHT), self.getRetroArchButtonValue(JoyStick.BTN_RIGHT))
		cfg += 'input_save_state_btn = "%s"\n' % (self.getRetroArchButtonValue(JoyStick.BTN_SAVE_STATE))
		cfg += 'input_load_state_btn = "%s"\n' % (self.getRetroArchButtonValue(JoyStick.BTN_LOAD_STATE))
		cfg += 'input_exit_emulator_btn = "%s"\n' % (self.getRetroArchButtonValue(JoyStick.BTN_EXIT))
		cfg += 'input_pause_toggle = "nul"\n'
		cfg += 'input_l_x_plus_%s = "%s"\n' % (self.getAxisOrBtn(JoyStick.BTN_LEFT_AXIS_RIGHT), self.getRetroArchButtonValue(JoyStick.BTN_LEFT_AXIS_RIGHT))
		cfg += 'input_l_x_minus_%s = "%s"\n' % (self.getAxisOrBtn(JoyStick.BTN_LEFT_AXIS_LEFT), self.getRetroArchButtonValue(JoyStick.BTN_LEFT_AXIS_LEFT))
		cfg += 'input_l_y_plus_%s = "%s"\n' % (self.getAxisOrBtn(JoyStick.BTN_LEFT_AXIS_UP), self.getRetroArchButtonValue(JoyStick.BTN_LEFT_AXIS_UP))
		cfg += 'input_l_y_minus_%s = "%s"\n' % (self.getAxisOrBtn(JoyStick.BTN_LEFT_AXIS_DOWN), self.getRetroArchButtonValue(JoyStick.BTN_LEFT_AXIS_DOWN))
		cfg += 'input_r_x_plus_%s = "%s"\n' % (self.getAxisOrBtn(JoyStick.BTN_RIGHT_AXIS_RIGHT), self.getRetroArchButtonValue(JoyStick.BTN_RIGHT_AXIS_RIGHT))
		cfg += 'input_r_x_minus_%s = "%s"\n' % (self.getAxisOrBtn(JoyStick.BTN_RIGHT_AXIS_LEFT), self.getRetroArchButtonValue(JoyStick.BTN_RIGHT_AXIS_LEFT))
		cfg += 'input_r_y_plus_%s = "%s"\n' % (self.getAxisOrBtn(JoyStick.BTN_RIGHT_AXIS_UP), self.getRetroArchButtonValue(JoyStick.BTN_RIGHT_AXIS_UP))
		cfg += 'input_r_y_minus_%s = "%s"\n' % (self.getAxisOrBtn(JoyStick.BTN_RIGHT_AXIS_DOWN), self.getRetroArchButtonValue(JoyStick.BTN_RIGHT_AXIS_DOWN))
		return cfg

	def isMatch(self, js):
		#for i in self.__matches:
		#	if i in js:
		#		return True
		#return False
		return self.__name == js

class Record(object):

	def __init__(self, db, table, fields, keyField, keyValue = None, autoIncrement = True, loadData = True):
		self.__db = db
		self.__autoIncrement = autoIncrement
		self.__table = table
		self.__fields = fields
		self.__keyField = keyField
		self.__keyValue = keyValue
		self.__properties = {}
		self.__properties[self.__keyField] = keyValue
		self.__isDirty = False
		self.__con = None
		self.__dirtyFields = []

		if loadData:
			self.refresh()
			self.__dataLoaded = True
		else:
			self.__dataLoaded = False

	def connect(self):
		if self.__con:
			return self.__con

		self.__con = sqlite3.connect(self.__db)
		self.__con.row_factory = sqlite3.Row
		self.__cur = self.__con.cursor()
		#logging.debug("connected to %s database, using table %s" % (self.__db, self.__table))
		return self.__con

	@staticmethod
	def convertValue(v):
		isNumeric = False
		try:
			float(v)
			isNumeric = True
		except ValueError:
			pass

		if not isNumeric:
			return '"%s"' % v
		return str(v)

	def dataLoaded(self):
		return self.__dataLoaded
		
	def disconnect(self):
		if self.__con:
			self.__con.close()
		self.__con = None
		#logging.debug("disconnected from %s database, using table %s" % (self.__db, self.__table))

	def doQuery(self, query):
		if not self.__con:
			raise sqlite3.Error('Database %s not connected' % self.__db)
		logging.debug('executing query: %s' % query)
		self.__cur.execute(query)
		return self.__cur

	def __getFieldsQuery(self):
		i = 0
		total = len(self.__fields)
		query = ''
		for f in self.__fields:
			query += '`%s`' % f
			if i < total - 1:
				query += ','
			i += 1
		return query

	def getDb(self):
		return self.__db

	def getId(self):
		return self.__properties[self.__keyField]

	def getProperty(self, field):
		if self.__dataLoaded:
			return self.__properties[field]
		return None

	def __getWritableFields(self):
		l = []
		for f in self.__fields:
			if f != self.__keyField:
				l.append(f)

		return l

	def isDirty(self):
		return len(self.__dirtyFields) > 0

	def isNew(self):
		return self.__isNew

	def refresh(self):
		self.connect()
		if not self.__con:
			raise sqlite3.Error('Database %s not connected' % self.__db)

		if self.__properties[self.__keyField] != None:
			self.doQuery('SELECT %s FROM `%s` WHERE `%s` = %d;' % (self.__getFieldsQuery(), self.__table, self.__keyField, self.__properties[self.__keyField]))
			row = self.__cur.fetchone()
			if row == None:
				#raise sqlite3.Error('No record found for field "%s" in table "%s"' % (self.__primaryKey, self.__table)
				self.__isNew = True
				self.__dirtyFields = self.__getWritableFields()
			else:
				for f in self.__fields:
					self.__properties[f] = row[f]
				self.__isNew = False
				self._dirtyFields = []
			self.__dataLoaded = True
		else:
			self.__isNew = True
			self.__dataLoaded = False
		self.disconnect()

	def save(self):
		self.connect()
		if not self.__con:
			raise sqlite3.Error('Database %s not connected' % self.__db)

		query = ''
		if self.__isNew:
			i = 0
			writableFields = None
			if self.__autoIncrement:
				writableFields = self.__getWritableFields()
			else:
				writableFields = self.__fields
			total = len(writableFields)
			query = 'INSERT INTO `%s` (' % self.__table
			endQuery = ''
			for f in writableFields:
				query += '`%s`' % f
				endQuery += self.convertValue(self.__properties[f])
				if i < total - 1:
					query += ','
					endQuery += ','
				i += 1

			query += ') VALUES (%s);' % endQuery
				
		else:
			i = 0
			total = len(self.__dirtyFields)
			query = 'UPDATE `%s` SET ' % self.__table
			for f in self.__dirtyFields:
				query += '`%s` = %s' % (f, self.convertValue(self.__properties[f]))
				if i < total - 1:
					query += ','
				i += 1
			query += ' WHERE `%s` = %d;' % (self.__keyField, self.__properties[self.__keyField])

		self.doQuery(query)
		self.__con.commit()
		self.disconnect()

		if self.__isNew:
			self.__isNew = False
			self.__properties[self.__keyField] = self.__cur.lastrowid
		self.__dirtyFields = []

	def setProperty(self, field, value):
		self.__properties[field] = value
		if not field in self.__dirtyFields:
			self.__dirtyFields.append(field)

class Console(Record):

	def __init__(self, name, consoleId, apiId, extensions, romDir, command, db, consoleImg, noCoverArtImg, imgCacheDir, emulator):
		super(Console, self).__init__(db, 'consoles', ['console_id', 'name'], 'console_id', consoleId, True)
		self.setProperty('name', name)
		self.__apiId = apiId
		self.__extensions = extensions
		self.__romDir = romDir
		self.__consoleImg = consoleImg
		self.__noCoverArtImg = noCoverArtImg
		self.__emulator = emulator
		self.__games = []
		self.__command = command
		self.__imgCacheDir = imgCacheDir
		self.__gameTotal = 0
		
	def getApiId(self):
		return self.__apiId

	def getCommand(self, game):
		return self.__command.replace('%%GAME%%', "\"%s\"" % game.getPath())

	def getDir(self):
		return self.__dir

	def getEmulator(self):
		return self.__emulator
		
	def getGames(self, favouritesOnly=False, limit=0, count=0):
		self.connect()
		query = 'SELECT `game_id` FROM `games` WHERE `console_id` = %d ' % self.getId()
		if favouritesOnly:
			query += ' AND favourite = 1 '
		query += 'ORDER BY `name`'
		if limit >= 0 and count > 0:
			query += ' LIMIT %d, %d' % (limit, count)
		query += ';'
		cur = self.doQuery(query)
		self.__games = []
		while True:
			row = cur.fetchone()
			if row == None:
				break
			self.__games.append(Game(row['game_id'], self.getDb(), self, False))
		self.disconnect()
		return self.__games

	def getGameTotal(self):
		self.connect()
		cur = self.doQuery('SELECT COUNT(`game_id`) AS `total` FROM `games` WHERE `console_id` = %d;' % self.getId())
		row = cur.fetchone()
		self.disconnect()
		return row['total']	

	def getExtensions(self):
		return self.__extensions
		
	def getFavouriteTotal(self):
		self.connect()
		cur = self.doQuery('SELECT COUNT(`game_id`) AS `total` FROM `games` WHERE `favourite` = 1 AND `console_id` = %d;' % self.getId())
		row = cur.fetchone()
		self.disconnect()
		return row['total']	

	def getImgCacheDir(self):
		return self.__imgCacheDir
	
	def getImg(self):
		return self.__consoleImg

	def getName(self):
		return self.getProperty('name')

	def getNoCoverArtImg(self):
		return self.__noCoverArtImg

	def getRomDir(self):
		return self.__romDir

class Game(Record):

	def __init__(self, gameId, db, console=None, loadData=True):
		super(Game, self).__init__(db, 'games', ['api_id', 'exists', 'console_id', 'name', 'cover_art', 'game_path', 'overview', 'released', 'last_played', 'favourite', 'play_count', 'size'], 'game_id', int(gameId), True, loadData)
		self.__console = console

	def getCommand(self):
		return self.__console.getCommand(self)

	def getConsole(self):
		return self.__console

	def getConsoleId(self):
		return self.getProperty('console_id')

	def getCoverArt(self):
		coverArt = self.getProperty('cover_art')
		if coverArt == '0':
			return None
		return coverArt

	def getLastPlayed(self, fmt=None):
		timestamp = int(self.getProperty('last_played'))
		if timestamp == -1:
			return None
		if fmt == None:
			return timestamp
		return datetime.fromtimestamp(timestamp).strftime(fmt)

	def getName(self):
		return self.getProperty('name')

	def getOverview(self):
		return self.getProperty('overview')

	def getPath(self):
		return self.getProperty('game_path')

	def getReleased(self, fmt=None):
		timestamp = self.getProperty('released')
		if fmt == None:
			return timestamp
		return datetime.fromtimestamp(timestamp).strftime(fmt)

	def getPlayCount(self):
		return self.getProperty('play_count')

	def getSize(self):
		return self.getProperty('size')

	def isFavourite(self, yesNoMap=None):
		fav = self.getProperty('favourite') == 1
		if yesNoMap == None:
			return fav
		if fav:
			return yesNoMap[0]
		return yesNoMap[1]

	def setConsoleId(self, consoleId):
		self.setProperty('console_id', consoleId)

	def setCoverArt(self, path):
		self.setProperty('game_path', path)

	def setFavourite(self, fav):
		if fav:
			self.setProperty('favourite', 1)
		else:
			self.setProperty('favourite', 0)

	def setLastPlayed(self, date=None):
		if date == None:
			# use current date/time
			date = int(time.time())
		self.setProperty('last_played', date)

	def setName(self, name):
		self.setProperty('name', name)

	def setOverview(self, overview):
		self.setProperty('overview', overview)

	def setReleased(self, released):
		self.setProperty('released', released)

	def setPath(self, path):
		self.setProperty('game_path', path)

	def setPlayCount(self, x=None):
		if x == None:
			x = self.getPlayCount() + 1
		self.setProperty('play_count', x)

	def setSize(self, s):
		self.setProperty('size')

class Panel(object):

	def __init__(self, width, height, bgColour, title='', margins=[0, 0, 0, 0]):
		self.__active = False
		self.__width = width
		self.__height = height
		self.__bgColour = bgColour
		self.__background = pygame.Surface((self.__width, self.__height)).convert()
		self.__handleJoyStickEvents = False
		self.__locked = False
		self.__listeners = []
		self.__title = title
		self.__margins = margins # left, right, top, bottom

	def addListener(self, l):
		self.__listeners.append(l)

	def blit(self, obj, coords, area=None):
		newCoords = (coords[0] + self.__margins[0], coords[1] + self.__margins[1])
		self.__background.blit(obj, newCoords, area)

	def fireEvent(self, event, args=None):
		if self.__active:
			for l in self.__listeners:
				l.processEvent(event, args)

	def fillBackground(self):
		self.__background.fill(self.__bgColour)

	def getBackground(self):
		return self.__background

	def getBackgroundColour(self):
		return self.__bgColour

	# help routine to returns an array of labels required to render the given text in the space available
	@staticmethod
	def getLabels(lines, font, colour, bgColour, width, height):
		fontHeight = font.size('A')[1]
		y = 0
		labels = []		

		for text in lines:
			while text:
				if y + fontHeight > height:
					break

				i = 1
				while font.size(text[:i])[0] < width and i < len(text):
					i += 1

				if i < len(text): 
					i = text.rfind(" ", 0, i) + 1

				labels.append(font.render(text[:i], 1, colour, bgColour))
				y += fontHeight

				text = text[i:]
		return labels

	def getHeight(self):
		return self.__height

	def getMargins(self):
		return self.__margins

	def getTitle(self):
		return self.__title

	def getWidth(self):
		return self.__width

	def handlesJoyStickEvents(self):
		return self.__handleJoyStickEvents

	def isActive(self):
		return self.__active

	def isLocked(self):
		return self.__locked

	def lock(self):
		self.__locked = True

	def processEvent(self, event):
		pass

	def removeListener(self, l):
		self.__listeners.remove(l)

	def setActive(self, active):
		self.__active = active

	def setHandleJoyStickEvents(self, b):
		self.__handleJoyStickEvents = b

	def setTitle(self, title):
		self.__title = title

	def unlock(self):
		self.__locked = False

	def update(self, x, y):
		screen = pygame.display.get_surface()
		screen.blit(self.getBackground(), (x, y))

class MessageBox(Panel):

	def __init__(self, width, height, font, fontSize, colour, bgColour, message):
		self.__transparentColour = (255, 174, 201) # pink
		super(MessageBox, self).__init__(width, height, self.__transparentColour)
		self.getBackground().set_colorkey(self.__transparentColour) # set background of the surface to be transparent
		self.__colour = colour
		self.__bgColour = bgColour
		self.__font = pygame.font.Font(font, fontSize)
		self.__message = message
		self.__redraw = True
		self.__lineWidth = 2
		self.__boxWidth = (width / 2) + (self.__lineWidth * 2)
		self.__labels = self.getLabels([message], self.__font, self.__colour, bgColour, self.__boxWidth, height)
		self.__okLabel = label = self.__font.render('OK', 1, bgColour, self.__colour)
		self.__okLabelWidth = self.__okLabel.get_rect().width
		self.__btnMargin = 20
		self.__boxHeight = (self.__labels[0].get_rect().height * len(self.__labels)) + (self.__lineWidth * 2) + self.__btnMargin + self.__okLabel.get_rect().height + 5

	def draw(self, x, y):
		if self.isActive() and self.__redraw:
			self.fillBackground()
			# draw in center of the screen
			currentX = (self.getWidth() - self.__boxWidth) / 2
			currentY = (self.getHeight() - self.__boxHeight) / 2

			pygame.draw.rect(self.getBackground(), self.__bgColour, (currentX, currentY, self.__boxWidth, self.__boxHeight), 0)
			pygame.draw.rect(self.getBackground(), self.__colour, (currentX, currentY, self.__boxWidth, self.__boxHeight), self.__lineWidth)

			currentX += self.__lineWidth
			currentY += self.__lineWidth

			for l in self.__labels:
				labelRec = l.get_rect()
				currentX = (self.getWidth() - labelRec.width) / 2
				self.blit(l, (currentX, currentY))
				currentY += labelRec.height

			currentY += self.__btnMargin
			currentX = (self.getWidth() - self.__okLabelWidth) / 2
			self.blit(self.__okLabel, (currentX, currentY))
			
			self.update(x, y)
			self.__redraw = False

	def handleEvent(self, event):
		if self.isActive():
			if event.type == KEYDOWN and event.key == K_RETURN:
				if event.key == K_RETURN:
					self.fireEvent(EVENT_MESSAGE_BOX_OK)

	def setActive(self, active):
		if active:
			self.__redraw = True
		super(MessageBox, self).setActive(active)

class Footer(Panel):

	def __init__(self, width, height, font, fontSize, colour, bgColour):
		super(Footer, self).__init__(width, height, bgColour)
		self.__colour = colour
		self.__font = pygame.font.Font(font, fontSize)
		self.__lineHeight = 2
		self.__fields = OrderedDict()
		
		self.__fields['IP'] = '127.0.0.1'
		self.__fields['Temp'] = '0C'
		self.__fields['JoySticks'] = 0
		self.__fields['Primary Joystick'] = 'Disabled'

		self.__fieldLabelSpacing = width / len(self.__fields)
		self.__redraw = True
		
	def draw(self, x, y):
		if self.isActive() and self.__redraw:
			self.fillBackground()
			pygame.draw.rect(self.getBackground(), self.__colour, (5, 0, self.getWidth(), self.__lineHeight), 0)

			labelX = 5
			labelY = self.__lineHeight + 2
			i = 1
			for key, value in self.__fields.iteritems():
				label = self.__font.render("%s: %s" % (key, value), 1, self.__colour)
				self.blit(label, (labelX, labelY))
				labelX += self.__fieldLabelSpacing
				i += 1

			self.update(x, y)
			self.__redraw = False

	def setField(self, field, value):
		if field in self.__fields:
			self.__fields[field] = value
			self.__redraw = True

class Header(Panel):

	def __init__(self, title, width, height, font, fontSize, colour, bgColour):
		super(Header, self).__init__(width, height, bgColour)
		self.__lineHeight = 2
		self.__gap = 2
		self.__colour = colour
		self.__bgColour = bgColour
		self.__font = pygame.font.Font(font, fontSize)
		self.__title = title
		self.__label = self.__font.render(self.__title, 1, self.__colour)
		self.__lastTime = 0
		self.__redraw = True

	def draw(self, x, y):
		if self.isActive():
			doBlit = False

			if self.__redraw:
				self.fillBackground()
				doBlit = True
				self.blit(self.__label, (x, y))
				pygame.draw.rect(self.getBackground(), self.__colour, (x, self.__label.get_rect().height + self.__gap, self.getWidth(), self.__lineHeight), 0)

			timeStamp = time.time()
			if self.__redraw or timeStamp - self.__lastTime > 30:
				#print "updating time"
				doBlit = True
				self.__lastTime = timeStamp
				now = datetime.now()
				timeLabel = self.__font.render(now.strftime("%H:%M %d/%m/%Y"), 1, self.__colour, self.getBackgroundColour())
				self.blit(timeLabel, (self.getWidth() - timeLabel.get_rect().width, y))
		
			if doBlit:
				self.update(x, y)

			self.__redraw = False

	def setTitle(self, title):
		self.__title = title
		self.__label = self.__font.render(self.__title, 1, self.__colour)
		self.__redraw = True

class ThumbnailMenu(Panel):

	def __init__(self, menuItems, width, height, font, fontSize, colour, bgColour, thumbsPerRow=4, fitToHeight=True):
		super(ThumbnailMenu, self).__init__(width, height, bgColour)

		self.__thumbMargin = 30
		self.__menuItems = menuItems
		self.__menuItemsTotal = len(menuItems)
		self.__font = pygame.font.Font(font, fontSize)
		self.__fontHeight = self.__font.size('A')[1]

		# use first thumbnail to work out image ratios
		imgWidth, imgHeight = menuItems[0].getImageDimensions()
		#self.__imgRatio = float(imgHeight) / float(imgWidth)

		marginSpace = self.__thumbMargin * thumbsPerRow

		if fitToHeight:
			# we need to fit ALL thumbnails on the first page, therefore need to use
			# image dimensions to work out scaling
			self.__thumbsInY = int(round(float(self.__menuItemsTotal) / float(thumbsPerRow), 0))
			if self.__thumbsInY == 0:
				self.__thumbsInY = 1
			marginSpace = (self.__fontHeight + self.__thumbMargin) * (self.__thumbsInY + 1)
			self.__thumbHeight = (height - marginSpace) / self.__thumbsInY
			imgRatio = float(imgWidth) / float(imgHeight)
			self.__thumbWidth = int(self.__thumbHeight * imgRatio)	
			self.__thumbsInX = thumbsPerRow
			if (self.__thumbWidth + self.__thumbMargin) * thumbsPerRow > width:
				# doesn't fit width wise
				self.__thumbWidth = (width - ((thumbsPerRow) * self.__thumbMargin)) / thumbsPerRow
				imgRatio = float(imgHeight) / float(imgWidth)
				self.__thumbHeight = int(self.__thumbWidth * imgRatio)
		else:
			imgRatio = float(imgHeight) / float(imgWidth)
			self.__thumbWidth = int((width - marginSpace) / thumbsPerRow)
			self.__thumbHeight = int(self.__thumbWidth * imgRatio)		
			self.__thumbsInY = self.getHeight() / (self.__thumbHeight + self.__thumbMargin + (self.__fontHeight * 2))
			self.__thumbsInX = int(self.getWidth() / (self.__thumbWidth + self.__thumbMargin))
		
		self.__colour = colour
		self.__selected = 0
		self.__startIndex = 0
		self.__menuItems[self.__selected].setSelected(True)
		
		self.__visibleItems = self.__thumbsInX * self.__thumbsInY
		self.__redraw = True

	def __getStartIndex(self, index):
		return (index / self.__visibleItems) * self.__visibleItems

	def draw(self, x, y):
		x = 0 # ignore screen margin
		if self.isActive() and self.__redraw:
			self.fillBackground()
			thumbsWidth = (self.__thumbsInX * self.__thumbWidth) + ((self.__thumbsInX - 1) * self.__thumbMargin)
			startX = (self.getWidth() - thumbsWidth) / 2 
			nextX = startX

			nextY = y
			i = self.__startIndex
			col = 0
			label = None

			while i < self.__visibleItems + self.__startIndex and i < self.__menuItemsTotal:
				if self.__menuItems[i].isSelected():
					pygame.draw.rect(self.getBackground(), self.__colour, (nextX - 2, nextY - 2, self.__thumbWidth + 4, self.__thumbHeight + (self.__fontHeight * 2) + 4), 0)
					labelY = nextY + self.__thumbHeight
					for l in self.getLabels([self.__menuItems[i].getText()], self.__font, self.getBackgroundColour(), self.__colour, self.__thumbWidth, self.__fontHeight * 2):
						self.blit(l, (nextX, labelY))
						labelY += l.get_rect().height
				else:
					labelY = nextY + self.__thumbHeight
					for l in self.getLabels([self.__menuItems[i].getText()], self.__font, self.__colour, self.getBackgroundColour(), self.__thumbWidth, self.__fontHeight * 2):
						self.blit(l, (nextX, labelY))
						labelY += l.get_rect().height

				image = self.__menuItems[i].getThumbnail(self.__thumbWidth, self.__thumbHeight)
				self.blit(image, (nextX, nextY))
				col += 1
				nextX += self.__thumbWidth + self.__thumbMargin
				if col == self.__thumbsInX:
					nextY += self.__thumbHeight + self.__thumbMargin + self.__fontHeight
					nextX = startX
					col = 0
				i += 1

			self.update(x, y)
			self.__redraw = False

	def handleEvent(self, event):
		if self.isActive():
			if event.type == KEYDOWN:
				if event.key == K_UP:
					self.__menuItems[self.__selected].setSelected(False)
					self.__selected -= self.__thumbsInX
					if self.__selected < 0:
						self.__selected = self.__menuItemsTotal - 1
						self.__startIndex = self.__getStartIndex(self.__selected)
					elif self.__selected < self.__startIndex:
						self.__startIndex = self.__getStartIndex(self.__selected)
					self.__menuItems[self.__selected].setSelected(True)
					self.__redraw = True
				elif event.key == K_DOWN:
					self.__menuItems[self.__selected].setSelected(False)
					self.__selected += self.__thumbsInX
					if self.__selected > self.__startIndex + self.__visibleItems - 1:
						self.__startIndex = self.__getStartIndex(self.__selected)
						if self.__startIndex < self.__menuItemsTotal:
							if self.__selected > self.__menuItemsTotal - 1:
								self.__selected = self.__startIndex
						else:
							self.__startIndex = 0
							self.__selected = 0
					elif self.__selected > self.__menuItemsTotal - 1:
						self.__startIndex = 0
						self.__selected = 0
					self.__menuItems[self.__selected].setSelected(True)
					self.__redraw = True
				elif event.key == K_LEFT:
					self.__menuItems[self.__selected].setSelected(False)
					self.__selected -= 1
					if self.__selected < 0:
						self.__selected = self.__menuItemsTotal - 1
						self.__startIndex = self.__getStartIndex(self.__selected)
					elif self.__selected < self.__startIndex:
						self.__startIndex = self.__selected - self.__visibleItems + 1
					self.__menuItems[self.__selected].setSelected(True)
					self.__redraw = True
				elif event.key == K_RIGHT:
					self.__menuItems[self.__selected].setSelected(False)
					self.__selected += 1
					if self.__selected > self.__menuItemsTotal - 1:
						self.__selected = 0
						self.__startIndex = 0
					elif self.__selected > self.__startIndex + self.__visibleItems - 1:
						self.__startIndex = self.__selected
					self.__menuItems[self.__selected].setSelected(True)
					self.__redraw = True
				elif event.key == K_RETURN:
					return self.__menuItems[self.__selected].activate()
		return None

	def setActive(self, active):
		if active:
			self.__redraw = True
		super(ThumbnailMenu, self).setActive(active)

	def setLabelText(self, index, text):
		if index >= 0 and index < self.__menuItemsTotal:
			self.__menuItems[index].setText(text)

class GamesMenu(Panel):

	def __init__(self, console, width, height, font, fontSize, colour, bgColour, favImage):
		super(GamesMenu, self).__init__(width, height, bgColour, console.getName())
		self.__colour = colour
		self.__font = pygame.font.Font(font, fontSize)
		self.__fontHeight = self.__font.size('A')[1]
		self.__smallFont = pygame.font.Font(font, fontSize - 4)
		self.__smallFontHeight = self.__smallFont.size('A')[1]
		self.__console = console
		self.__thumbMargin = 40
		self.__thumbsInX = 5
		self.__thumbsInY = 2 # desired number of rows

		self.__nocoverArtImage = pygame.image.load(console.getNoCoverArtImg()).convert()
		imgWidth = self.__nocoverArtImage.get_width()
		imgHeight = self.__nocoverArtImage.get_height()

		self.__thumbWidth = (width - (self.__thumbsInX * self.__thumbMargin)) / self.__thumbsInX
		imgRatio = float(imgHeight) / float(imgWidth)
		self.__thumbHeight = int(self.__thumbWidth * imgRatio)
		
		thumbsInY = (height - self.__smallFontHeight) / (self.__thumbHeight + (self.__fontHeight * 2) + self.__thumbMargin)
		if thumbsInY < self.__thumbsInY:
			# what width is required to fix a minimum of two rows?
			imgRatio = float(imgWidth) / float(imgHeight)
			self.__thumbHeight = int((height - self.__smallFontHeight - (((self.__fontHeight * 2) + self.__thumbMargin) * self.__thumbsInY)) / self.__thumbsInY)
			self.__thumbWidth = int(self.__thumbHeight * imgRatio)
		else:
			self.__thumbsInY = thumbsInY

		#print "RATIO: %f" % imgRatio
		#print "IMG WIDTH: %d" % imgWidth
		#print "IMG HEIGHT: %d" % imgHeight
		#print "THUMB WIDTH: %d" % self.__thumbWidth
		#print "THUMB HEIGHT: %d" % self.__thumbHeight
		#print "PANEL WIDTH: %d" % self.getHeight()
		#print "PANEL HEIGHT: %d" % self.getHeight()
		#print "THUMB MAX HEIGHT: %d" % (self.getHeight() - self.__smallFontHeight)
		#print "THUMB HEIGHT WITH LABEL: %d" % (self.__thumbHeight + self.__thumbMargin + (self.__fontHeight * 2))

		self.__nocoverArtImage = scaleImage(self.__nocoverArtImage, (self.__thumbWidth, self.__thumbHeight))
		self.__favImage = pygame.image.load(favImage).convert_alpha()
		self.__favImage = pygame.transform.scale(self.__favImage, (int(round(self.__thumbWidth * 0.25, 0)), int(round(self.__thumbHeight * 0.25, 0))))
		self.__visibleItems = self.__thumbsInX * self.__thumbsInY
		self.__showFavourites = False

	def __getStartIndex(self, index):
		return (index / self.__visibleItems) * self.__visibleItems

	def __setMenuItems(self, games):
		self.__menuItems = []
		for g in games:
			self.__menuItems.append(GameMenuItem(g))
		self.__menuItemsTotal = len(self.__menuItems)
		if self.__menuItemsTotal <= self.__visibleItems:
			self.__pageTotal = 1
		else:
			self.__pageTotal = math.ceil(float(self.__menuItemsTotal) / float(self.__visibleItems))
		self.__page = 1
		self.__selected = 0
		self.__startIndex = 0
		self.__menuItems[self.__selected].setSelected(True)
		self.__redraw = True

	def draw(self, x, y):
		x = 0 # ignore screen margin
		if self.isActive() and self.__redraw:
			self.fillBackground()
			thumbsWidth = (self.__thumbsInX * self.__thumbWidth) + ((self.__thumbsInX - 1) * self.__thumbMargin)
			startX = (self.getWidth() - thumbsWidth) / 2 
			nextX = startX

			nextY = y
			i = self.__startIndex
			col = 0
			label = None

			while i < self.__visibleItems + self.__startIndex and i < self.__menuItemsTotal:
				game = self.__menuItems[i].getGame()
				if not game.dataLoaded():
					# load the Game object's data if not already done so
					self.__menuItems[i].refresh()

				if self.__menuItems[i].isSelected():
					pygame.draw.rect(self.getBackground(), self.__colour, (nextX - 2, nextY - 2, self.__thumbWidth + 4, self.__thumbHeight + (self.__fontHeight * 2) + 4), 0)
					labelY = nextY + self.__thumbHeight
					for l in self.getLabels([self.__menuItems[i].getText()], self.__font, self.getBackgroundColour(), self.__colour, self.__thumbWidth, self.__fontHeight * 2):
						self.blit(l, (nextX, labelY))
						labelY += l.get_rect().height
				else:
					labelY = nextY + self.__thumbHeight
					for l in self.getLabels([self.__menuItems[i].getText()], self.__font, self.__colour, self.getBackgroundColour(), self.__thumbWidth, self.__fontHeight * 2):
						self.blit(l, (nextX, labelY))
						labelY += l.get_rect().height

				if game.getCoverArt() == None:
					self.blit(self.__nocoverArtImage, (nextX, nextY))
				else:
					image = self.__menuItems[i].getThumbnail(self.__thumbWidth, self.__thumbHeight)
					self.blit(image, (nextX, nextY))

				if game.isFavourite():
					self.blit(self.__favImage, ((nextX + self.__thumbWidth) - self.__favImage.get_width(), nextY))

				col += 1
				nextX += self.__thumbWidth + self.__thumbMargin
				if col == self.__thumbsInX:
					nextY += self.__thumbHeight + self.__thumbMargin + self.__fontHeight
					nextX = startX
					col = 0
				i += 1

			# draw page number in the bottom right hand corner
			self.__page = (self.__selected / self.__visibleItems) + 1
			pageLabel = self.__smallFont.render('Page %d of %d' % (self.__page, self.__pageTotal), 1, self.__colour, self.getBackgroundColour())
			pageLabelWidth = pageLabel.get_rect().width
			pageLabelHeight = pageLabel.get_rect().height
			self.blit(pageLabel, (self.getWidth() - (pageLabelWidth + 5), self.getHeight() - (pageLabelHeight + 5)))

			self.update(x, y)
			self.__redraw = False

	def handleEvent(self, event):
		if self.isActive():
			if event.type == KEYDOWN:
				if event.key == K_UP:
					self.__menuItems[self.__selected].setSelected(False)
					self.__selected -= self.__thumbsInX
					if self.__selected < 0:
						self.__selected = self.__menuItemsTotal - 1
						self.__startIndex = self.__getStartIndex(self.__selected)
					elif self.__selected < self.__startIndex:
						self.__startIndex = self.__getStartIndex(self.__selected)
					self.__menuItems[self.__selected].setSelected(True)
					self.__redraw = True
				elif event.key == K_DOWN:
					self.__menuItems[self.__selected].setSelected(False)
					self.__selected += self.__thumbsInX
					if self.__selected > self.__startIndex + self.__visibleItems - 1:
						self.__startIndex = self.__getStartIndex(self.__selected)
						if self.__startIndex < self.__menuItemsTotal:
							if self.__selected > self.__menuItemsTotal - 1:
								self.__selected = self.__startIndex
						else:
							self.__startIndex = 0
							self.__selected = 0
					elif self.__selected > self.__menuItemsTotal - 1:
						self.__startIndex = 0
						self.__selected = 0
					self.__menuItems[self.__selected].setSelected(True)
					self.__redraw = True
				elif event.key == K_LEFT:
					self.__menuItems[self.__selected].setSelected(False)
					self.__selected -= 1
					if self.__selected < 0:
						self.__selected = self.__menuItemsTotal - 1
						self.__startIndex = self.__getStartIndex(self.__selected)
					elif self.__selected < self.__startIndex:
						self.__startIndex = self.__selected - self.__visibleItems + 1
					self.__menuItems[self.__selected].setSelected(True)
					self.__redraw = True
				elif event.key == K_RIGHT:
					self.__menuItems[self.__selected].setSelected(False)
					self.__selected += 1
					if self.__selected > self.__menuItemsTotal - 1:
						self.__selected = 0
						self.__startIndex = 0
					elif self.__selected > self.__startIndex + self.__visibleItems - 1:
						self.__startIndex = self.__selected
					self.__menuItems[self.__selected].setSelected(True)
					self.__redraw = True
				elif event.key == K_i:
					self.fireEvent(EVENT_LOAD_GAME_INFO, [self.__console, self.__menuItems[self.__selected].getGame()])
				elif event.key == K_f:
					games = self.__console.getGames(not self.__showFavourites)
					if len(games) == 0:
						if self.__showFavourites:
							# should never get run, but just in case!
							self.fireEvent(EVENT_WARNING, ['No games found!'])
						else:
							self.fireEvent(EVENT_WARNING, ['No games have been added to your favourites!'])
					else:
						self.__showFavourites = not self.__showFavourites
						self.__setMenuItems(games)
				elif event.key == K_s:
					game = self.__menuItems[self.__selected].getGame()
					game.setFavourite(not game.isFavourite())
					game.save()
					self.__redraw = True
				elif event.key == K_PAGEUP:
					self.__menuItems[self.__selected].setSelected(False)
					if self.__selected - self.__visibleItems < 0:
						self.__selected = self.__menuItemsTotal - 1
						self.__startIndex = self.__getStartIndex(self.__selected)
					elif self.__selected == self.__menuItemsTotal - 1:
						self.__selected = self.__getStartIndex(self.__menuItemsTotal) - 1
						self.__startIndex = self.__getStartIndex(self.__selected)
					else:
						self.__selected -= self.__visibleItems
						self.__startIndex = self.__getStartIndex(self.__selected)
					self.__menuItems[self.__selected].setSelected(True)
					self.__redraw = True
				elif event.key == K_PAGEDOWN:
					self.__menuItems[self.__selected].setSelected(False)
					if self.__selected + self.__visibleItems > self.__menuItemsTotal - 1:
						self.__selected = 0
						self.__startIndex = 0
					else:
						self.__selected += self.__visibleItems
						self.__startIndex = self.__getStartIndex(self.__selected)
					self.__menuItems[self.__selected].setSelected(True)
					self.__redraw = True
				elif event.key == K_RETURN:
					return self.__menuItems[self.__selected].activate()
		return None

	def setActive(self, active):
		if active:
			games = None
			if self.__console.getFavouriteTotal() == 0:
				# if no favourites, then show all games
				games = self.__console.getGames()
				self.__showFavourites = False
			else:
				games = self.__console.getGames(self.__showFavourites)
			self.__setMenuItems(games)
			self.__redraw = True
		super(GamesMenu, self).setActive(active)

class AboutPanel(Panel):

	def __init__(self, width, height, font, fontSize, colour, bgColour, margins):
		super(AboutPanel, self).__init__(width, height, bgColour, 'About', margins)
		self.__margins = margins
		self.__colour = colour
		self.__font = pygame.font.Font(font, fontSize)
		self.__redraw = True

	def draw(self, x, y):
		currentY = 10

		if self.isActive() and self.__redraw:
			self.fillBackground()

			for l in self.getLabels(['Pi Entertainment System version %s' % VERSION_NUMBER, ' ', 'Released: %s' % VERSION_DATE, ' ', 'License: Licensed under version 3 of the GNU Public License (GPL)', ' ', 'Author: %s' % VERSION_AUTHOR, ' ', 'Contributors: Eric Smith', ' ', 'Cover art: theGamesDB.net', ' ', 'Documentataion: http://pes.mundayweb.com', ' ', 'Help: pes@mundayweb.com'], self.__font, self.__colour, self.getBackgroundColour(), self.getWidth() - self.__margins[0], self.getHeight()):
				self.blit(l, (0, currentY))
				currentY += l.get_rect().height

			self.update(x, y)
			self.__redraw = False

	def handleEvent(self, event):
		if self.isActive():
			return None

	def setActive(self, active):
		if active:
			self.__redraw = True
		super(AboutPanel, self).setActive(active)

class UpdateDbPanel(Panel):

	def __init__(self, width, height, font, fontSize, colour, bgColour, db, consoles, margins=[0,0,0,0]):
		super(UpdateDbPanel, self).__init__(width, height, bgColour, 'Update Database', margins)
		self.__margins = margins
		self.__font = pygame.font.Font(font, fontSize)
		self.__fontSize = fontSize
		self.__colour = colour
		self.__bgColour = bgColour
		self.__db = db
		self.__consoles = consoles
		self.__redraw = True
		self.__updateThread = UpdateDbThread(self.__db, self.__consoles)
		self.__progressSymbols = ['/', '-', '\\', '|']
		self.__progressIdx = 0
		self.__prevProgress = ''
		self.__abort = False
		self.__updateStarted = False

	def draw(self, x, y):
		if self.isActive() and self.__redraw:
			self.fillBackground()

			currentY = 10

			for l in self.getLabels(['PES will now scan your ROMs directory for any changes and will update your database accordingly. Depending on the number of changes this may take several minutes. You will not be able to exit this screen until the scan has completed or you decide to abort. The progress of the scan will be displayed below:'], self.__font, self.__colour, self.getBackgroundColour(), self.getWidth() - (self.__margins[0] + self.__margins[1]), self.getHeight()):
				self.blit(l, (0, currentY))
				currentY += l.get_rect().height

			currentY += 20

			if not self.__updateStarted and not self.__updateThread.hasStarted() and not self.__updateThread.hasFinished():
				logging.debug('starting update thread')
				self.lock()
				self.__updateThread.start()
				self.__updateStarted = True
			elif self.__updateThread.hasStarted() and not self.__updateThread.hasFinished():
				progress = self.__updateThread.getProgress()
				if progress == self.__prevProgress:
					progress += ' (%s)' % self.__progressSymbols[self.__progressIdx]
					self.__progressIdx += 1
					if self.__progressIdx > len(self.__progressSymbols) - 1:
						self.__progressIdx = 0
				else:
					self.__prevProgress = progress
					self.__progressIdx = 0
				label = self.__font.render(progress, 1, self.__colour, self.getBackgroundColour())
				self.blit(label, (0, currentY))	
				currentY += 20 + label.get_rect().height
				if not self.__abort:
					label = self.__font.render('Abort', 1, self.getBackgroundColour(), self.__colour)
				else:
					label = self.__font.render('Aborting...', 1, self.__colour, self.getBackgroundColour())
				self.blit(label, (0, currentY))
					
			elif self.__updateThread.hasFinished():
				logging.debug('update thread finished')
				self.fireEvent(EVENT_DATABASE_UPDATED)
				self.__redraw = False
				self.unlock()
				label = self.__font.render(self.__updateThread.getProgress(), 1, self.__colour, self.getBackgroundColour())
				self.blit(label, (0, currentY))	

			self.update(x, y)

	def handleEvent(self, event):
		if self.isActive():
			if self.__updateThread.hasStarted() and not self.__updateThread.hasFinished():
				if event.type == KEYDOWN:
					if not self.__abort and event.key == K_RETURN:
						logging.debug('stopping update thread...')
						self.__abort = True
						self.__updateThread.stop()

class JoyStickConfigurationPanel(Panel):

	def __init__(self, width, height, font, fontSize, colour, bgColour, configFile, retroarchJoysticksConfigDir):
		super(JoyStickConfigurationPanel, self).__init__(width, height, bgColour, 'Joystick Configuration')
		self.setHandleJoyStickEvents(True)
		self.__configFile = configFile
		self.__retroarchJoysticksConfigDir = retroarchJoysticksConfigDir
		self.__colour = colour
		self.__font = pygame.font.Font(font, fontSize)
		self.__redraw = True
		self.__lastBtn = None
		self.__prompts = ['Start', 'Select', 'Up', 'Down', 'Left', 'Right', 'A', 'B', 'X', 'Y', 'Shoulder L', 'Shoulder R', 'Shoulder L2', 'Shoulder R2', 'L3 Up', 'L3 Down', 'L3 Left', 'L3 Right', 'R3 Up', 'R3 Down', 'R3 Left', 'R3 Right', 'Exit Game', 'Save State', 'Load State']
		self.__btns = [JoyStick.BTN_START, JoyStick.BTN_SELECT, JoyStick.BTN_UP, JoyStick.BTN_DOWN, JoyStick.BTN_LEFT, JoyStick.BTN_RIGHT, JoyStick.BTN_A, JoyStick.BTN_B, JoyStick.BTN_X, JoyStick.BTN_Y, JoyStick.BTN_SHOULDER_LEFT, JoyStick.BTN_SHOULDER_RIGHT, JoyStick.BTN_SHOULDER_RIGHT2, JoyStick.BTN_SHOULDER_LEFT2, JoyStick.BTN_LEFT_AXIS_UP, JoyStick.BTN_LEFT_AXIS_DOWN, JoyStick.BTN_LEFT_AXIS_LEFT, JoyStick.BTN_LEFT_AXIS_RIGHT, JoyStick.BTN_RIGHT_AXIS_UP, JoyStick.BTN_RIGHT_AXIS_DOWN, JoyStick.BTN_RIGHT_AXIS_LEFT, JoyStick.BTN_RIGHT_AXIS_RIGHT, JoyStick.BTN_EXIT, JoyStick.BTN_SAVE_STATE, JoyStick.BTN_LOAD_STATE]
		self.__answers = []
		i = 0
		while i < len(self.__prompts):
			self.__answers.append(None)
			i += 1
		self.__promptIdx = 0
		self.__configComplete = False
		self.__error = False
		self.__errorMsg = ''
		self.__axisHistory = {}
		self.__firstPass = True

	def draw(self, x, y):
		if self.isActive() and self.__redraw:
			currentY = 10
			self.fillBackground()

			if self.__reinit:
				self.__jsDetect = True
				self.__secs = 11
				self.__reinit = False
				self.__configComplete = False
				self.__lastBtn = None
				self.__lastButtonTime = 0
				self.__lastTime = time.time()
				self.__currentTime = self.__lastTime
				self.__axisHistory = {}
				self.__firstPass = True

			if self.__configComplete:
				jsName = self.__js.get_name()
				# read in existing config
				configParser = ConfigParser.ConfigParser()
				configParser.read(self.__configFile)
				if configParser.has_section(jsName):
					configParser.remove_section(jsName)
					logging.debug('removed section for %s from config parser' % jsName)
				configParser.add_section(jsName)
				i = 0
				for b in self.__btns:
					configParser.set(jsName, b, str(self.__answers[i]))
					i += 1

				# save PES joystick settings
				logging.debug('saving PES joystick config for %s to %s' % (jsName, self.__configFile))
				with open(self.__configFile, 'wb') as f:
					configParser.write(f)

				# save RetroArch joystick settings
				if not os.path.exists(self.__retroarchJoysticksConfigDir):
					# something has gone wrong!
					logging.error("%s does not exist!" % self.__retroarchJoysticksConfigDir)
					print "Error! %s does not exist!" % self.__retroarchJoysticksConfigDir
					sys.exit(1)

				jsFile = self.__retroarchJoysticksConfigDir + os.sep + jsName + '.cfg'
				if os.path.exists(jsFile):
					logging.debug("overwriting: %s" % jsFile)
				else:
					logging.debug("creating: %s" % jsFile)

				js = JoyStick(jsName, configParser.items(jsName))
				with open(jsFile, 'wb') as f:
					f.write(js.getRetroArchConfig())

				self.fireEvent(EVENT_JOYSTICKS_UPDATED)
				
				self.setHandleJoyStickEvents(False)

				for l in self.getLabels(['Configuration of joystick %d is complete and has been saved! Press the button you have assigned as B to go back.' % (self.__jsIdx + 1)], self.__font, self.__colour, self.getBackgroundColour(), self.getWidth() - x, self.getHeight()):
					self.blit(l, (0, currentY))
					currentY += l.get_rect().height
				self.update(x, y)
				self.__redraw = False
				return

			if self.__jsDetect:
				if self.__currentTime > self.__lastTime:
					self.__secs -= self.__currentTime - self.__lastTime

				if self.__secs < 0:
					pygame.event.post(pygame.event.Event(KEYDOWN, {'key': K_BACKSPACE}))
					self.setActive(False)
					return

				self.__lastTime = self.__currentTime
				self.__currentTime = time.time()
				label = self.__font.render('Please press a button on the joystick you wish to configure (aborting in %ds)' % self.__secs, 1, self.__colour, self.getBackgroundColour())
				self.blit(label, (0, currentY))
			else:
				for l in self.getLabels(['Configuration for joystick %d, type: %s' % (self.__jsIdx + 1, self.__js.get_name()), ' ', 'These controls will be used both with PES and the emulators for ALL control pads of this type. You will be asked to press the "start" button first. If your control pad does not have a button that is asked for, press the button you have assigned to START to skip to the next button.', ' '], self.__font, self.__colour, self.getBackgroundColour(), self.getWidth() - x, self.getHeight()):
					self.blit(l, (0, currentY))
					currentY += l.get_rect().height

				label = self.__font.render('Press: %s' % self.__prompts[self.__promptIdx], 1, self.__colour, self.getBackgroundColour())
				self.blit(label, (0, currentY))

				configValue = None

				if self.__firstPass:
					logging.debug("joystick config: ignoring first button sweep")

					# check that all buttons are reset
					buttonSet = False
					for i in range(0, self.__js.get_numbuttons()):
						if self.__js.get_button(i):
							logging.debug("joystick %d button %d is set!" % (self.__js.get_id(), i))
							buttonSet = True
							break

					if not buttonSet:
						self.__firstPass = False
						self.__lastButton = -1
						self.__error = False
					else:
						self.__errorMsg = "Waiting for all buttons to reset..."
						self.__error = True
						logging.debug("joystick config: at least one button is not reset")
				else:
					# loop through buttons
					for i in range(0, self.__js.get_numbuttons()):
						if self.__js.get_button(i) and i != self.__lastButton:
							logging.debug("joystick config: joystick %d, button %d pressed" % (self.__js.get_id(), i))
							self.__lastButton = i
							self.__lastButtonTime = time.time()
							configValue = str(i)

					if configValue == None and time.time() - self.__lastButtonTime >= 1:
						# loop through axes
						for i in range(0, self.__js.get_numaxes()):
							value = self.__js.get_axis(i)

							if self.__lastAxis != i or (self.__lastAxis == i and ((value < 0 and self.__lastAxisValue > 0) or (value > 0 and self.__lastAxisValue < 0))):
								if abs(value) > 0.9 and abs(value - self.__initialAxis[i]) > 0.5:
									logging.debug("joystick config: joystick %d, axis %d, value: %f" % (self.__js.get_id(), i, value))
									self.__lastAxis = i
									self.__lastAxisValue = value
									if value > 0:
										configValue = "+%d" % i
									else:
										configValue = "-%d" % i

				if configValue:
					logging.debug("joystick config: looking for %s in joystick answers array" % configValue)
					if self.__promptIdx > 0 and self.__answers[0] == configValue:
						logging.debug("joystick config: skipping button assignment")
						self.__error = False
						self.__promptIdx += 1
						self.__lastButton = -1
						if self.__promptIdx == len(self.__prompts):
							logging.debug("joystick config: config complete!")
							self.__configComplete = True
					elif configValue in self.__answers:
						logging.debug("joystick config: button already assigned!")
						self.__errorMsg = 'This button has already been assigned. Please try again'
						self.__error = True
					else:
						self.__answers[self.__promptIdx] = configValue
						logging.debug("joystick config: setting %s button to %s in answers array" % (self.__prompts[self.__promptIdx], configValue))
						self.__promptIdx += 1
						self.__error = False
						if self.__promptIdx == len(self.__prompts):
							logging.debug("joystick config: config complete!")
							self.__configComplete = True

				if self.__error:
					currentY += label.get_rect().height * 2
					label = self.__font.render(self.__errorMsg, 1, self.__colour, self.getBackgroundColour())
					self.blit(label, (0, currentY))

				if not self.__configComplete:
					self.__redraw = False

			self.update(x, y)
			#self.__redraw = False

	def handleEvent(self, event):

		if self.isActive():
			if not self.__configComplete and (event.type == pygame.JOYBUTTONDOWN or event.type == pygame.JOYAXISMOTION):
				value = None
						
				self.__redraw = True
				if self.__jsDetect:
					if event.type == pygame.JOYBUTTONDOWN:
						logging.debug("joystick config: initial button press from joystick %d, button %d" % (event.joy, event.button))
						self.__jsIdx = event.joy
						self.__js = pygame.joystick.Joystick(event.joy)
						self.__initialAxis = []
						for i in range(0, self.__js.get_numaxes()):
							value =  self.__js.get_axis(i)
							logging.debug("joystick config: initial value for axis %d, value %f" % (i, value))
							if abs(value) > 0.5:
								self.__initialAxis.append(value)
							else:
								self.__initialAxis.append(0)

						self.__lastAxis = -1
						self.__lastAxisValue = 0
						self.__lastButton = event.button
						self.__lastButtonTime = 0
						self.__firstPass = True
						self.__jsDetect = False

	def setActive(self, active):
		super(JoyStickConfigurationPanel, self).setActive(active)
		self.__reinit = True
		self.__redraw = True

class Menu(Panel):

	def __init__(self, entries, width, height, font, fontSize, colour, bgColour, margins=[0,0,0,0], menuItemGap = 10):
		super(Menu, self).__init__(width, height, bgColour, '', margins)
		self.__marginTop = margins[2]
		self.__marginBottom = margins[3]
		self.__menuItemGap = menuItemGap
		self.__redraw = True
		self.__entries = entries
		self.__colour = colour
		self.__selected = 0
		self.__entries[self.__selected].setSelected(True)
		self.__font = pygame.font.Font(font, fontSize)
		self.__fontHeight = self.__font.size('A')[1]
		# work out number of visible items
		self.__startIndex = 0
		self.__maxVisibleItems = (self.getHeight() - self.__marginBottom - self.__marginTop) / (self.__fontHeight + self.__menuItemGap)
		self.__visibleItems = self.__maxVisibleItems
		self.__entriesTotal = len(self.__entries)
		if self.__visibleItems > self.__entriesTotal:
			self.__visibleItems = self.__entriesTotal 

	def draw(self, x, y):
		# x is where the panel is drawn
		# all x, y values for drawing labels should be relative to zero!
		if self.isActive() and self.__redraw:
			self.fillBackground()
			nextY = self.__marginTop
			i = self.__startIndex
			while i < self.__visibleItems + self.__startIndex: 
				if self.__entries[i].isSelected():
					label = self.__font.render(self.__entries[i].getText(), 1, self.getBackgroundColour(), self.__colour)
				else:
					label = self.__font.render(self.__entries[i].getText(), 1, self.__colour, self.getBackgroundColour())
				self.blit(label, (0, nextY))
				nextY += self.__fontHeight + self.__menuItemGap
				i += 1
			self.update(x, y)
			self.__redraw = False

	def handleEvent(self, event):
		if self.isActive():
			if event.type == KEYDOWN:
				if event.key == K_UP:
					self.__redraw = True
					if self.__selected - 1 >= 0:
						self.__entries[self.__selected].setSelected(False)
						self.__selected -= 1
						self.__entries[self.__selected].setSelected(True)
						if self.__selected == self.__startIndex - 1:
							self.__startIndex -= 1
					else:
						self.__entries[self.__selected].setSelected(False)
						self.__selected = self.__entriesTotal - 1
						self.__startIndex = self.__entriesTotal - self.__visibleItems
						self.__entries[self.__selected].setSelected(True)
				elif event.key == K_DOWN:
					self.__redraw = True
					if self.__selected + 1 < self.__entriesTotal:
						self.__entries[self.__selected].setSelected(False)
						self.__selected += 1
						self.__entries[self.__selected].setSelected(True)
						if self.__selected == self.__startIndex + self.__visibleItems:
							self.__startIndex += 1
					else:
						self.__entries[self.__selected].setSelected(False)
						self.__selected = 0
						self.__startIndex = 0
						self.__entries[self.__selected].setSelected(True)
				elif event.key == K_RETURN:
					self.__redraw = True
					#logging.debug('MenuItem %d selected' % self.__selected)
					return self.__entries[self.__selected].activate()

				#logging.debug('selected menu item: %d' % self.__selected)

		return None

	def setActive(self, active):
		if active:
			self.__redraw = True
		super(Menu, self).setActive(active)

	def setEntries(self, entries):
		self.__entries = entries
		self.__startIndex = 0
		self.__visibleItems = self.__maxVisibleItems
		self.__entriesTotal = len(self.__entries)
		if self.__visibleItems > self.__entriesTotal:
			self.__visibleItems = self.__entriesTotal 
		self.__selected = 0
		self.__entries[self.__selected].setSelected(True)
		i = 1
		while i < len(self.__entries):
			self.__entries[i].setSelected(False)
			i += 1
		self.__redraw = True

	def setSelected(self, i):
		self.__entries[self.__selected].setSelected(False)
		self.__selected = i
		self.__entries[self.__selected].setSelected(True)
		self.__redraw = True

class MenuItem(object): 

	def __init__(self, text, callback = None, *callbackArgs):
		self.__text = text
		self.__selected = False
		self.__callback = callback
		self.__callbackArgs = callbackArgs

	def activate(self):
		#logging.debug('menu item: "%s" activated!' % self.__text)
		if self.__callback:
			if self.__callbackArgs:
				return self.__callback(self.__callbackArgs)
			else:
				return self.__callback()

		return None

	def getText(self):
		return self.__text

	def isSelected(self):
		return self.__selected

	def setSelected(self, sel):
		if self.__selected != sel:
			self.__selected = sel

	def setText(self, text):
		self.__text = text

class MenuImgItem(MenuItem):

	def __init__(self, text, img, callback = None, *callbackArgs):
		super(MenuImgItem, self).__init__(text, callback, *callbackArgs)
		self.setImage(img)

	def getImageDimensions(self):
		if self.__imgDimensions == None:
			img = Image.open(self.__img)
			self.__imgDimensions = img.size
		return self.__imgDimensions

	def getThumbnail(self, width, height):
		if self.__thumbnail == None:
			if self.__img != None:
				 self.__thumbnail = scaleImage(pygame.image.load(self.__img).convert_alpha(), (width, height))

		return self.__thumbnail
		
	def setImage(self, img):
		self.__img = img
		self.__thumbnail = None
		self.__imgDimensions = None

class GameMenuItem(MenuImgItem):

	def __init__(self, game):
		if game.dataLoaded():
			super(GameMenuItem, self).__init__(game.getName(), game.getCoverArt())
		else:
			super(GameMenuItem, self).__init__("", None)
		self.__game = game

	def activate(self):
		# user has opted to play the game so update its stats
		self.__game.setLastPlayed()
		self.__game.setPlayCount()
		self.__game.save()
		return (self.__game.getCommand(), self.__game.getConsole().getEmulator())

	def getGame(self):
		return self.__game
		
	def refresh(self):
		self.__game.refresh()
		self.setText(self.__game.getName())
		self.setImage(self.__game.getCoverArt())

class GameInfoPanel(Panel):

	def __init__(self, width, height, font, fontSize, colour, bgColour, console, game, margins=[0,0,0,0]):
		self.__margins = margins
		self.__game = game
		self.__console = console
		super(GameInfoPanel, self).__init__(width, height, bgColour, self.__game.getName())
		self.__colour = colour
		self.__font = pygame.font.Font(font, fontSize)
		self.__redraw = True
		self.__menuItems = [MenuItem('Favourite: %s' % (self.__game.isFavourite(('Yes', 'No'))), self.favourite), MenuItem('Play', self.play)]
		self.__menu = Menu(self.__menuItems, 200, 80, font, fontSize, colour, bgColour, [0,0,0,0], 0)
		self.__menu.setSelected(1)
		self.__menu.setActive(True)

	def draw(self, x, y):
		currentY = 10

		if self.isActive() and self.__redraw:
			self.fillBackground()

			self.__menuItems[0].setText('Favourite: %s' % (self.__game.isFavourite(('Yes', 'No'))))

			width = self.getWidth()
			height = self.getHeight()

			coverArt = self.__game.getCoverArt()
			if coverArt == None:
				coverArt = self.__console.getNoCoverArtImg()

			img = Image.open(coverArt)
			ratio = min(float((width / 2.0) / img.size[0]), float((height / 2.0) / img.size[1]))
			imgWidth = img.size[0] * ratio
			imgHeight = img.size[1] * ratio

			currentX = (width - imgWidth) / 2
			currentY = y

			#logging.debug('drawing image %s at (%d, %d) using ratio: %f, panel dimensions: (%d, %d), scaled image dimensions: (%d, %d), original image dimensions: (%d, %d)' % (self.__coverArt, currentX, currentY, ratio, width, height, imgWidth, imgHeight, img.size[0], img.size[1]))

			# display cover art and description
			self.blit(scaleImage(pygame.image.load(coverArt).convert_alpha(), (imgWidth, imgHeight)), (currentX, currentY))

			released = self.__game.getReleased('%d/%m/%Y')
			if released == None:
				released = 'Unknown'

			lastPlayed = self.__game.getLastPlayed('%d/%m/%Y')
			if lastPlayed == None:
				lastPlayed = 'N/A'

			fileSize = getHumanReadableSize(self.__game.getSize())

			labels = self.getLabels(['Released: %s' % released, 'Last played: %s' % lastPlayed, 'Played: %d times' % self.__game.getPlayCount(), 'Size: %s' % fileSize], self.__font, self.__colour, self.getBackgroundColour(), width - (currentX + imgWidth) - 10, imgHeight)
			labelHeight = labels[0].get_rect().height
			currentX += imgWidth + 10
			for l in labels:
				self.blit(l, (currentX, currentY))
				currentY += labelHeight

			self.__menuX = currentX + x
			self.__menuY = currentY + y

			currentY = y + imgHeight + 20
			currentX = self.__margins[0]
			labels = self.getLabels([self.__game.getOverview().replace("\n", "")], self.__font, self.__colour, self.getBackgroundColour(), width - 100, height / 2)
			for l in labels:
				self.blit(l, (currentX, currentY))
				currentY += l.get_rect().height

			self.update(x, y)
			self.__menu.setActive(True)
			self.__menu.draw(self.__menuX, self.__menuY)

			self.__redraw = False

	def favourite(self):
		logging.debug('process favourite request for %s' % self.__game.getName())
		self.__game.setFavourite(not self.__game.isFavourite())
		self.__game.save()
		self.__redraw = True
		return None

	def handleEvent(self, event):
		if self.isActive():
			self.__menu.draw(self.__menuX, self.__menuY)
			rtn = self.__menu.handleEvent(event)
			self.__redraw = True
			return rtn

	def play(self):
		self.__game.setLastPlayed()
		self.__game.setPlayCount()
		self.__game.save()
		return (self.__console.getCommand(self.__game), self.__console.getEmulator())

	def setActive(self, active):
		if active:
			self.__redraw = True
		super(GameInfoPanel, self).setActive(active)

	def setGame(self, console, game):
		self.__console = console
		self.__game = game
		self.__menu.setSelected(1)
		self.setTitle(self.__game.getName())
		self.__redraw = True

