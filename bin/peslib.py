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
import json
import csv
import socket
import fcntl
import struct
from PIL import Image
from collections import OrderedDict
from Levenshtein import *

CEC_UP = 1
CEC_DOWN = 2
CEC_LEFT = 3
CEC_RIGHT = 4
CEC_ENTER = 0
CEC_EXIT = 13
CEC_RETURN = 145

EVENT_DATABASE_UPDATED = 1
EVENT_JOYSTICKS_UPDATED = 2
EVENT_MESSAGE_BOX_OK = 3

VERSION_NUMBER = '1.1'
VERSION_DATE = '2014-10-29'
VERSION_AUTHOR = 'Neil Munday'

verbose = False

def get_default_if(): 
    f = open('/proc/net/route') 
    for i in csv.DictReader(f, delimiter="\t"): 
        if long(i['Destination'], 16) == 0: 
            return i['Iface'] 
    return None 

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

def printMsg(msg):
        global verbose
        if verbose:
                print msg
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

	__fontColour = (255, 255, 0)
	__bgColour = (0, 0, 0)
	__screenMargin = 30
	__headerHeight = 30
	__footerHeight = 30
	__headerMaginBottom = 30
	__name = 'Pi Entertainment System'

	def __init__(self, window, commandFile):
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
		self.__confDir = self.__baseDir + os.sep + 'conf.d'
		self.__checkDir(self.__confDir)
		self.__pesConfigFile = self.__confDir + os.sep + 'pes.ini'
		self.__checkFile(self.__pesConfigFile)
		self.__consolesConfigFile = self.__confDir + os.sep + 'consoles.ini'
		self.__checkFile(self.__consolesConfigFile)
		self.__joysticksConfigFile = self.__confDir + os.sep + 'joysticks.ini'
                self.__checkFile(self.__joysticksConfigFile)
		self.__retroarchJoysticksConfigFile = self.__confDir + os.sep + 'retroarch-joysticks.cfg'
                self.__checkFile(self.__retroarchJoysticksConfigFile)
		self.__commandFile = commandFile

		# read in program settings
		configParser = ConfigParser.ConfigParser()
		configParser.read(self.__pesConfigFile)
		try:
			self.__fontFile = os.path.abspath(self.__baseDir + os.sep + configParser.get('pes', 'fontFile'))
			self.__romsDir = configParser.get('pes', 'romsDir')
			self.__nocoverImage = os.path.abspath(self.__baseDir + os.sep + configParser.get('pes', 'nocoverImage'))
			self.__rebootCommand = configParser.get('pes', 'rebootCommand')
			self.__shutdownCommand = configParser.get('pes', 'shutdownCommand')
			self.__tempCommand = configParser.get('pes', 'tempCommand')
		except ConfigParser.NoOptionError, e:
			self.__exit('Error parsing config file %s: %s' % (self.__pesConfigFile, e.message), True)
		
		self.__checkFile(self.__fontFile)
		self.__checkDir(self.__romsDir)

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


		# create database (if needed)
		con = sqlite3.connect(self.__userDb)
		try:
			cur = con.cursor()
			cur.execute('CREATE TABLE IF NOT EXISTS `games`(`game_id` INTEGER PRIMARY KEY, `api_id`, `exists` INT, `console_id` INT, `name` TEXT, `cover_art` TEXT, `game_path` TEXT)')
			cur.execute('CREATE TABLE IF NOT EXISTS `consoles`(`console_id` INTEGER PRIMARY KEY, `name` TEXT)')
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
				extensions = configParser.get(c, 'extensions').split(' ')
				command = configParser.get(c, 'command').replace('%%BASE%%', self.__baseDir)
				consoleImg = configParser.get(c, 'image').replace('%%BASE%%', self.__baseDir)
				self.__checkFile(consoleImg)
				nocoverart = configParser.get(c, 'nocoverart').replace('%%BASE%%', self.__baseDir)
				self.__checkFile(nocoverart)
				consoleId = configParser.get(c, 'id')
				console = Console(c, consoleId, extensions, self.__romsDir + os.sep + c, command, self.__userDb, consoleImg, nocoverart, self.__imgCacheDir)
				console.getGames(True)
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

		# detect joysticks
		self.loadJoysticks()
		self.detectJoysticks()

		# read initial temperature
		self.__checkTemp()

		# create settings menu
		menuItems = [MenuItem("Configure Joystick", self.__loadJoyStickConfiguration), MenuItem("Reset Database", self.__resetDb)]
                self.__settingsMenu = Menu(menuItems, self.__screenWidth, self.__screenHeight - (self.__footerHeight + self.__headerHeight), self.__fontFile, 20, self.__fontColour, self.__bgColour)

		# create about menu
		self.__aboutMenu = None
		
		# create consoles menu
		consoleMenuItems = []
		for c in self.__consoles:
			gameTotal = c.getGameTotal()
			consoleMenuItems.append(MenuImgItem("%s (%d)" % (c.getName(), gameTotal), c.getImg(), self.__loadGamesMenu, c))
		self.__consolesMenu = ThumbnailMenu(consoleMenuItems, self.__screenWidth, self.__screenHeight - (self.__footerHeight + self.__headerHeight), self.__fontFile, 20, self.__fontColour, self.__bgColour)

                # create main menu
		menuItems = []
		#consoleMenuItems = []

		#for c in self.__consoles:
		#	if c.getGameTotal() > 0:
		#		consoleMenuItems.append(MenuItem(c.getName(), self.__loadGamesMenu, c))

		menuItems.append(MenuItem("Games", self.__loadConsolesMenu))	
		menuItems.append(MenuItem('Update Database', self.__updateDb))
		menuItems.append(MenuItem("Settings", self.__loadSettingsMenu))
		menuItems.append(MenuItem("Reboot", self.__reboot))
		menuItems.append(MenuItem("Power Off", self.__poweroff))
		menuItems.append(MenuItem("About", self.__loadAboutMenu))
		menuItems.append(MenuItem("Exit to command line", self.__exit))

		self.__mainMenu = Menu(menuItems, self.__screenWidth, self.__screenHeight - (self.__footerHeight + self.__headerHeight), self.__fontFile, 20, self.__fontColour, self.__bgColour)
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
			printMsg("checking temp...")
			temp = float(subprocess.check_output(self.__tempCommand, shell=True)[:-1])
			temp /= 1000
			if self.__temp != temp:
				self.__temp = temp
				self.__footer.setField("Temp", "%.2fC" % temp)
			
		except subprocess.CalledProcessError, e:
			printMsg("CalledProcessError: %s", e.args)

	def __createRetroArchJoystickCfg(self):
		# generate RetroArch joystick config
		if self.__joystickTotal > 0:
			printMsg("generating RetroArch joystick configuration: %s" % self.__retroarchJoysticksConfigFile)
			with open(self.__retroarchJoysticksConfigFile, 'w') as f:
				f.write("# THIS FILE IS AUTOMATICALLY GENERATED BY PES #\n")
				f.write("# ANY MODIFICATIONS WILL BE LOST #\n")
				for i in range(0, self.__joystickTotal):
					js = pygame.joystick.Joystick(i)
					js.init()
					for j in self.__joysticks:
						if j.isMatch(js.get_name()):
							# we recognise this joystick
							f.write(j.getRetroArchConfig(i))
				if self.__joystick:
					f.write("input_load_state_btn = \"%s\"\n" % self.__joystick.getRetroArchButtonValue(JoyStick.BTN_LOAD_STATE))
					f.write("input_save_state_btn = \"%s\"\n" % self.__joystick.getRetroArchButtonValue(JoyStick.BTN_SAVE_STATE))
					f.write("input_exit_emulator_btn = \"%s\"\n" % self.__joystick.getRetroArchButtonValue(JoyStick.BTN_EXIT))

	def detectJoysticks(self):
		printMsg("Looking for joysticks...")
                if pygame.joystick.get_init():
                       pygame.joystick.quit()
                pygame.joystick.init()

                self.__js = None # PyGame joystick object
                self.__joystick = None # PES joystick object
                self.__joystickTotal = pygame.joystick.get_count()
                printMsg("Found %d joystick(s)" % self.__joystickTotal)
                if self.__joystickTotal > 0:
			primaryFound = False
			for i in range(0, self.__joystickTotal):
				js = pygame.joystick.Joystick(i)
				js.init()
				printMsg("Joystick %d: %s" % (i, js.get_name()))
				matchFound = False
				for j in self.__joysticks:
					if j.isMatch(js.get_name()):
						matchFound = True
						printMsg("joystick recognised: %s" % js.get_name())
						if not primaryFound:
							self.__joystick = j
							self.__js = js
							primaryFound = True
							break

				if not matchFound:
					printMsg("joystick not recognised!")

		self.__footer.setField("JoySticks", self.__joystickTotal)
		if self.__joystick == None:
			self.__footer.setField("Primary Joystick", "Disabled")
		else:
			#self.__footer.setField("Primary JoyStick", self.__joystick.getName())
			self.__footer.setField("Primary Joystick", "Pad %d" % (self.__js.get_id() + 1))

	def __exit(self, msg = None, error = False):
		if msg:
			print msg
		if error:
			#self.destroy()
			sys.exit(1)

		with open(self.__commandFile, 'w') as f:
			f.write('exit')

		sys.exit(0)

	def __getActiveMenu(self):
		return self.__menuStack[len(self.__menuStack) - 1]

	def __loadAboutMenu(self):
		if self.__aboutMenu == None:
			self.__aboutMenu = AboutPanel(self.__screenWidth, self.__screenHeight - (self.__footerHeight + self.__headerHeight), self.__fontFile, 18, self.__fontColour, self.__bgColour)
		activeMenu = self.__getActiveMenu()
		activeMenu.setActive(False)
		activeMenu = self.__aboutMenu
		activeMenu.setActive(True)
		self.__menuStack.append(activeMenu)
		self.__header.setTitle('%s: About' % self.__name)

	def __loadConsolesMenu(self):
		activeMenu = self.__getActiveMenu()
		activeMenu.setActive(False)
		activeMenu = self.__consolesMenu
		activeMenu.setActive(True)
		self.__menuStack.append(activeMenu)
		self.__header.setTitle('%s: Games' % self.__name)

	def __loadGamesMenu(self, args):
		console = args[0]
		if console.getGameTotal() > 0:
			activeMenu = self.__getActiveMenu()
			activeMenu.setActive(False)
			activeMenu = GamesMenu(console, self.__screenWidth, self.__screenHeight - (self.__footerHeight + self.__headerHeight), self.__fontFile, 18, self.__fontColour, self.__bgColour, self.__nocoverImage)
			activeMenu.setActive(True)
			self.__menuStack.append(activeMenu)
			self.__header.setTitle('%s: %s' % (self.__name, console.getName()))
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
		activeMenu = JoyStickConfigurationPanel(self.__screenWidth, self.__screenHeight - (self.__footerHeight + self.__headerHeight), self.__fontFile, 18, self.__fontColour, self.__bgColour, self.__joysticksConfigFile)
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
                printMsg("shutting down...")
                subprocess.call(self.__shutdownCommand, shell=True)

        def __reboot(self):
                printMsg("rebooting...")
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
				pygame.event.post(pygame.event.Event(KEYDOWN, {'key': K_ESCAPE}))
		elif dur == 500:
			if btn == CEC_RETURN:
				pygame.event.post(pygame.event.Event(KEYDOWN, {'key': K_BACKSPACE}))

	def __goBack(self):
		activeMenu = self.__getActiveMenu()
		activeMenu.setActive(False)
		self.__menuStack.pop()
		activeMenu = self.__getActiveMenu()
		activeMenu.setActive(True)
		if activeMenu == self.__mainMenu:
			self.__header.setTitle(self.__name)

	def processEvent(self, event):
		if event == EVENT_DATABASE_UPDATED:
			printMsg("Trapping PES event: database update")
			i = 0
			for c in self.__consoles:
				c.getGames(True)
				self.__consolesMenu.setLabelText(i, "%s (%d)" % (c.getName(), c.getGameTotal()))
				i += 1
			
		elif event == EVENT_JOYSTICKS_UPDATED:
			self.loadJoysticks()
			self.detectJoysticks()
		elif event == EVENT_MESSAGE_BOX_OK:
			printMsg("Trapping PES event: Message Box OK")
			self.__getActiveMenu().removeListener(self)
			self.__goBack()

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
		# generate a backspace key events to return to the main menu
		#pygame.event.post(pygame.event.Event(KEYDOWN, {'key': K_BACKSPACE}))
		#pygame.event.post(pygame.event.Event(KEYDOWN, {'key': K_BACKSPACE}))		
			
	def run(self):
                pygame.mouse.set_visible(False)
                fps = 20
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
			activeMenu.draw(self.__screenMargin, self.__header.getHeight())

			self.__footer.draw(5, self.__screenHeight - self.__footerHeight)

			# handle events
			for event in pygame.event.get():
				if event.type != pygame.KEYDOWN and event.type != pygame.JOYBUTTONDOWN:
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
							self.__createRetroArchJoystickCfg()
                                                        ok = False
				elif activeMenu.handlesJoyStickEvents():
					activeMenu.handleEvent(event)
				elif self.__joystick and self.__js.get_id() == event.joy and event.type == pygame.JOYBUTTONDOWN:
                                        if self.__joystick.getButton(event.button) == JoyStick.BTN_EXIT:
                                                #ok = False
						pass
                                        elif self.__joystick.getButton(event.button) == JoyStick.BTN_B:
                                                if not activeMenu.isLocked() and len(self.__menuStack) > 1:
							activeMenu.setActive(False)
							self.__menuStack.pop()
							activeMenu = self.__getActiveMenu()
							activeMenu.setActive(True)
							if activeMenu == self.__mainMenu:
								self.__header.setTitle(self.__name)
                                        else:
                                                e = self.__joystick.mapToKeyEvent(event.button)
                                                if e:
                                                        event = e
                                                        rtn = activeMenu.handleEvent(event)
                                                        if rtn != None:
								self.__createRetroArchJoystickCfg()
                                                                ok = False

                        frame += 1
			pygame.display.update()

		pygame.display.quit()
		pygame.quit()
		return rtn

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
		activeMenu = UpdateDbPanel(self.__screenWidth, self.__screenHeight - (self.__footerHeight + self.__headerHeight), self.__fontFile, 18, self.__fontColour, self.__bgColour, self.__userDb, self.__consoles)
		activeMenu.addListener(self)
		activeMenu.setActive(True)
		self.__menuStack.append(activeMenu)
		self.__header.setTitle('%s: %s' % (self.__name, 'Update Database'))

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
		printMsg('UpdateDbThread created')

	def run(self):
		printMsg('UpdateDbThread: started')
		self.__started = True
		url = 'http://pes.mundayweb.com/api.php?'

		con = None
		cur = None

		try:
			con = sqlite3.connect(self.__db)
			con.row_factory = sqlite3.Row
			cur = con.cursor()
		except sqlite3.Error, e:
			if con:
				con.rollback()
			print "Error: %s" % e.args[0]
			sys.exit(1)

		for c in self.__consoles:
			consoleName = c.getName()
			consoleId = c.getId()
			printMsg('UpdateDbThread: processing games for %s' % consoleName)
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
							for e in c.getExtensions():
								name = name.replace(e, '')

							self.__progress = 'Found game: %s' % name

							cur.execute('SELECT `game_id`, `name`, `cover_art`, `game_path` FROM `games` WHERE `game_path` = "%s";' % f)
							row = cur.fetchone()
							if row == None:
								self.__progress = 'Downloading data for game: %s' % name
								printMsg('downloading game info for %s' % name)
								# now grab thumbnail
								obj = { 'game_name': '%s' % name, 'platform_id': consoleId }
								data = urllib.urlencode(obj)
								urlLoaded = False
								jsonOk = False
								thumbPath = 0
								gameId = None
								nameLower = name.lower()
								bestName = name

								try:
									printMsg("loading: " + url + data)
									response = urllib2.urlopen(url + data)
									urlLoaded = True
								except urllib2.URLError, e:
									printMsg("an error occurred whilst trying to open: " + url + data)
									print e

								if urlLoaded:
									try:
										results = json.loads(response.read())
										jsonOk = True
									except ValueError, e:
										printMsg("error parsing JSON: %s", e)
							
								if jsonOk and int(results['number_of_total_results']) > 0:
									bestResultDistance = -1

									for r in results['results']:
										printMsg("potential result: %s" % r['name'])
										stringMatcher = StringMatcher(str(nameLower), str(r['name'].lower()))
										distance = stringMatcher.distance()
										if bestResultDistance == -1 or distance < bestResultDistance:
											bestResultDistance = distance
											bestName = r['name']
											gameId = r['id']

								if self.__stopCheck(con, cur):
									return

								if gameId != None:
									self.__progress = 'Match found: %s' % bestName
									printMsg("best match was: \"%s\" with a match rating of %d" % (bestName, bestResultDistance))
									obj = { 'game_id': gameId }
									data = urllib.urlencode(obj)

									urlLoaded = False

									try:
										response = urllib2.urlopen(url + data)
										urlLoaded = True
									except urllib2.URLError, e:
										printMsg("an error occurred whilst trying to open: " + url + data)
										print e

									if urlLoaded:
										jsonOk = False

										try:
											results = json.loads(response.read())
											jsonOk = True
										except ValueError, e:
											printMsg("error parsing JSON: %s", e)

										if jsonOk and results['results']['image']['small_url']:
											printMsg('Downloading cover art for %s' % name)
											self.__downloading = name
											self.__progress = 'Downloading cover art for %s' % name
											imgUrl = results['results']['image']['small_url']
											extension = imgUrl[imgUrl.rfind('.'):]
											thumbPath = c.getImgCacheDir() + os.sep + str(gameId) + extension
											urllib.urlretrieve(imgUrl, thumbPath)
								else:
									self.__progress = 'Could not find game data for %s' % name
									printMsg("Could not find game info for %s " % name)
									gameId = -1
								self.__progress = 'Adding %s to database...' % name
								cur.execute('INSERT INTO `games`(`exists`, `console_id`, `name`, `game_path`, `api_id`, `cover_art`) VALUES (1, %d, "%s", "%s", %d, "%s");' % (consoleId, bestName, f, gameId, thumbPath))
								con.commit()
							else:
								self.__progress = 'No need to update %s' % name
								printMsg("no need to download for %s" % name)
								coverArt = None
								if row['cover_art'] != '0':
									coverArt = row['cover_art']
								cur.execute('UPDATE `games` SET `exists` = 1 WHERE `game_id` = %s;' % row["game_id"])
								con.commit()

							if self.__stopCheck(con, cur):
								return

			except sqlite3.Error, e:
				print "Error: %s" % e.args[0]
				if con:
					con.rollback()
				self.__progress = 'An error occurred whilst updating the database'
				self.__finished = True
				return

		try:
			cur.execute('DELETE FROM `games` WHERE `exists` = 0')
			con.commit()
			printMsg('Closing database')
			con.close()
		except sqlite3.Error, e:
			print "Error: %s" % e.args[0]
			if con:
				con.rollback()
			self.__progress = 'An error occurred whilst updating the database'
			self.__finished = True

		self.__progress = 'Update complete'
		self.__finished = True
		printMsg('UpdateDbThread: finished')
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
					print "Error: %s" % e.args[0]
				
			self.__progress = 'Update interrupted!'
			self.__finished = True
			printMsg('UpdateDbThread: finished (interrupted)')
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
	BTN_SHOULDER_LEFT = 'btn_shoulder_left'
	BTN_SHOULDER_RIGHT = 'btn_shoulder_right'
	BTN_SHOULDER_LEFT2 = 'btn_shoulder_left2'
	BTN_SHOULDER_RIGHT2 = 'btn_shoulder_right2'
	BTN_SHOULDER_LEFT3 = 'btn_shoulder_left3'
	BTN_SHOULDER_RIGHT3 = 'btn_shoulder_right3'
        BTN_SAVE_STATE = 'btn_save_state'
	BTN_LOAD_STATE = 'btn_load_state'
	BTN_EXIT = 'btn_exit'

        def __init__(self, name, buttons):
		self.__name = name
		self.__matches = []
		self.__eventMap = {}
		self.__btnMap = {}
		for b in buttons:
			(key, value) = b
			#print "%s = %s" % (key, value)
			if value != 'None':
				if key[0:4] == 'btn_':
					self.__eventMap[int(value)] = key
					self.__btnMap[key] = value

        def getButton(self, event):
                if event in self.__eventMap:
                        return self.__eventMap[event]
                return None

	def getButtonValue(self, name):
		if name in self.__btnMap:
			return self.__btnMap[name]
		return None

        def getName(self):
                return self.__name

	def getRetroArchButtonValue(self, btn):
		if not btn in self.__btnMap:
			return 'nul'
		try:
			b = int(self.__btnMap[btn])
			return b
		except ValueError, e:
			return 'nul'

	def getRetroArchConfig(self, index):
		prefix = "input_player%d" % (index + 1) 
		cfg = "%s_joypad_index = \"%d\"\n" % (prefix, index)
		cfg += "%s_b_btn = \"%s\"\n" % (prefix, self.getRetroArchButtonValue(JoyStick.BTN_B))
		cfg += "%s_a_btn = \"%s\"\n" % (prefix, self.getRetroArchButtonValue(JoyStick.BTN_A))
		cfg += "%s_y_btn = \"%s\"\n" % (prefix, self.getRetroArchButtonValue(JoyStick.BTN_Y))
		cfg += "%s_x_btn = \"%s\"\n" % (prefix, self.getRetroArchButtonValue(JoyStick.BTN_X))
		cfg += "%s_l_btn = \"%s\"\n" % (prefix, self.getRetroArchButtonValue(JoyStick.BTN_SHOULDER_LEFT))
		cfg += "%s_r_btn = \"%s\"\n" % (prefix, self.getRetroArchButtonValue(JoyStick.BTN_SHOULDER_RIGHT))
		cfg += "%s_l2_btn = \"%s\"\n" % (prefix, self.getRetroArchButtonValue(JoyStick.BTN_SHOULDER_LEFT2))
		cfg += "%s_r2_btn = \"%s\"\n" % (prefix, self.getRetroArchButtonValue(JoyStick.BTN_SHOULDER_RIGHT2))
		cfg += "%s_l3_btn = \"%s\"\n" % (prefix, self.getRetroArchButtonValue(JoyStick.BTN_SHOULDER_LEFT3))
		cfg += "%s_r3_btn = \"%s\"\n" % (prefix, self.getRetroArchButtonValue(JoyStick.BTN_SHOULDER_RIGHT3))
		cfg += "%s_start_btn = \"%s\"\n" % (prefix, self.getRetroArchButtonValue(JoyStick.BTN_START))
		cfg += "%s_select_btn = \"%s\"\n" % (prefix, self.getRetroArchButtonValue(JoyStick.BTN_SELECT))
		cfg += "%s_up_btn = \"%s\"\n" % (prefix, self.getRetroArchButtonValue(JoyStick.BTN_UP))
		cfg += "%s_down_btn = \"%s\"\n" % (prefix, self.getRetroArchButtonValue(JoyStick.BTN_DOWN))
		cfg += "%s_left_btn = \"%s\"\n" % (prefix, self.getRetroArchButtonValue(JoyStick.BTN_LEFT))
		cfg += "%s_right_btn = \"%s\"\n" % (prefix, self.getRetroArchButtonValue(JoyStick.BTN_RIGHT))
		return cfg

	def isMatch(self, js):
		#for i in self.__matches:
		#	if i in js:
		#		return True
		#return False
		return self.__name == js

        def mapToKeyEvent(self, event):
                if event in self.__eventMap:
                        if self.__eventMap[event] == JoyStick.BTN_A:
                                return pygame.event.Event(KEYDOWN, {'key': K_RETURN})
                        if self.__eventMap[event] == JoyStick.BTN_B:
                                return pygame.event.Event(KEYDOWN, {'key': K_BACKSPACE})
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
                return None

class Console(object):

	def __init__(self, name, consoleId, extensions, romDir, command, db, consoleImg, noCoverArtImg, imgCacheDir):
		self.__id = int(consoleId)
		self.__name = name
		self.__extensions = extensions
		self.__romDir = romDir
		self.__consoleImg = consoleImg
		self.__noCoverArtImg = noCoverArtImg
		self.__games = []
		self.__refresh = True
		self.__command = command
		self.__db = db
		self.__imgCacheDir = imgCacheDir
		self.__gameTotal = 0

		try:
			con = sqlite3.connect(self.__db)
			con.row_factory = sqlite3.Row
			cur = con.cursor()
			cur.execute('SELECT `name` FROM `consoles` WHERE `console_id` = %d;' % self.__id)
			row = cur.fetchone()
			if row == None:
				printMsg('Adding console %s to database' % self.__name)
				cur.execute('INSERT INTO `consoles` VALUES (%d, "%s")' % (self.__id, self.__name))
				con.commit()
		except sqlite3.Error, e:
			print "Error: %s" % e.args[0]
			sys.exit(1)
		finally:
			if con:
				con.close()


	def getCommand(self, game):
		return self.__command.replace('%%GAME%%', "\"%s\"" % game.getPath())

	def getDir(self):
		return self.__dir

	def getGames(self, refresh = False):
		if self.__refresh or refresh:
			try:
				con = sqlite3.connect(self.__db)
				con.row_factory = sqlite3.Row
				cur = con.cursor()
				cur.execute('SELECT `name`, `game_path`, `cover_art` FROM `games` WHERE `console_id` = %d ORDER BY `name`;' % self.__id)
				self.__games = []
				while True:
					row = cur.fetchone()
					if row == None:
						break
					coverArt = None
					if row['cover_art'] != '0':
						coverArt = row['cover_art']
					else:
						coverArt = self.__noCoverArtImg
					self.__games.append(Game(row['name'], row['game_path'], self, coverArt))
			except sqlite3.Error, e:
				print "Error: %s" % e.args[0]
				sys.exit(1)
			finally:
				if con:
					con.close()

		return self.__games

	def getGameTotal(self):
		return len(self.__games)

	def getExtensions(self):
		return self.__extensions

	def getId(self):
		return self.__id

	def getImgCacheDir(self):
		return self.__imgCacheDir
	
	def getImg(self):
		return self.__consoleImg

	def getName(self):
		return self.__name

	def getRomDir(self):
		return self.__romDir		

class Game(object):

	def __init__(self, name, path, console, imagePath = None):
		self.__name = name
		self.__path = path
		self.__console = console
		self.__imagePath = imagePath

	def getCommand(self):
		return self.__console.getCommand(self)

	def getConsole(self):
		return self.__console

	def getImagePath(self):
		return self.__imagePath

	def getName(self):
		return self.__name

	def getPath(self):
		return self.__path

class Panel(object):

	def __init__(self, width, height, bgColour):
		self.__active = False
		self.__width = width
		self.__height = height
		self.__bgColour = bgColour
		self.__background = pygame.Surface((self.__width, self.__height)).convert()
		self.__handleJoyStickEvents = False
		self.__locked = False
		self.__listeners = []

	def addListener(self, l):
		self.__listeners.append(l)

	def blit(self, obj, coords, area=None):
		self.__background.blit(obj, coords, area)

	def fireEvent(self, event):
		for l in self.__listeners:
			l.processEvent(event)

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

	def __init__(self, menuItems, width, height, font, fontSize, colour, bgColour, thumbsPerRow=3, fitToHeight=True):
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
			self.__thumbsInY = int((self.__menuItemsTotal / thumbsPerRow) + 0.5)
			marginSpace = (self.__fontHeight + self.__thumbMargin) * (self.__thumbsInY + 1)
			self.__thumbHeight = (height - marginSpace) / self.__thumbsInY
			imgRatio = float(imgWidth) / float(imgHeight)
			self.__thumbWidth = int(self.__thumbHeight * imgRatio)
			self.__thumbsInX = thumbsPerRow
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
		
		#printMsg("thumbs in X: %d" % self.__thumbsInX)
		#
		#printMsg("thumbs in Y: %d" % self.__thumbsInY)
		self.__visibleItems = self.__thumbsInX * self.__thumbsInY
		self.__pageTotal = int(self.__menuItemsTotal / self.__visibleItems)
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

	def __init__(self, console, width, height, font, fontSize, colour, bgColour, nocoverImage):
		super(GamesMenu, self).__init__(width, height, bgColour)
		self.__thumbWidth = int(width / 6)
		self.__thumbHeight = int(self.__thumbWidth * 1.2)
		self.__thumbMargin = 40
		self.__entries = []
		for g in console.getGames():
			self.__entries.append(GameMenuItem(g))
		self.__entriesTotal = len(self.__entries)
		self.__colour = colour
		self.__selected = 0
		self.__startIndex = 0
		self.__entries[self.__selected].setSelected(True)
		self.__font = pygame.font.Font(font, fontSize)
		self.__fontHeight = self.__font.size('A')[1]
		self.__nocoverImage = pygame.image.load(nocoverImage).convert()
		self.__nocoverImage = pygame.transform.scale(self.__nocoverImage, (self.__thumbWidth, self.__thumbHeight))

		self.__thumbsInX = self.getWidth() / (self.__thumbWidth + self.__thumbMargin)
		self.__thumbsInY = self.getHeight() / (self.__thumbHeight + self.__thumbMargin + (self.__fontHeight * 2))
		self.__visibleItems = self.__thumbsInX * self.__thumbsInY
		self.__pageTotal = int(self.__entriesTotal / self.__visibleItems)

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

			while i < self.__visibleItems + self.__startIndex and i < self.__entriesTotal:
				if self.__entries[i].isSelected():
					pygame.draw.rect(self.getBackground(), self.__colour, (nextX - 2, nextY - 2, self.__thumbWidth + 4, self.__thumbHeight + (self.__fontHeight * 2) + 4), 0)
					labelY = nextY + self.__thumbHeight
					for l in self.getLabels([self.__entries[i].getText()], self.__font, self.getBackgroundColour(), self.__colour, self.__thumbWidth, self.__fontHeight * 2):
						self.blit(l, (nextX, labelY))
						labelY += l.get_rect().height
				else:
					labelY = nextY + self.__thumbHeight
					for l in self.getLabels([self.__entries[i].getText()], self.__font, self.__colour, self.getBackgroundColour(), self.__thumbWidth, self.__fontHeight * 2):
						self.blit(l, (nextX, labelY))
						labelY += l.get_rect().height

				if self.__entries[i].getGame().getImagePath() == None:
					self.blit(self.__nocoverImage, (nextX, nextY))
				else:
                                        image = self.__entries[i].getThumbnail(self.__thumbWidth, self.__thumbHeight)
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
					self.__entries[self.__selected].setSelected(False)
					self.__selected -= self.__thumbsInX
					if self.__selected < 0:
						self.__selected = self.__entriesTotal - 1
						self.__startIndex = self.__getStartIndex(self.__selected)
					elif self.__selected < self.__startIndex:
						self.__startIndex = self.__getStartIndex(self.__selected)
					self.__entries[self.__selected].setSelected(True)
					self.__redraw = True
				elif event.key == K_DOWN:
					self.__entries[self.__selected].setSelected(False)
					self.__selected += self.__thumbsInX
					if self.__selected > self.__startIndex + self.__visibleItems - 1:
						self.__startIndex = self.__getStartIndex(self.__selected)
						if self.__startIndex < self.__entriesTotal:
							if self.__selected > self.__entriesTotal - 1:
								self.__selected = self.__startIndex
						else:
							self.__startIndex = 0
							self.__selected = 0
					elif self.__selected > self.__entriesTotal - 1:
						self.__startIndex = 0
						self.__selected = 0
					self.__entries[self.__selected].setSelected(True)
					self.__redraw = True
				elif event.key == K_LEFT:
					self.__entries[self.__selected].setSelected(False)
					self.__selected -= 1
					if self.__selected < 0:
						self.__selected = self.__entriesTotal - 1
						self.__startIndex = self.__getStartIndex(self.__selected)
					elif self.__selected < self.__startIndex:
						self.__startIndex = self.__selected - self.__visibleItems + 1
					self.__entries[self.__selected].setSelected(True)
					self.__redraw = True
				elif event.key == K_RIGHT:
					self.__entries[self.__selected].setSelected(False)
					self.__selected += 1
					if self.__selected > self.__entriesTotal - 1:
						self.__selected = 0
						self.__startIndex = 0
					elif self.__selected > self.__startIndex + self.__visibleItems - 1:
						self.__startIndex = self.__selected
					self.__entries[self.__selected].setSelected(True)
					self.__redraw = True
				elif event.key == K_RETURN:
					return self.__entries[self.__selected].activate()
		return None

class AboutPanel(Panel):

	def __init__(self, width, height, font, fontSize, colour, bgColour):
		super(AboutPanel, self).__init__(width, height, bgColour)
		self.__colour = colour
		self.__font = pygame.font.Font(font, fontSize)
		self.__redraw = True

	def draw(self, x, y):
		currentY = 10

		if self.isActive() and self.__redraw:
			self.fillBackground()

			for l in self.getLabels(['Pi Entertainment System version %s' % VERSION_NUMBER, ' ', 'Author: %s' % VERSION_AUTHOR, ' ', 'Released: %s' % VERSION_DATE, ' ', 'License: Licensed under version 3 of the GNU Public License (GPL)', ' ', 'Art work: Eric Smith', ' ', 'Documentataion: http://pes.mundayweb.com', ' ', 'Help: pes@mundayweb.com'], self.__font, self.__colour, self.getBackgroundColour(), self.getWidth() - x, self.getHeight()):
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

	def __init__(self, width, height, font, fontSize, colour, bgColour, db, consoles):
		super(UpdateDbPanel, self).__init__(width, height, bgColour)
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

			for l in self.getLabels(['PES will now scan your ROMs directory for any changes and will update your database accordingly. Depending on the number of changes this may take several minutes. You will not be able to exit this screen until the scan has completed or you decide to abort. The progress of the scan will be displayed below:'], self.__font, self.__colour, self.getBackgroundColour(), self.getWidth() - x, self.getHeight()):
				self.blit(l, (0, currentY))
				currentY += l.get_rect().height

			currentY += 20

			if not self.__updateStarted and not self.__updateThread.hasStarted() and not self.__updateThread.hasFinished():
				printMsg('Starting update thread')
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
				printMsg('Update thread finished')
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
						printMsg('Stopping update thread...')
						self.__abort = True
						self.__updateThread.stop()

class JoyStickConfigurationPanel(Panel):

	def __init__(self, width, height, font, fontSize, colour, bgColour, configFile):
		super(JoyStickConfigurationPanel, self).__init__(width, height, bgColour)
		self.setHandleJoyStickEvents(True)
		self.__configFile = configFile
		self.__colour = colour
		self.__font = pygame.font.Font(font, fontSize)
		self.__redraw = True
		self.__lastBtn = None
		self.__prompts = ['Start', 'Select', 'Up', 'Down', 'Left', 'Right', 'A', 'B', 'X', 'Y', 'Shoulder L', 'Shoulder R', 'Shoulder L2', 'Shoulder R2', 'Exit Game', 'Save State', 'Load State']
		self.__btns = [JoyStick.BTN_START, JoyStick.BTN_SELECT, JoyStick.BTN_UP, JoyStick.BTN_DOWN, JoyStick.BTN_LEFT, JoyStick.BTN_RIGHT, JoyStick.BTN_A, JoyStick.BTN_B, JoyStick.BTN_X, JoyStick.BTN_Y, JoyStick.BTN_SHOULDER_LEFT, JoyStick.BTN_SHOULDER_RIGHT, JoyStick.BTN_SHOULDER_RIGHT2, JoyStick.BTN_SHOULDER_LEFT2, JoyStick.BTN_EXIT, JoyStick.BTN_SAVE_STATE, JoyStick.BTN_LOAD_STATE]
		self.__answers = []
		i = 0
		while i < len(self.__prompts):
			self.__answers.append(None)
			i += 1
		self.__promptIdx = 0
		self.__configComplete = False
		self.__error = False
		self.__errorMsg = ''

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
				self.__lastTime = time.time()
				self.__currentTime = self.__lastTime

			if self.__configComplete:
				jsName = self.__js.get_name()
				# read in existing config
				configParser = ConfigParser.ConfigParser()
				configParser.read(self.__configFile)
				if configParser.has_section(jsName):
					configParser.remove_section(jsName)
					printMsg('Removed section for %s from config parser' % jsName)
				configParser.add_section(jsName)
				i = 0
				for b in self.__btns:
					configParser.set(jsName, b, self.__answers[i])
					i += 1

				with open(self.__configFile, 'wb') as configfile:
					# save PES joystick settings
					configParser.write(configfile)
					# emulator joystick settings will be generated on the fly prior to each game launch

				#pes.loadJoysticks()
				#pes.detectJoysticks()
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

				if self.__error:
					currentY += label.get_rect().height * 2
					label = self.__font.render(self.__errorMsg, 1, self.__colour, self.getBackgroundColour())
					self.blit(label, (0, currentY))

				self.__redraw = False

			self.update(x, y)
			#self.__redraw = False

	def handleEvent(self, event):
		if self.isActive():
			if not self.__configComplete and event.type == pygame.JOYBUTTONDOWN:
				self.__redraw = True
				if self.__jsDetect:
					self.__jsIdx = event.joy
					self.__js = pygame.joystick.Joystick(event.joy)
					self.__jsDetect = False
				else:
					if self.__promptIdx > 0:
						if event.button == self.__answers[0]:
							self.__answers[self.__promptIdx] = None
						else:
							# look for clashes
							if event.button in self.__answers:
								self.__error = True
								self.__errorMsg = 'This button has already been assigned. Please try again'
								printMsg('Button %d has already been assigned for joystick %d' % (event.button, self.__jsIdx))
							else:
								self.__answers[self.__promptIdx] = event.button
								self.__error = False
					else:
						self.__answers[self.__promptIdx] = event.button

					if not self.__error:
						self.__promptIdx += 1

						if self.__promptIdx == len(self.__prompts):
							self.__configComplete = True

	def setActive(self, active):
		super(JoyStickConfigurationPanel, self).setActive(active)
		self.__reinit = True
		self.__redraw = True

class Menu(Panel):

	__marginTop = 20
	__marginBottom = 20
	__menuItemGap = 10

	def __init__(self, entries, width, height, font, fontSize, colour, bgColour):
		super(Menu, self).__init__(width, height, bgColour)
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
		if self.isActive() and self.__redraw:
			self.fillBackground()
			nextY = self.__marginTop
			i = self.__startIndex
			while i < self.__visibleItems + self.__startIndex: 
				if self.__entries[i].isSelected():
					label = self.__font.render(self.__entries[i].getText(), 1, self.getBackgroundColour(), self.__colour)
				else:
					label = self.__font.render(self.__entries[i].getText(), 1, self.__colour, self.getBackgroundColour())
				self.blit(label, (x, nextY))
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
					return self.__entries[self.__selected].activate()

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

class MenuItem(object): 

	def __init__(self, text, callback = None, *callbackArgs):
		self.__text = text
		self.__selected = False
		self.__callback = callback
		self.__callbackArgs = callbackArgs

	def activate(self):
		if self.__callback:
			if self.__callbackArgs:
				self.__callback(self.__callbackArgs)
			else:
				self.__callback()

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
		self.__img = img
		self.__thumbnail = None
		self.__imgDimensions = None

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

class GameMenuItem(MenuImgItem):
	def __init__(self, game):
		super(GameMenuItem, self).__init__(game.getName(), game.getImagePath())
		self.__game = game

	def activate(self):
		return self.__game.getCommand()

	def getGame(self):
		return self.__game


