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

from ctypes import c_int, c_uint32, byref
from datetime import datetime
from pes import *
from pes.data import *
from pes.util import *
from PIL import Image
from collections import OrderedDict
from xml.etree import ElementTree
from xml.etree.ElementTree import Element, SubElement
import glob
import logging
import math
import ConfigParser
import sdl2
import sdl2.video
import sdl2.render
import sdl2.ext
import sdl2.sdlgfx
import sdl2.sdlttf
import sdl2.joystick
import sdl2.timer
import sqlite3
import sys
import threading
import time
import urllib
import urllib2

def createText(renderer, font, txt, colour, wrap=0):
	if wrap > 0:
		surface = sdl2.sdlttf.TTF_RenderText_Blended_Wrapped(font, txt, colour, wrap)
	else:
		surface = sdl2.sdlttf.TTF_RenderText_Blended(font, txt, colour)
	texture = sdl2.SDL_CreateTextureFromSurface(renderer, surface)
	sdl2.SDL_FreeSurface(surface)
	return texture

def getFontHeight(font):
	s = sdl2.sdlttf.TTF_RenderText_Blended(font, 'A', sdl2.SDL_Color(0, 0, 0))
	h = s.contents.h
	sdl2.SDL_FreeSurface(s)
	return h

def renderLines(renderer, font, lines, colour, x, y, wrap):
	w = 0
	totalHeight = 0
	for l in lines:
		(w, h) = renderText(renderer, font, l, colour, x, y, wrap)
		y += h
		totalHeight += h
	return (w, totalHeight)

def renderText(renderer, font, txt, colour, x, y, wrap=0):
	texture = createText(renderer, font, txt, colour, wrap)
	(w, h) = getTextureDimensions(texture)
	sdl2.SDL_RenderCopy(renderer, texture, None, sdl2.SDL_Rect(x, y, w, h))
	sdl2.SDL_DestroyTexture(texture)
	return (w, h)
	
def getTextureDimensions(texture):
	flags = c_uint32()
	access = c_int()
	w = c_int()
	h = c_int()
	ret = sdl2.SDL_QueryTexture(texture, byref(flags), byref(access), byref(w), byref(h))
	return (w.value, h.value)

class PESApp(object):
	
	def __del__(self):
		logging.debug("PESApp.del: deleting object")
		if getattr(self, "__window", None):
			logging.debug("PESApp.del: window destroyed")
			sdl2.video.SDL_DestroyWindow(self.__window)
			self.__window = None

	#def __init__(self, dimensions, fontFile, backgroundColour, menuBackgroundColour, headerBackgroundColour, lineColour, textColour, menuTextColour, menuSelectedTextColour, consoles):
	def __init__(self, dimensions, fontFile, romsDir, coverartDir, backgroundColour, menuBackgroundColour, headerBackgroundColour, lineColour, textColour, menuTextColour, menuSelectedTextColour):
		super(PESApp, self).__init__()
		self.__dimensions = dimensions
		self.fontFile = fontFile
		self.romsDir = romsDir
		self.coverartDir = coverartDir
		#self.consoles = consoles
		self.consoles = []
		
		self.lineColour = sdl2.SDL_Color(lineColour[0], lineColour[1], lineColour[2])
		self.backgroundColour = sdl2.SDL_Color(backgroundColour[0], backgroundColour[1], backgroundColour[2])
		self.headerBackgroundColour = sdl2.SDL_Color(headerBackgroundColour[0], headerBackgroundColour[1], headerBackgroundColour[2])
		self.menuBackgroundColour = sdl2.SDL_Color(menuBackgroundColour[0], menuBackgroundColour[1], menuBackgroundColour[2])
		self.menuTextColour = sdl2.SDL_Color(menuTextColour[0], menuTextColour[1], menuTextColour[2])
		self.menuSelectedTextColour = sdl2.SDL_Color(menuSelectedTextColour[0], menuSelectedTextColour[1], menuSelectedTextColour[2])
		self.menuSelectedBgColour = self.lineColour
		self.textColour = sdl2.SDL_Color(textColour[0], textColour[1], textColour[2])
		
		self.__headerHeight = 30
		#self.__footerHeight = self.__headerHeight
		self.__footerHeight = 0
		
		# redraw hints
		#self.redrawMainMenu = True
		#self.__screenChange = True
		# call SDL2 directly to probe joysticks
		#SDL_Init(SDL_INIT_JOYSTICK)
		#self.joystickTotal = SDLJoystick.SDL_NumJoysticks()
		#print "Joysticks: %d " % self.joystickTotal
		#for i in range(0, self.joystickTotal):
		#   print SDLJoystick.SDL_JoystickNameForIndex(i)
		
	def initScreens(self):
		self.screens["Home"] = HomeScreen(self, self.renderer, self.menuRect, self.screenRect)
		self.screens["Settings"] = SettingsScreen(self, self.renderer, self.menuRect, self.screenRect)
		self.screenStack = ["Home"]
		
	def exit(self, rtn=0):
		# tidy up
		logging.debug("stopping screens...")
		for s in self.screens:
			self.screens[s].stop()
		logging.debug("tidying up...")
		sdl2.sdlttf.TTF_CloseFont(self.headerFont)
		sdl2.sdlttf.TTF_CloseFont(self.bodyFont)
		sdl2.sdlttf.TTF_CloseFont(self.menuFont)
		sdl2.sdlttf.TTF_CloseFont(self.titleFont)
		sdl2.sdlttf.TTF_CloseFont(self.splashFont)
		sdl2.sdlttf.TTF_Quit()
		sdl2.SDL_Quit()
		logging.info("exiting...")
		sys.exit(rtn)
        
	def run(self):
		sdl2.SDL_Init(sdl2.SDL_INIT_EVERYTHING)
		sdl2.SDL_ShowCursor(0)
		sdl2.sdlttf.TTF_Init()
		videoMode = sdl2.video.SDL_DisplayMode()
		if sdl2.video.SDL_GetDesktopDisplayMode(0, videoMode) != 0:
			pesExit("PESApp.run: unable to get current video mode!")
			
		logging.debug("PESApp.run: video mode (%d, %d), refresh rate: %dHz" % (videoMode.w, videoMode.h, videoMode.refresh_rate))
		
		if self.__dimensions[0] == 0 or self.__dimensions == 0:
			# assume full screen
			logging.debug("PESApp.run: running fullscreen")
			self.__dimensions = (videoMode.w, videoMode.h)
			self.__window = sdl2.video.SDL_CreateWindow('PES', sdl2.video.SDL_WINDOWPOS_UNDEFINED, sdl2.video.SDL_WINDOWPOS_UNDEFINED, self.__dimensions[0], self.__dimensions[1], self.__dimensions[0], self.__dimensions[1], sdl2.video.SDL_WINDOW_FULLSCREEN_DESKTOP)
		else:
			# windowed
			logging.debug("PESApp.run: running windowed")
			self.__window = sdl2.video.SDL_CreateWindow('PES', sdl2.video.SDL_WINDOWPOS_UNDEFINED, sdl2.video.SDL_WINDOWPOS_UNDEFINED, self.__dimensions[0], self.__dimensions[1], 0)
		
		self.menuWidth = 200
		self.menuHeight = self.__dimensions[1] - self.__footerHeight - self.__headerHeight
		
		self.menuRect = [0, self.__headerHeight + 1, self.menuWidth, self.__dimensions[1] - self.__headerHeight + 1]
		self.screenRect = [self.menuWidth + 1, self.__headerHeight + 1, self.__dimensions[0] - self.menuWidth + 1, self.__dimensions[1] - self.__headerHeight + 1]
		
		#self.__joystickTotal = sdl2.joystick.SDL_NumJoysticks()
        ##print "Joysticks: %d " % self.__joystickTotal
        ##for i in range(0, self.__joystickTotal):
        #   print sdl2.joystick.SDL_JoystickNameForIndex(i)
		
		logging.debug("PESApp.run: window dimensions: (%d, %d)" % (self.__dimensions[0], self.__dimensions[1]))
		
		self.splashFont = sdl2.sdlttf.TTF_OpenFont(self.fontFile, 50)
		self.menuFont = sdl2.sdlttf.TTF_OpenFont(self.fontFile, 20)
		self.headerFont = sdl2.sdlttf.TTF_OpenFont(self.fontFile, 22)
		self.titleFont = sdl2.sdlttf.TTF_OpenFont(self.fontFile, 20)
		self.bodyFont = sdl2.sdlttf.TTF_OpenFont(self.fontFile, 18)
		self.bodyFontHeight = getFontHeight(self.bodyFont)
		
		self.renderer = sdl2.SDL_CreateRenderer(self.__window, -1, sdl2.render.SDL_RENDERER_ACCELERATED)
		#sdl2.SDL_RenderSetLogicalSize(renderer, 1024, 576)
		
		# pre-initialise screens
		self.screens = {}
		
		headerTexture = createText(self.renderer, self.headerFont, "Pi Entertainment System", self.textColour)
		(headerTextureWidth, headerTextureHeight) = getTextureDimensions(headerTexture)
		
		dateTexture = None
		
		splashTexture = createText(self.renderer, self.splashFont, "Pi Entertainment System", self.textColour)
		(splashTextureWidth, splashTextureHeight) = getTextureDimensions(splashTexture)
		splashTextureX = int((self.__dimensions[0] - splashTextureWidth) / 2)
		splashTextureY = ((self.__dimensions[1]) / 2) - splashTextureHeight
		
		running = True
		loading = True
		
		splashTextFadeTime = 10
		lastTick = sdl2.timer.SDL_GetTicks()
		splashTextureAlpha = 25
		progressBarWidth = splashTextureWidth
		progressBarHeight = 40
		progressBarX = splashTextureX
		progressBarY = splashTextureY + splashTextureHeight + 20
		loadingThread = PESLoadingThread(self)
		progressBar = ProgressBar(self.renderer, progressBarX, progressBarY, progressBarWidth, progressBarHeight, self.lineColour, self.menuBackgroundColour)
		
		while running:
			events = sdl2.ext.get_events()
			for event in events:
				if not loading:
					# keyboard events
					if event.type == sdl2.SDL_KEYDOWN:
						if event.key.keysym.sym == sdl2.SDLK_BACKSPACE:
							logging.debug("PESApp.run: trapping backspace key event")
							if not self.screens[self.screenStack[-1]].menuActive:
								self.screens[self.screenStack[-1]].setMenuActive(True)
							else:
								# pop the screen
								screenStackLen = len(self.__screenStack)
								logging.debug("PESApp.run: popping screen stack, current length: %d" % screenStackLen)
								if screenStackLen > 1:
									self.screenStack.pop()
									self.setScreen(self.screenStack[-1])
					self.screens[self.screenStack[-1]].processEvent(event)
								
				if event.type == sdl2.SDL_KEYDOWN and event.key.keysym.sym == sdl2.SDLK_ESCAPE:
					logging.debug("PESApp.run: trapping escape key event")
					running = False
					break
					
				# joystick events
				if event.type == sdl2.SDL_QUIT:
					running = False
					break
				
			sdl2.SDL_SetRenderDrawColor(self.renderer, self.backgroundColour.r, self.backgroundColour.g, self.backgroundColour.b, 255)
			sdl2.SDL_RenderClear(self.renderer)
			
			if loading:
				if not loadingThread.started:
					loadingThread.start()
				tick = sdl2.timer.SDL_GetTicks()
				if splashTextureAlpha < 255 and tick - lastTick > 100:
					splashTextureAlpha += 25
					if splashTextureAlpha > 255:
						splashTextureAlpha = 255
					lastTick = tick
				sdl2.SDL_SetTextureAlphaMod(splashTexture, splashTextureAlpha)
				sdl2.SDL_RenderCopy(self.renderer, splashTexture, None, sdl2.SDL_Rect(splashTextureX, splashTextureY, splashTextureWidth, splashTextureHeight))
				if loadingThread.done and splashTextureAlpha >= 255:
					loading = False
					sdl2.SDL_DestroyTexture(splashTexture)
				else:
					progressBar.draw(loadingThread.progress)
			else:
				sdl2.sdlgfx.boxRGBA(self.renderer, 0, 0, self.__dimensions[0], self.__headerHeight, self.headerBackgroundColour.r, self.headerBackgroundColour.g, self.headerBackgroundColour.b, 255) # header bg
				sdl2.sdlgfx.rectangleRGBA(self.renderer, 0, self.__headerHeight, self.__dimensions[0], self.__dimensions[1], self.lineColour.r, self.lineColour.g, self.lineColour.b, 255) # header line
				sdl2.SDL_RenderCopy(self.renderer, headerTexture, None, sdl2.SDL_Rect(5, 0, headerTextureWidth, headerTextureHeight)) # header text
				
				self.screens[self.screenStack[-1]].draw()
			
				now = datetime.now()
			
				dateTexture = createText(self.renderer, self.headerFont, now.strftime("%H:%M:%S %d/%m/%Y"), self.textColour)
				(dateTextureWidth, dateTextureHeight) = getTextureDimensions(dateTexture)
				sdl2.sdlgfx.boxRGBA(self.renderer, self.__dimensions[0] - dateTextureWidth - 5, 0, self.__dimensions[0] - 5, dateTextureHeight, self.headerBackgroundColour.r, self.headerBackgroundColour.g, self.headerBackgroundColour.b, 255)
				sdl2.SDL_RenderCopy(self.renderer, dateTexture, None, sdl2.SDL_Rect(self.__dimensions[0] - dateTextureWidth - 5, 0, dateTextureWidth, dateTextureHeight))
			
			sdl2.SDL_RenderPresent(self.renderer)
		
		sdl2.SDL_DestroyTexture(headerTexture)
		sdl2.SDL_DestroyTexture(dateTexture)
		self.exit()
		
	def setScreen(self, screen):
		if not screen in self.screens:
			logging.warning("PESApp.setScreen: invalid screen selection \"%s\"" % screen)
		else:
			logging.debug("PESApp.setScreen: setting current screen to \"%s\"" % screen)
			logging.debug("PESApp.setScreen: adding screen \"%s\" to screen stack" % screen)
			self.screenStack.append(screen)
			self.screens[screen].setMenuActive(True)
			
class PESLoadingThread(threading.Thread):
	def __init__(self, app):
		super(PESLoadingThread, self).__init__()
		self.app = app
		self.progress = 0
		self.started = False
		self.done = False
		
	def run(self):
		self.started = True
		
		# create database (if needed)
		con = None
		logging.debug('PESLoadingThread.run: connecting to database: %s' % userPesDb)
		try:
			con = sqlite3.connect(userPesDb)
			con.row_factory = sqlite3.Row
			cur = con.cursor()
			cur.execute('CREATE TABLE IF NOT EXISTS `games`(`game_id` INTEGER PRIMARY KEY, `api_id` INT, `exists` INT, `console_id` INT, `name` TEXT, `cover_art` TEXT, `game_path` TEXT, `overview` TEXT, `released` INT, `last_played` INT, `favourite` INT(1), `play_count` INT, `size` INT )')
			cur.execute('CREATE INDEX IF NOT EXISTS "games_index" on games (game_id ASC)')
			cur.execute('CREATE TABLE IF NOT EXISTS `consoles`(`console_id` INTEGER PRIMARY KEY, `api_id` INT, `name` TEXT)')
			cur.execute('CREATE INDEX IF NOT EXISTS "console_index" on consoles (console_id ASC)')
			cur.execute('CREATE TABLE IF NOT EXISTS `games_catalogue` (`short_name` TEXT, `full_name` TEXT)')
			cur.execute('CREATE INDEX IF NOT EXISTS "games_catalogue_index" on games_catalogue (short_name ASC)')
			
			self.progress = 25
			time.sleep(0.1)
			
			# is the games catalogue populated?
			cur.execute('SELECT COUNT(*) AS `total` FROM `games_catalogue`')
			row = cur.fetchone()
			if row['total'] == 0:
				logging.info("PESLoadingThread.run: populating games catalogue using file: %s" % userGamesCatalogueFile)
				catalogueConfigParser = ConfigParser.ConfigParser()
				catalogueConfigParser.read(userGamesCatalogueFile)
				
				for section in catalogueConfigParser.sections():
					if catalogueConfigParser.has_option(section, 'full_name'):
						fullName = catalogueConfigParser.get(section, 'full_name')
						logging.debug("PESLoadingThread.run: inserting game into catalogue: %s -> %s" % (section, fullName))
						cur.execute('INSERT INTO `games_catalogue` (`short_name`, `full_name`) VALUES ("%s", "%s");' % (section, fullName))
					else:
						logging.error("PESLoadingThread.run: games catalogue section \"%s\" has no \"full_name\" option!" % section)
						
			con.commit()
		except sqlite3.Error, e:
			pesExit("Error: %s" % e.args[0], True)
		finally:
			if con:
				con.close()
				
		self.progress = 50
		time.sleep(0.1)
		
		# load consoles
		configParser = ConfigParser.ConfigParser()
		configParser.read(userConsolesConfigFile)
		supportedConsoles = configParser.sections()
		supportedConsoles.sort()
		for c in supportedConsoles:
			# check the console definition from the config file
			try:
				consolePath = self.app.romsDir + os.sep + c
				mkdir(consolePath)
				consoleCoverartDir = self.app.coverartDir + os.sep + c
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
				self.app.consoles.append(console)
			except ConfigParser.NoOptionError, e:
				logging.error('PESLoadingThread.run: error parsing config file %s: %s' % (userConsolesConfigFile, e.message))
				self.done = True
				self.app.exit(1)
				return
			
		self.progress = 75
		time.sleep(0.1)
			
		self.app.initScreens()
		
		self.progress = 100
		time.sleep(0.1)
		
		logging.debug("PESLoadingThread.run: %d complete" % self.progress)
		self.done = True
		return
	
class UpdateDbThread(threading.Thread):
	def __init__(self, app):
		threading.Thread.__init__(self)
		self.app = app
		self.__db = userPesDb
		self.__consoles = self.app.consoles
		self.progress = 0
		self.status = 'stopped'
		self.stop = False
		self.added = 0
		self.updated = 0
		self.currentConsole = ''
		self.done = False
		self.started = False
		logging.debug("UpdateDbThread.init: initialised")
		
	def __extensionOk(self, extensions, filename):
		for e in extensions:
			if filename.endswith(e):
				return True
		return False

	def run(self):
		logging.debug('UpdateDbThread.run: started')
		self.started = True
		url = 'http://thegamesdb.net/api/'

		headers = {'User-Agent': 'PES Scraper'}
		
		imgExtensions = ['jpg', 'jpeg', 'png', 'gif']

		con = None
		cur = None

		try:
			con = sqlite3.connect(self.__db)
			con.row_factory = sqlite3.Row
			cur = con.cursor()
		except sqlite3.Error, e:
			if con:
				con.rollback()
			logging.error("UpdateDbThread.run: Error %s" % e.args[0])
			self.app.exit(1)

		for c in self.__consoles:
			self.progress = 0
			scanned = 0
			consoleName = c.getName()
			self.currentConsole = consoleName
			consoleId = c.getId()
			cacheDir = c.getImgCacheDir()

			urlLoaded = False
			consoleApiName = None

			try:
				# get API name for this console
				request = urllib2.Request("%sGetPlatform.php" % url, urllib.urlencode({ 'id':  c.getApiId() }), headers=headers)
				logging.debug('UpdateDbThread.run: loading URL: %s?%s' % (request.get_full_url(), request.get_data()))
				response = urllib2.urlopen(request)
				urlLoaded = True
				xmlData = ElementTree.parse(response)
				consoleApiName = xmlData.find('Platform/Platform').text
				logging.debug("UpdateDbThread.run: console API name: %s" % consoleApiName)
			except urllib2.URLError, e:
				logging.error("UpdateDbThread.run: an error occurred whilst trying to open url: %s" % e.message)

			logging.debug("UpdateDbThread.run: processing games for %s" % consoleName)
			self.status = 'Processing games for %s' % consoleName

			if self.__stopCheck():
				return

			try:
				cur.execute("UPDATE `games` SET `exists` = 0 WHERE `console_id` = %d;" % consoleId)
				con.commit()
				
				files = glob.glob("%s%s*" % (c.getRomDir(), os.sep))
				fileTotal = len(files)
				logging.debug("UpdateDbThread.run: found %d files to check" % fileTotal)
				extensions = c.getExtensions()

				for f in files:
					if os.path.isfile(f) and self.__extensionOk(extensions, f):
						if self.__stopCheck(con, cur):
							return

						filename = os.path.split(c.getRomDir() + os.sep + f)[1]
						name = filename
						fileSize = os.path.getsize(f)
						for e in c.getExtensions():
							name = name.replace(e, '')
						
						if c.ignoreRom(name):
							logging.debug("UpdateDbThread: ignoring %s" % f)
						else:
							self.__progress = 'Found game: %s' % name
							
							# look up name in games catalogue
							cur.execute("SELECT `full_name` FROM `games_catalogue` WHERE `short_name` = \"%s\"" % name)
							row = cur.fetchone()
							if row:
								logging.debug("UpdateDbThread.run: found match for %s in games catalogue: %s" % (name, row['full_name']))
								name = row['full_name']

							cur.execute("SELECT `game_id`, `name`, `cover_art`, `game_path`, `api_id` FROM `games` WHERE `game_path` = \"%s\";" % f)
							row = cur.fetchone()
							if row == None or (row['cover_art'] == "0" and row['api_id'] == -1) or (row['cover_art'] != "0" and not os.path.exists(row['cover_art'])):
								gameApiId = None
								bestName = name
								thumbPath = '0'
								
								# has cover art already been provided by the user or downloaded previously?
								for e in imgExtensions:
									path = cacheDir + os.sep + filename + '.' + e
									if os.path.exists(path):
										thumbPath = path
										break
									path = cacheDir + os.sep + name.replace('/', '_') + '.' + e
									if os.path.exists(path):
										thumbPath = path
										break
								
								overview = ''
								released = -1
								if consoleApiName != None:
									self.status = 'Downloading data for game: %s' % name
									logging.debug('downloading game info for %s' % name)
									# now grab thumbnail
									obj = { 'name': '%s' % name, 'platform': consoleApiName }
									data = urllib.urlencode(obj)
									urlLoaded = False
									nameLower = name.lower()
									fullUrl = ''

									try:
										request = urllib2.Request("%sGetGamesList.php" % url, urllib.urlencode(obj), headers=headers)
										fullUrl = '%s?%s' % (request.get_full_url(), request.get_data())
										logging.debug("UpdateDbThread.run: loading URL: %s" % fullUrl)
										response = urllib2.urlopen(request)
										urlLoaded = True
									except urllib2.URLError, e:
										logging.error("UpdateDbThread.run: an error occurred whilst trying to open %s: %s" % (fullUrl, e.message))

									if urlLoaded:
										bestResultDistance = -1
										dataOk = False
										try:
											xmlData = ElementTree.parse(response)
											dataOk = True
										except ParseError, e:
											logging.error('Unable to parse data from %s: %s' % (fullUrl, e.message))
										
										if dataOk:
											for x in xmlData.findall("Game"):
												xname = x.find("GameTitle").text.encode('ascii', 'ignore')
												xid = int(x.find("id").text)
												logging.debug("UpdateDbThread.run: potential result: %s (%d)" % (xname, xid))

												if xname.lower() == nameLower:
													logging.debug("UpdateDbThread.run: exact match!")
													gameApiId = xid
													break

												stringMatcher = StringMatcher(str(nameLower), xname.lower())
												distance = stringMatcher.distance()
												logging.debug("UpdateDbThread.run: string distance: %d" % distance)

												if bestResultDistance == -1 or distance < bestResultDistance:
													bestResultDistance = distance
													bestName = xname
													gameApiId = xid

								if self.__stopCheck(con, cur):
									return

								if gameApiId != None:
									self.status = "Match found: %s" % bestName
									logging.debug("UpdateDbThread.run: best match was: \"%s\" with a match rating of %d" % (bestName, bestResultDistance))
									urlLoaded = False
									try:
										request = urllib2.Request("%sGetGame.php" % url, urllib.urlencode({"id": gameApiId}), headers=headers)
										logging.debug("UpdateDbThread.run: loading URL: %s?%s" % (request.get_full_url(), request.get_data()))
										response = urllib2.urlopen(request)
										urlLoaded = True
									except urllib2.URLError, e:
										logging.debug("UpdateDbThread.run: an error occurred whilst trying to open url: %s" % e.message)

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
												logging.warning("UpdateDbThread.run: release date: %s is not in m/d/Y format!" % released)
												released = -1
												
										if thumbPath == "0":
											boxartElement = xmlData.find("Game/Images/boxart[@side='front']")
											if boxartElement != None:
												imageSaved = False
												try:
													imgUrl = "http://thegamesdb.net/banners/%s" % boxartElement.text
													logging.debug("UpdateDbThread.run: downloading cover art: %s" % imgUrl)
													self.status = "Downloading cover art for %s" % name
													extension = imgUrl[imgUrl.rfind('.'):]
													thumbPath =  c.getImgCacheDir() + os.sep + name.replace('/', '_') + extension
													request = urllib2.Request(imgUrl, headers=headers)
													response = urllib2.urlopen(request).read()
													logging.debug("opening file: %s" % thumbPath)
													output = open(thumbPath, 'wb')
													output.write(response)
													output.close()
													imageSaved = True
												except urllib2.URLError, e:
													logging.error("UpdateDbThread.run: an error occurred whilst trying to open url: %s" % e.message)

												if imageSaved:
													# resize the image if it is too big
													self.__scaleImage(thumbPath, name)
										else:
											logging.debug("UpdateDbThread.run: using cached cover art: %s" % thumbPath)
											# does the provided image need to be scaled?
											self.__scaleImage(thumbPath, name)
														
								else:
									self.__progress = 'Could not find game data for %s' % name
									logging.debug("could not find game info for %s " % name)
									gameApiId = -1

								if row == None:
									self.status = "Adding %s to database..." % name
									logging.debug("UpdateDbThread.run: inserting new game record into database...")
									cur.execute("INSERT INTO `games`(`exists`, `console_id`, `name`, `game_path`, `api_id`, `cover_art`, `overview`, `released`, `favourite`, `last_played`, `play_count`, `size`) VALUES (1, %d, '%s', '%s', %d, '%s', '%s', %d, 0, -1, 0, %d);" % (consoleId, name.replace("'", "''"), f.replace("'", "''"), gameApiId, thumbPath.replace("'", "''"), overview.replace("'", "''"), released, fileSize))
									self.added += 1
								elif gameApiId != -1:
									self.status = "Updating %s..." % name
									logging.debug('updating game record in database...')
									cur.execute("UPDATE `games` SET `api_id` = %d, `cover_art` = '%s', `overview` = '%s', `exists` = 1 WHERE `game_id` = %d;" % (gameApiId, thumbPath.replace("'", "''"), overview.replace("'", "''"), row['game_id']))
									self.updated += 1
								else:
									self.status = "No need to update %s" % name
									logging.debug("UpdateDbThread.run: no need to update - could not find %s in online database" % name)
									cur.execute("UPDATE `games` SET `exists` = 1 WHERE `game_id` = %d;" % row["game_id"])
									
								con.commit()
							else:
								self.status = "No need to update %s" % name
								logging.debug("UpdateDbThread.run: no need to update %s" % name)
								cur.execute("UPDATE `games` SET `exists` = 1 WHERE `game_id` = %d;" % row["game_id"])
								con.commit()

						if self.__stopCheck(con, cur):
							return
								
					scanned += 1
					self.progress = (float(scanned) / float(fileTotal)) * 100
				logging.debug("UpdateDbThread.run: purging missing games for: %s" % consoleName)
				cur.execute("DELETE FROM `games` WHERE `exists` = 0 AND console_id = %d" % consoleId)
				con.commit()
								
			except sqlite3.Error, e:
				logging.error("UpdateDbThread.run:UpdateDbThread.run: could not update database: %s" % (e.args[0]))
				if con:
					con.rollback()
				self.status = "An error occurred whilst updating the database"
				self.progress = 100
				self.finished = True
				return

		self.status = "Update complete"
		self.done = True
		self.progress = 100
		logging.debug("UpdateDbThread.run: finished")
		return

	def __scaleImage(self, path, name):
		img = Image.open(path)
		width, height = img.size
		ratio = min(float(400.0 / width), float(400.0 / height))
		newWidth = width * ratio
		newHeight = height * ratio
		if width > newWidth or height > newHeight:
			# scale image
			self.status = "Scaling cover art for %s" % name
			logging.debug("UpdateDbThread.__scaleImage: scaling image: %s" % path)
			img.thumbnail((newWidth, newHeight), Image.ANTIALIAS)
			img.save(path)
	
	def setConsoles(self, consoles):
		self.__consoles = consoles

	def __stopCheck(self, con=None, cur=None):
		if self.stop:
			if cur != None and con != None:
				try:
					# revert exists field
					cur.execute('UPDATE `games` SET `exists` = 1 WHERE `exists` = 0')
					con.commit()
					con.close()
				except sqlite3.Error, e:
					logging.error("Error: %s" % e.args[0])
				
			self.status = 'Update interrupted!'
			self.done = True
			self.progress = 100
			logging.debug('UpdateDbThread.run: finished (interrupted)')
			return True
		return False

class ProgressBar(object):
	
	def __init__(self, renderer, x, y, width, height, colour, backgroundColour):
		self.__progress = 0.0 # percent complete
		self.__renderer = renderer
		self.__x = x
		self.__y = y
		self.__width = width
		self.__height = height
		self.__colour = colour
		self.__backgroundColour = backgroundColour
		logging.debug("ProgressBar.init: initialised")
	
	def draw(self, progress=0):
		self.setProgress(progress)
		margin = 3
		w = int(self.__width * (self.__progress / 100.0))
		sdl2.sdlgfx.boxRGBA(self.__renderer, self.__x, self.__y, self.__x + self.__width, self.__y + self.__height, self.__backgroundColour.r, self.__backgroundColour.g, self.__backgroundColour.b, 255)
		sdl2.sdlgfx.boxRGBA(self.__renderer, self.__x + margin, self.__y + margin, self.__x + w - margin, self.__y + self.__height - margin, self.__colour.r, self.__colour.g, self.__colour.b, 255)
	
	def setCoords(self, x, y):
		self.__x = x
		self.__y = y
	
	def setProgress(self, p):
		if p > 100:
			raise ValueError("%d is greater than 100" % p)
		if p < 0:
			raise ValueError("%d is less than 0" % p)
		self.__progress = p
		
	def setSize(self, w, h):
		self.__w = w
		self.__h = h

class Menu(object):
	
	def __init__(self, items):
		super(Menu, self).__init__()
		self.__selected = 0
		self.__items = items
		logging.debug("Menu.init: Menu initialised")
	
	def addItem(self, item):
		self.__items.append(item)
		
	def getItem(self, i):
		return self.__items[i]
		
	def getItems(self):
		return self.__items
	
	def getSelectedIndex(self):
		return self.__selected
	
	def getSelectedItem(self):
		return self.__items[self.__selected]
	
	def getCount(self):
		return len(self.__items)
		
	def setSelected(self, i):
		if i >= 0 and i < len(self.__items):
			self.__items[self.__selected].setSelected(False)
			self.__selected = i
			self.__items[self.__selected].setSelected(True)
			return
		raise ValueError("Menu.setSelected: invalid value for i: %s" % i)
	
	def toggleAll(self, toggle):
		for i in self.__items:
			if i.isToggable():
				i.toggle(toggle)
	
class MenuItem(object):
	
	def __init__(self, text, selected = False, toggable = False, callback = None, *callbackArgs):
		super(MenuItem, self).__init__()
		self.__text = text
		self.__selected = selected
		self.__callback = callback
		self.__toggled = False
		self.__toggable = toggable
		self.__callbackArgs = callbackArgs
	
	def getText(self):
		return self.__text
	
	def isSelected(self):
		return self.__selected
	
	def isToggled(self):
		return self.__toggled
	
	def toggle(self, t):
		self.__toggled = t
		
	def isToggable(self):
		return self.__toggable
	
	def setSelected(self, selected):
		self.__selected = selected
	
	def setText(text):
		self.__text = text
		
	def trigger(self):
		if self.__callback:
			logging.debug("MenuItem.trigger: calling function for %s menu item" % self.__text)
			if self.__callbackArgs:
				self.__callback(*self.__callbackArgs)
			else:
				self.__callback()
		else:
			logging.debug("MenuItem.trigger: no callback defined for %s menu item" % self.__text)
		
	def __repr__(self):
		return "<MenuItem: text: %s >" % self.__text
		
class ConsoleMenuItem(MenuItem):
	
	def __init__(self, console):
		super(ConsoleMenuItem, self).__init__(console.getName())
		self.__console = console
		
class Screen(object):
	
	def __init__(self, app, renderer, title, menu, menuRect, screenRect):
		super(Screen, self).__init__()
		self.title = title
		self.app = app
		self.renderer = renderer
		self.menu = menu
		self.menuRect = menuRect
		self.screenRect = screenRect
		self.menuActive = True
		self.__menuMargin = 5
		self.__menuTopMargin = 10
		self.__menuFontHeight = getFontHeight(self.app.menuFont)
		self.__menuItemChanged = False
		self.__lastTick = sdl2.timer.SDL_GetTicks()
		self.screenMargin = 10
		self.wrap = self.screenRect[2] - (self.screenMargin * 2)
		self.menu.setSelected(0)
		
	def draw(self):
		#if self.menuActive:
		#	tick = sdl2.timer.SDL_GetTicks()
		#	if self.__menuItemChanged and tick - self.__lastTick >= 1000: # 3 seconds
		#		self.__lastTick = tick
		#		self.__menuItemChanged = False
		#		logging.debug("MainMenuPanel.draw: menu hover tick triggered!")
		#		self.drawScreen()
		
		self.drawMenu()
		self.drawScreen()
		
	def drawMenu(self):
		
		#logging.debug("Screen.draw: drawing menu at (%d, %d) dimensions (%d, %d)" % (self.menuRect[0], self.menuRect[1], self.menuRect[2], self.menuRect[3]))
		x = self.menuRect[0]
		y = self.menuRect[1]
		w = self.menuRect[2]
		h = self.menuRect[3]
		menuTop = y + self.__menuTopMargin
		sdl2.sdlgfx.boxRGBA(self.renderer, x, y, x + w, y + h, self.app.menuBackgroundColour.r, self.app.menuBackgroundColour.g, self.app.menuBackgroundColour.b, 255)
		visibleMenuItems = int((h - self.__menuTopMargin) / self.__menuFontHeight)
		menuItems = self.menu.getItems()
		menuItemTotal = len(menuItems)
		
		#logging.debug("Screen.draw: visibleMenuItems = %d" % visibleMenuItems)
		
		currentY = menuTop
		firstMenuItem = 0
		
		selectedIndex = self.menu.getSelectedIndex()
		if selectedIndex >= firstMenuItem + visibleMenuItems:
			firstMenuItem = selectedIndex - visibleMenuItems + 1
		elif selectedIndex < firstMenuItem:
			firstMenuItem = selectedIndex
		
		i = firstMenuItem
		while i < menuItemTotal and i < firstMenuItem + visibleMenuItems:
				m = self.menu.getItem(i)
				if m.isSelected():
					if self.menuActive:
						sdl2.sdlgfx.boxRGBA(self.renderer, x + self.__menuMargin, currentY, x + self.__menuMargin + (w - (self.__menuMargin * 2)), currentY + self.__menuFontHeight, self.app.menuSelectedBgColour.r, self.app.menuSelectedBgColour.g, self.app.menuSelectedBgColour.b, 255)
					else:
						sdl2.sdlgfx.boxRGBA(self.renderer, x + self.__menuMargin, currentY, x + self.__menuMargin + (w - (self.__menuMargin * 2)), currentY + self.__menuFontHeight, self.app.menuTextColour.r, self.app.menuTextColour.g, self.app.menuTextColour.b, 255)
					renderText(self.renderer, self.app.menuFont, m.getText(), self.app.menuSelectedTextColour, self.__menuMargin, currentY)
				else:
					renderText(self.renderer, self.app.menuFont, m.getText(), self.app.menuTextColour, self.__menuMargin, currentY)
				currentY += self.__menuFontHeight
				i += 1
	
	def drawScreen(self):
		sdl2.sdlgfx.boxRGBA(self.renderer, self.screenRect[0], self.screenRect[1], self.screenRect[0] + self.screenRect[2], self.screenRect[1] + self.screenRect[3], self.app.backgroundColour.r, self.app.backgroundColour.g, self.app.backgroundColour.b, 255)
	
	def processEvent(self, event):
		if self.menuActive:
			if event.type == sdl2.SDL_KEYDOWN:
				if event.key.keysym.sym == sdl2.SDLK_DOWN:
					logging.debug("Screen.processEvent: (menu) key event: DOWN")
					i = self.menu.getSelectedIndex()
					total = self.menu.getCount()
					if i + 1 > total - 1:
						self.menu.setSelected(0)
					else:
						self.menu.setSelected(i + 1)
					self.__lastTick = sdl2.timer.SDL_GetTicks()
					self.__menuItemChanged = True
				elif event.key.keysym.sym == sdl2.SDLK_UP:
					logging.debug("Screen.processEvent: (menu) key event: UP")
					i = self.menu.getSelectedIndex()
					total = self.menu.getCount()
					if i - 1 < 0:
						self.menu.setSelected(total - 1)
					else:
						self.menu.setSelected(i - 1)
					self.__lastTick = sdl2.timer.SDL_GetTicks()
					self.__menuItemChanged = True
				elif event.key.keysym.sym == sdl2.SDLK_RETURN or event.key.keysym.sym == sdl2.SDLK_KP_ENTER:
					logging.debug("Screen.processEvent: (menu) key event: RETURN")
					self.__menuItemChanged = False
					self.menu.getSelectedItem().trigger()
					self.setMenuActive(False)
	
	def setMenuActive(self, active):
		self.menuActive = active
		logging.debug("Screen.setMenuActive: \"%s\" activate state is now: %s" % (self.title, self.menuActive))
		
	def stop(self):
		pass
	
class HomeScreen(Screen):
	
	def __init__(self, app, renderer, menuRect, screenRect):
		super(HomeScreen, self).__init__(app, renderer, "Home", Menu([MenuItem("Home")]), menuRect, screenRect)
		for c in self.app.consoles:
			self.menu.addItem(ConsoleMenuItem(c))
		self.menu.addItem(MenuItem("Settings", False, False, self.app.setScreen, "Settings"))
		self.menu.addItem(MenuItem("Reboot"))
		self.menu.addItem(MenuItem("Power Off"))
		self.menu.addItem(MenuItem("Exit", False, False, self.app.exit))
		logging.debug("HomeScreen.init: initialised")
			
	def drawScreen(self):
		super(HomeScreen, self).drawScreen()
		#logging.debug("HomeScreen.draw: drawing screen at (%d, %d) dimensions (%d, %d)" % (self.screenRect[0], self.screenRect[1], self.screenRect[2], self.screenRect[3]))
		(textWidth, textHeight) = renderText(self.renderer, self.app.titleFont, "Welcome to PES!", self.app.textColour, self.screenRect[0] + self.screenMargin, self.screenRect[1])
		(textWidth, textHeight) = renderText(self.renderer, self.app.bodyFont, "The home screen provides you with quick access to your favourite, new additions and most recently played games.", self.app.textColour, self.screenRect[0] + self.screenMargin, self.screenRect[1] + (textHeight * 2), self.wrap)
		
class SettingsScreen(Screen):
	
	def __init__(self, app, renderer, menuRect, screenRect):
		super(SettingsScreen, self).__init__(app, renderer, "Settings", Menu([
			MenuItem("Update Database"),
			MenuItem("Joystick Set-Up"),
			MenuItem("Reset Database"),
			MenuItem("Reset Config"),
			MenuItem("About")]),
		menuRect, screenRect)
		
		self.__init = True
		self.__updateDatabaseMenu = Menu([MenuItem("Begin Scan", True)])
		for c in self.app.consoles:
			self.__updateDatabaseMenu.addItem(MenuItem(c.getName(), False, True))
		self.__toggleMargin = 20
		self.__updateDbThread = None
		self.__scanProgressBar = None
		logging.debug("SettingsScreen.init: initialised")

	def drawScreen(self):
		super(SettingsScreen, self).drawScreen()
		#logging.debug("SettingsScreen.draw: drawing screen at (%d, %d) dimensions (%d, %d)" % (self.screenRect[0], self.screenRect[1], self.screenRect[2], self.screenRect[3]))
		
		currentX = self.screenRect[0] + self.screenMargin
		currentY = self.screenRect[1]
		
		if self.__init:
			(textWidth, textHeight) = renderText(self.renderer, self.app.titleFont, "Settings", self.app.textColour, currentX, currentY)
			renderLines(self.renderer, self.app.bodyFont, ["Here you can scan for new games, set-up your joysticks as well as being able to reset PES to its default settings.", " ", "Please select an item from the menu on the left."], self.app.textColour, currentX, currentY + textHeight + self.screenMargin, self.wrap)
			return
		
		selected = self.menu.getSelectedItem().getText()
		#logging.debug("SettingsScreen.drawScreen: selected \"%s\"" % selected)
		
		(textWidth, textHeight) = renderText(self.renderer, self.app.titleFont, selected, self.app.textColour, currentX, currentY)
		
		currentY += textHeight + self.screenMargin
		
		if selected == "Update Database":
			if self.__updateDbThread == None:
				(textWidth, textHeight) = renderText(self.renderer, self.app.bodyFont, "Please use the menu below to select which consoles you wish to include in your search. By default all consoles are selected. When you are ready, please select the \"Begin Scan\" item from the menu below.", self.app.textColour, currentX , currentY, self.wrap)
				currentY += textHeight + 10
				
				visibleMenuItems = int((self.screenRect[3] - currentY) / self.app.bodyFontHeight)
				menuItems = self.__updateDatabaseMenu.getItems()
				menuItemTotal = len(menuItems)
				
				firstMenuItem = 0
				
				selectedIndex = self.__updateDatabaseMenu.getSelectedIndex()
				if selectedIndex >= firstMenuItem + visibleMenuItems:
					firstMenuItem = selectedIndex - visibleMenuItems + 1
				elif selectedIndex < firstMenuItem:
					firstMenuItem = selectedIndex
				
				toggleCenterY = self.app.bodyFontHeight / 2
				toggleCenterX = int(currentX + (self.__toggleMargin / 2))
				toggleRad = 3
				
				i = firstMenuItem
				while i < menuItemTotal and i < firstMenuItem + visibleMenuItems:
						m = self.__updateDatabaseMenu.getItem(i)
						if m.isSelected():
							sdl2.sdlgfx.boxRGBA(self.renderer, currentX, currentY, 500, currentY + self.app.bodyFontHeight + 2, self.app.menuSelectedBgColour.r, self.app.menuSelectedBgColour.g, self.app.menuSelectedBgColour.b, 255)
						if m.isToggable():
							if m.isToggled():
								sdl2.sdlgfx.filledCircleRGBA(self.renderer, toggleCenterX, toggleCenterY + currentY, toggleRad, self.app.textColour.r, self.app.textColour.g, self.app.textColour.b, 255)
						renderText(self.renderer, self.app.bodyFont, m.getText(), self.app.textColour, currentX + self.__toggleMargin, currentY)
						currentY += self.app.bodyFontHeight
						i += 1
			elif self.__updateDbThread.started and not self.__updateDbThread.done:
				(textWidth, textHeight) = renderLines(self.renderer, self.app.bodyFont, ["Scan now in progress... press BACK to abort", " ", "Console: %s" % self.__updateDbThread.currentConsole, " ", "Status: %s" % self.__updateDbThread.status, " ", "Progress for this console:"], self.app.textColour, currentX, currentY, self.wrap)
				currentY += textHeight + 20
				self.__scanProgressBar.setCoords(currentX, currentY)
				self.__scanProgressBar.draw(self.__updateDbThread.progress)
			elif self.__updateDbThread.done:
				renderLines(self.renderer, self.app.bodyFont, ["Scan complete!", " ", "Added: %d" % self.__updateDbThread.added, " ", "Updated: %d" % self.__updateDbThread.updated, " ", "Press BACK to return to the previous screen."], self.app.textColour, currentX, currentY, self.wrap)
				
			
		elif selected == "Joystick Set-Up":
			pass
		elif selected == "Reset Database":
			pass
		elif selected == "Reset Config":
			pass
		elif selected == "About":
			renderLines(self.renderer, self.app.bodyFont, ['Pi Entertainment System version %s' % VERSION_NUMBER, ' ', 'Released: %s' % VERSION_DATE, ' ', 'License: Licensed under version 3 of the GNU Public License (GPL)', ' ', 'Author: %s' % VERSION_AUTHOR, ' ', 'Contributors: Eric Smith', ' ', 'Cover art: theGamesDB.net', ' ', 'Documentation: http://pes.mundayweb.com', ' ', 'Facebook: https://www.facebook.com/pientertainmentsystem', ' ', 'Help: pes@mundayweb.com'], self.app.textColour, currentX, currentY, self.wrap)
		
	def processEvent(self, event):
		selected = self.menu.getSelectedItem().getText()
		oldMenuActive = self.menuActive # store state before parent method changes it!
		
		# don't pass up the event if a db scan is in progress
		if event.type == sdl2.SDL_KEYDOWN and event.key.keysym.sym == sdl2.SDLK_BACKSPACE and selected == "Update Database" and self.__updateDbThread != None:
			if self.__updateDbThread.started and not self.__updateDbThread.done:
				self.setMenuActive(False)
				self.__updateDbThread.stop = True
				return
			elif selected == "Update Database"  and self.__updateDbThread != None and self.__updateDbThread.done:
				self.setMenuActive(False)
				self.__updateDbThread = None
				return
		
		super(SettingsScreen, self).processEvent(event)
		
		if selected == "Update Database":
			pass
		elif selected == "Joystick Set-Up":
			pass
		elif selected == "Reset Database":
			pass
		elif selected == "Reset Config":
			pass
		elif selected == "About":
			pass
		
		if oldMenuActive:
			if event.type == sdl2.SDL_KEYDOWN and (event.key.keysym.sym == sdl2.SDLK_RETURN or event.key.keysym.sym == sdl2.SDLK_KP_ENTER):
				logging.debug("SettingsScreen.processEvent: return key trapped for %s" % selected)
				if selected == "Update Database":
					self.__updateDatabaseMenu.setSelected(0)
					self.__updateDatabaseMenu.toggleAll(True)
				self.__init = False
		
		if self.menuActive: # this will be true if parent method trapped a backspace event
			if event.type == sdl2.SDL_KEYDOWN:
				if event.key.keysym.sym == sdl2.SDLK_BACKSPACE:
					logging.debug("SettingsScreen.processEvent: trapping backspace event")
					self.__init = True
		else:
			if selected == "Update Database":
				if event.type == sdl2.SDL_KEYDOWN:
					if event.key.keysym.sym == sdl2.SDLK_DOWN:
						logging.debug("SettingsScreen.processEvent: (Update Database) key event: DOWN")
						i = self.__updateDatabaseMenu.getSelectedIndex()
						total = self.__updateDatabaseMenu.getCount()
						if i + 1 > total - 1:
							self.__updateDatabaseMenu.setSelected(0)
						else:
							self.__updateDatabaseMenu.setSelected(i + 1)
					elif event.key.keysym.sym == sdl2.SDLK_UP:
						logging.debug("SettingsScreen.processEvent: (Update Database) key event: UP")
						i = self.__updateDatabaseMenu.getSelectedIndex()
						total = self.__updateDatabaseMenu.getCount()
						if i - 1 < 0:
							self.__updateDatabaseMenu.setSelected(total - 1)
						else:
							self.__updateDatabaseMenu.setSelected(i - 1)
					elif self.menuActive == oldMenuActive and (event.key.keysym.sym == sdl2.SDLK_RETURN or event.key.keysym.sym == sdl2.SDLK_KP_ENTER):
						logging.debug("SettingsScreen.processEvent: (Update Database) key event: RETURN")
						m = self.__updateDatabaseMenu.getSelectedItem()
						if m.isToggable():
							m.toggle(not m.isToggled())
						elif m.getText() == "Begin Scan":
							if self.__scanProgressBar == None:
								self.__scanProgressBar = ProgressBar(self.renderer, self.screenRect[0] + self.screenMargin, 0, self.screenRect[2] - (self.screenMargin * 2), 40, self.app.lineColour, self.app.menuBackgroundColour)
							else:
								self.__scanProgressBar.setProgress(0)
							self.__updateDbThread = UpdateDbThread(self.app)
							self.__updateDbThread.start()
						
	def stop(self):
		if self.__updateDbThread:
			logging.debug("settings.stop: stopping update thread")
			self.__updateDbThread.stop = True