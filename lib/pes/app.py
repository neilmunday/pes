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

#
# TO DO:
#
# - games screens
# - joystick integration and settings etc.
#

from ctypes import c_int, c_char_p, c_uint32, c_void_p, byref, cast
from datetime import datetime
from pes import *
from pes.data import *
from pes.dbupdate import *
from pes.ui import *
import pes.event
from pes.util import *
from PIL import Image
from collections import OrderedDict
from xml.etree import ElementTree
from xml.etree.ElementTree import Element, SubElement
import glob
import logging
import math
import ConfigParser
import pes.event
import sdl2
import sdl2.ext
import sdl2.sdlimage
import sdl2.joystick
import sdl2.video
import sdl2.render
import sdl2.sdlgfx
import sdl2.sdlttf
import sdl2.timer
import sqlite3
import sys
import threading
import time
import urllib
import urllib2

CONSOLE_TEXTURE_ALPHA = 50

class PESApp(object):
	
	def __del__(self):
		logging.debug("PESApp.del: deleting object")
		if getattr(self, "__window", None):
			logging.debug("PESApp.del: window destroyed")
			sdl2.video.SDL_DestroyWindow(self.__window)
			self.__window = None

	def __init__(self, dimensions, fontFile, romsDir, coverartDir, backgroundColour, menuBackgroundColour, headerBackgroundColour, lineColour, textColour, menuTextColour, menuSelectedTextColour):
		super(PESApp, self).__init__()
		self.__dimensions = dimensions
		self.fontFile = fontFile
		self.romsDir = romsDir
		self.coverartDir = coverartDir
		self.consoles = []
		self.consoleSurfaces = None
		self.__uiObjects = [] # list of UI objects created so we can destroy them upon exit
		
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
		
		#self.joystickTotal = SDLJoystick.SDL_NumJoysticks()
		#print "Joysticks: %d " % self.joystickTotal
		#for i in range(0, self.joystickTotal):
		#   print SDLJoystick.SDL_JoystickNameForIndex(i)
		
	def exit(self, rtn=0):
		# tidy up
		logging.debug("PESApp.exit: stopping screens...")
		for s in self.screens:
			self.screens[s].stop()
		logging.debug("PESApp.exit: purging cached surfaces...")
		for console, surface in self.consoleSurfaces.iteritems():
			logging.debug("PESApp.exit: unloading surface for %s..." % console)
			sdl2.SDL_FreeSurface(surface)
		logging.debug("PESApp.exit: tidying up...")
		Thumbnail.destroyTextures()
		for o in self.__uiObjects:
			o.destroy()
		sdl2.sdlttf.TTF_CloseFont(self.headerFont)
		sdl2.sdlttf.TTF_CloseFont(self.bodyFont)
		sdl2.sdlttf.TTF_CloseFont(self.menuFont)
		sdl2.sdlttf.TTF_CloseFont(self.titleFont)
		sdl2.sdlttf.TTF_CloseFont(self.splashFont)
		sdl2.sdlttf.TTF_Quit()
		sdl2.sdlimage.IMG_Quit()
		sdl2.SDL_Quit()
		logging.info("PESApp.exit: exiting...")
		sys.exit(rtn)
		
	def initScreens(self):
		logging.debug("PESApp.initScreens: initialising screens...")
		self.screens["Home"] = HomeScreen(self, self.renderer, self.menuRect, self.screenRect)
		self.screens["Settings"] = SettingsScreen(self, self.renderer, self.menuRect, self.screenRect)
		consoleScreens = 0
		for c in self.consoles:
			if c.getGameTotal() > 0:
				self.screens["Console %s" % c.getName()] = ConsoleScreen(self, self.renderer, self.menuRect, self.screenRect, c)
				consoleScreens += 1
		logging.debug("PESApp.initScreens: initialised %d screens of which %d are console screens" % (len(self.screens), consoleScreens))
		self.screenStack = ["Home"]
	
	def initSurfaces(self):
		
		if self.consoleSurfaces != None:
			return
		
		self.consoleSurfaces = {}
		logging.debug("PESApp.initSurfaces: pre-loading console images...")
		for c in self.consoles:
			surface = sdl2.sdlimage.IMG_Load(c.getImg())
			if surface == None:
				logging.error("PESApp.initSurfaces: failed to load image: %s" % c.getImg())
				self.exit(1)
			self.consoleSurfaces[c.getName()] = surface
			logging.debug("PESApp.initSurfaces: pre-loaded %s surface from %s" % (c.getName(), c.getImg()))
        
	def run(self):
		sdl2.SDL_Init(sdl2.SDL_INIT_EVERYTHING)
		sdl2.SDL_ShowCursor(0)
		sdl2.sdlttf.TTF_Init()
		imgFlags = sdl2.sdlimage.IMG_INIT_JPG | sdl2.sdlimage.IMG_INIT_PNG
		initted = sdl2.sdlimage.IMG_Init(imgFlags)
		if initted != imgFlags:
			logging.error("PESApp.run: failed to initialise SDL_Image")
			self.exit(1)
		videoMode = sdl2.video.SDL_DisplayMode()
		if sdl2.video.SDL_GetDesktopDisplayMode(0, videoMode) != 0:
			pesExit("PESApp.run: unable to get current video mode!")
			
		logging.debug("PESApp.run: video mode (%d, %d), refresh rate: %dHz" % (videoMode.w, videoMode.h, videoMode.refresh_rate))
		
		# register PES event type
		if pes.event.registerPesEventType():
			logging.debug("PESApp.run: PES event type registered in SDL2: %s" % pes.event.EVENT_TYPE)
		else:
			logging.error("PESApp.run: could not register PES event type in SDL2!")
			self.exit(1)
		
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
		
		self.renderer = sdl2.SDL_CreateRenderer(self.__window, -1, sdl2.render.SDL_RENDERER_ACCELERATED)
		
		# pre-initialise screens
		self.screens = {}
		
		headerLabel = Label(self.renderer, 5, 0, "Pi Entertainment System", self.headerFont, self.textColour)
		self.__uiObjects.append(headerLabel)
		dateLabel = Label(self.renderer, 0, 0, "00:00:00 00/00/0000", self.headerFont, self.textColour)
		dateLabel.x = self.__dimensions[0] - dateLabel.width - 5
		self.__uiObjects.append(dateLabel)

		splashLabel = Label(self.renderer, 0, 0, "Pi Entertainment System", self.splashFont, self.textColour)
		splashLabel.x = int((self.__dimensions[0] - splashLabel.width) / 2)
		splashLabel.y = ((self.__dimensions[1]) / 2) - splashLabel.height
		
		running = True
		loading = True
		
		lastTick = sdl2.timer.SDL_GetTicks()
		splashTextureAlpha = 25
		progressBarWidth = splashLabel.width
		progressBarHeight = 40
		progressBarX = splashLabel.x
		progressBarY = splashLabel.y + splashLabel.height + 20
		loadingThread = PESLoadingThread(self)
		progressBar = ProgressBar(self.renderer, progressBarX, progressBarY, progressBarWidth, progressBarHeight, self.lineColour, self.menuBackgroundColour)
		
		while running:
			events = sdl2.ext.get_events()
			for event in events:
				if event.type == pes.event.EVENT_TYPE:
					(t, d1, d2) = pes.event.decodePesEvent(event)
					logging.debug("PESApp.run: trapping PES Event")
					if not loading and t == pes.event.EVENT_DB_UPDATE:
						for c in self.consoles:
							c.refresh()
							screenName = "Console %s" % c.getName()
							if c.getGameTotal() > 0:
								if screenName in self.screens:
									self.screens[screenName].refresh()
								else:
									logging.debug("PESApp.run adding ConsoleScreen for %s following database update" % c.getName())
									self.screens[screenName] = ConsoleScreen(self, self.renderer, self.menuRect, self.screenRect, c)
								
						self.screens["Home"].refreshMenu()
						Thumbnail.destroyTextures()
					elif t == pes.event.EVENT_RESOURCES_LOADED:
						pass
				
				if not loading:
					# keyboard events
					if event.type == sdl2.SDL_KEYDOWN:
						if event.key.keysym.sym == sdl2.SDLK_BACKSPACE:
							logging.debug("PESApp.run: trapping backspace key event")
							if self.screens[self.screenStack[-1]].menuActive:
								# pop the screen
								screenStackLen = len(self.screenStack)
								logging.debug("PESApp.run: popping screen stack, current length: %d" % screenStackLen)
								if screenStackLen > 1:
									self.screenStack.pop()
									self.setScreen(self.screenStack[-1], False)
							else:
								self.screens[self.screenStack[-1]].setMenuActive(True)
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
				splashLabel.setAlpha(splashTextureAlpha)
				splashLabel.draw()
				if loadingThread.done and splashTextureAlpha >= 255:
					loading = False
					splashLabel.destroy()
				else:
					progressBar.setProgress(loadingThread.progress)
					progressBar.draw()
			else:
				sdl2.sdlgfx.boxRGBA(self.renderer, 0, 0, self.__dimensions[0], self.__headerHeight, self.headerBackgroundColour.r, self.headerBackgroundColour.g, self.headerBackgroundColour.b, 255) # header bg
				sdl2.sdlgfx.rectangleRGBA(self.renderer, 0, self.__headerHeight, self.__dimensions[0], self.__dimensions[1], self.lineColour.r, self.lineColour.g, self.lineColour.b, 255) # header line
				headerLabel.draw()
				
				self.screens[self.screenStack[-1]].draw()
			
				now = datetime.now()
				dateLabel.setText(now.strftime("%H:%M:%S %d/%m/%Y"))
				dateLabel.draw()
			
			sdl2.SDL_RenderPresent(self.renderer)
		self.exit(0)
		
	def setScreen(self, screen, doAppend=True):
		if not screen in self.screens:
			logging.warning("PESApp.setScreen: invalid screen selection \"%s\"" % screen)
		else:
			logging.debug("PESApp.setScreen: setting current screen to \"%s\"" % screen)
			logging.debug("PESApp.setScreen: adding screen \"%s\" to screen stack" % screen)
			if doAppend:
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
			cur.execute('CREATE TABLE IF NOT EXISTS `games`(`game_id` INTEGER PRIMARY KEY, `api_id` INT, `exists` INT, `console_id` INT, `name` TEXT, `cover_art` TEXT, `game_path` TEXT, `overview` TEXT, `released` INT, `last_played` INT, `added` INT, `favourite` INT(1), `play_count` INT, `size` INT )')
			cur.execute('CREATE INDEX IF NOT EXISTS "games_index" on games (game_id ASC)')
			cur.execute('CREATE TABLE IF NOT EXISTS `consoles`(`console_id` INTEGER PRIMARY KEY, `api_id` INT, `name` TEXT)')
			cur.execute('CREATE INDEX IF NOT EXISTS "console_index" on consoles (console_id ASC)')
			cur.execute('CREATE TABLE IF NOT EXISTS `games_catalogue` (`short_name` TEXT, `full_name` TEXT)')
			cur.execute('CREATE INDEX IF NOT EXISTS "games_catalogue_index" on games_catalogue (short_name ASC)')
			
			self.progress = 20
			
			# is the games catalogue populated?
			cur.execute('SELECT COUNT(*) AS `total` FROM `games_catalogue`')
			row = cur.fetchone()
			if row['total'] == 0:
				logging.info("PESLoadingThread.run: populating games catalogue using file: %s" % userGamesCatalogueFile)
				catalogueConfigParser = ConfigParser.ConfigParser()
				catalogueConfigParser.read(userGamesCatalogueFile)
				sections = catalogueConfigParser.sections()
				sectionTotal = float(len(sections))
				
				i = 0.0
				for section in sections:
					if catalogueConfigParser.has_option(section, 'full_name'):
						fullName = catalogueConfigParser.get(section, 'full_name')
						logging.debug("PESLoadingThread.run: inserting game into catalogue: %s -> %s" % (section, fullName))
						cur.execute('INSERT INTO `games_catalogue` (`short_name`, `full_name`) VALUES ("%s", "%s");' % (section, fullName))
					else:
						logging.error("PESLoadingThread.run: games catalogue section \"%s\" has no \"full_name\" option!" % section)
					i += 1.0
					self.progress = 20 + (20 * (i / sectionTotal))
						
			con.commit()
		except sqlite3.Error, e:
			pesExit("Error: %s" % e.args[0], True)
		finally:
			if con:
				con.close()
				
		self.progress = 40
		
		# load consoles
		configParser = ConfigParser.ConfigParser()
		configParser.read(userConsolesConfigFile)
		supportedConsoles = configParser.sections()
		supportedConsoleTotal = float(len(supportedConsoles))
		supportedConsoles.sort()
		i = 0
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
				i += 1
				self.progress = 40 + (20 * (i / supportedConsoleTotal))
			except ConfigParser.NoOptionError, e:
				logging.error('PESLoadingThread.run: error parsing config file %s: %s' % (userConsolesConfigFile, e.message))
				self.done = True
				self.app.exit(1)
				return
			
		self.progress = 60
		self.app.initSurfaces()
		self.progress = 80
		self.app.initScreens()
		self.progress = 100
		time.sleep(0.1)
		pes.event.pushPesEvent(pes.event.EVENT_RESOURCES_LOADED)
		logging.debug("PESLoadingThread.run: %d complete" % self.progress)
		self.done = True
		return
		
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
		self.__menuItemChanged = False
		self.__lastTick = sdl2.timer.SDL_GetTicks()
		self.screenMargin = 10
		self.wrap = self.screenRect[2] - (self.screenMargin * 2)
		self.menu.setSelected(0)
		self.__uiObjects = []
		self.__menuList = self.addUiObject(List(self.renderer, self.__menuMargin + self.menuRect[0], self.menuRect[1] + self.__menuTopMargin, self.menuRect[2] - (self.__menuMargin * 2), self.menuRect[3] - (self.menuRect[1] + self.__menuTopMargin), self.menu, self.app.menuFont, self.app.menuTextColour, self.app.menuSelectedTextColour, self.app.menuSelectedBgColour, self.app.menuTextColour))
		self.__menuList.setFocus(True)
		
	def addUiObject(self, o):
		if o not in self.__uiObjects:
			self.__uiObjects.append(o)
		return o
		
	def draw(self):
		self.drawMenu()
		self.drawScreen()
		
	def drawMenu(self):
		sdl2.sdlgfx.boxRGBA(self.renderer, self.menuRect[0], self.menuRect[1], self.menuRect[0] + self.menuRect[2], self.menuRect[1] + self.menuRect[3], self.app.menuBackgroundColour.r, self.app.menuBackgroundColour.g, self.app.menuBackgroundColour.b, 255)
		self.__menuList.draw()
	
	def drawScreen(self):
		sdl2.sdlgfx.boxRGBA(self.renderer, self.screenRect[0], self.screenRect[1], self.screenRect[0] + self.screenRect[2], self.screenRect[1] + self.screenRect[3], self.app.backgroundColour.r, self.app.backgroundColour.g, self.app.backgroundColour.b, 255)
	
	def processEvent(self, event):
		if self.menuActive and event.type == sdl2.SDL_KEYDOWN:
			if event.key.keysym.sym == sdl2.SDLK_RETURN or event.key.keysym.sym == sdl2.SDLK_KP_ENTER:
				self.menu.getSelectedItem().trigger()
				self.setMenuActive(False)
				self.__menuList.setFocus(False)
			else:
				self.__menuList.processEvent(event)
	
	def setMenuActive(self, active):
		self.menuActive = active
		self.__menuList.setFocus(True)
		logging.debug("Screen.setMenuActive: \"%s\" activate state is now: %s" % (self.title, self.menuActive))
		
	def stop(self):
		uiObjectLen = len(self.__uiObjects)
		if uiObjectLen > 0:
			logging.debug("Screen.stop: Destroying %d UI objects..." % uiObjectLen)
			for o in self.__uiObjects:
				o.destroy()
	
class ConsoleScreen(Screen):
	
	def __init__(self, app, renderer, menuRect, screenRect, console):
		super(ConsoleScreen, self).__init__(app, renderer, console.getName(), Menu([
			MenuItem("Recently Played"),
			MenuItem("Recently Added"),
			MenuItem("Favourites"),
			MenuItem("Most Played"),
			MenuItem("All"),
			MenuItem("Search"),
		]),
		menuRect, screenRect)
		self.__console = console
		self.__consoleName = console.getName()
		self.menu.setSelected(0)
		self.__thumbXGap = 20
		self.__thumbYGap = 10
		self.__showThumbs = 10
		self.__recentlyAddedThumbCache = []
		self.__recentlyPlayedThumbCache = []
		self.__mostPlayedThumbCache = []
		self.__favourites = []
		self.__desiredThumbWidth = int((screenRect[2] - (self.__showThumbs * self.__thumbXGap)) / self.__showThumbs)
		img = Image.open(console.getNoCoverArtImg())
		img.close()
		width, height = img.size
		ratio = float(height) / float(width)
		self.__thumbWidth = self.__desiredThumbWidth
		self.__thumbHeight = int(ratio * self.__thumbWidth)
		self.__consoleTexture = None
		self.__titleLabel = self.addUiObject(Label(self.renderer, self.screenRect[0] + self.screenMargin, self.screenRect[1], "%s: %s" % (self.__consoleName, self.menu.getSelectedItem().getText()),
 self.app.titleFont, self.app.textColour))
		self.__noGamesFoundLabel = self.addUiObject(Label(self.renderer, self.screenRect[0] + self.screenMargin, self.__titleLabel.y + (self.__titleLabel.height * 2), "No games found.", self.app.bodyFont, self.app.textColour))
		self.__descriptionLabel = self.addUiObject(Label(self.renderer, self.screenRect[0] + self.screenMargin, self.__titleLabel.y + (self.__titleLabel.height * 2), " ", self.app.bodyFont, self.app.textColour))
		self.refresh()
		logging.debug("ConsoleScreen.init: initialised for %s" % self.__consoleName)
		
	def drawScreen(self):
		if self.__consoleTexture == None:
			self.__consoleTexture = sdl2.SDL_CreateTextureFromSurface(self.renderer, self.app.consoleSurfaces[self.__consoleName])
			sdl2.SDL_SetTextureAlphaMod(self.__consoleTexture, CONSOLE_TEXTURE_ALPHA)
		sdl2.SDL_RenderCopy(self.renderer, self.__consoleTexture, None, sdl2.SDL_Rect(self.screenRect[0], self.screenRect[1], self.screenRect[2], self.screenRect[3]))
		self.__titleLabel.draw()
		
		selectedText = self.menu.getSelectedItem().getText()
		if self.menuActive:
			if selectedText == "Recently Added":
				for t in self.__recentlyAddedThumbCache:
					t.draw()
			elif selectedText == "Recently Played":
				if len(self.__recentlyPlayedThumbCache) == 0:
					self.__noGamesFoundLabel.draw()
				else:
					for t in self.__recentlyPlayedThumbCache:
						t.draw()
			elif selectedText == "Favourites":
				if len(self.__favourites) == 0:
					self.__noGamesFoundLabel.draw()
				else:
					pass
			elif selectedText == "Most Played":
				if len(self.__mostPlayedThumbCache) == 0:
					self.__noGamesFoundLabel.draw()
				else:
					for t in self.__mostPlayedThumbCache:
						t.draw()
			elif selectedText == "All":
				self.__descriptionLabel.draw()
			elif selectedText == "Search":
				self.__descriptionLabel.draw()
		else:
			if selectedText == "Recently Added":
				for t in self.__recentlyAddedThumbCache:
					t.draw()
			elif selectedText == "Recently Played":
				if len(self.__recentlyPlayedThumbCache) == 0:
					self.__noGamesFoundLabel.draw()
				else:
					for t in self.__recentlyPlayedThumbCache:
						t.draw()
			elif selectedText == "Favourites":
				if len(self.__favourites) == 0:
					self.__noGamesFoundLabel.draw()
				else:
					pass
			elif selectedText == "Most Played":
				if len(self.__mostPlayedThumbCache) == 0:
					self.__noGamesFoundLabel.draw()
				else:
					for t in self.__mostPlayedThumbCache:
						t.draw()
			elif selectedText == "All":
				pass
			elif selectedText == "Search":
				pass
						
	def refresh(self):
		logging.debug("ConsoleScreen.refresh: reloading content for %s..." % self.__consoleName)
		for t in self.__recentlyPlayedThumbCache:
			t.destroy()
		for t in self.__recentlyAddedThumbCache:
			t.destroy()
		games = self.__console.getRecentlyAddedGames(self.__showThumbs)
		thumbX = self.screenRect[0] + self.screenMargin
		if len(games) > 0:
			for g in games:
				self.__recentlyAddedThumbCache.append(self.addUiObject(Thumbnail(self.renderer, thumbX, self.__titleLabel.y + self.__titleLabel.height + self.__thumbYGap, self.__thumbWidth, self.__thumbHeight, g, self.app.bodyFont, self.app.textColour)))
				thumbX += self.__thumbWidth + self.__thumbXGap
						
	def processEvent(self, event):
		super(ConsoleScreen, self).processEvent(event)
		if self.menuActive:
			if event.type == sdl2.SDL_KEYDOWN and (event.key.keysym.sym == sdl2.SDLK_UP or event.key.keysym.sym == sdl2.SDLK_DOWN):
				self.__titleLabel.setText("%s: %s" % (self.__consoleName, self.menu.getSelectedItem().getText()))
				selectedText = self.menu.getSelectedItem().getText()
				if selectedText == "All":
					self.__descriptionLabel.setText("Browse all %d games." % self.__console.getGameTotal())
				elif selectedText == "Search":
					self.__descriptionLabel.setText("Search for games here.")
					
	def stop(self):
		super(ConsoleScreen, self).stop()
		logging.debug("ConsoleScreen.stop: deleting textures for %s..." % self.__consoleName)
		if self.__consoleTexture:
			sdl2.SDL_DestroyTexture(self.__consoleTexture)
		logging.debug("ConsoleScreen.drawScreen: destorying recently played textures for %s..." % self.__consoleName)
		for t in self.__recentlyPlayedThumbCache:
			t.destroy()
		logging.debug("ConsoleScreen.drawScreen: destorying recently added textures for %s..." % self.__consoleName)
		for t in self.__recentlyAddedThumbCache:
			t.destroy()
	
class HomeScreen(Screen):
	
	def __init__(self, app, renderer, menuRect, screenRect):
		super(HomeScreen, self).__init__(app, renderer, "Home", Menu([MenuItem("Home")]), menuRect, screenRect)
		for c in self.app.consoles:
			if c.getGameTotal() > 0:
				self.menu.addItem(ConsoleMenuItem(c, False, False, self.app.setScreen, "Console %s" % c.getName()))
		self.menu.addItem(MenuItem("Settings", False, False, self.app.setScreen, "Settings"))
		self.menu.addItem(MenuItem("Reboot"))
		self.menu.addItem(MenuItem("Power Off"))
		self.menu.addItem(MenuItem("Exit", False, False, self.app.exit))
		self.__thumbXGap = 20
		self.__thumbYGap = 10
		self.__showThumbs = 10
		self.__recentlyAddedThumbCache = []
		self.__recentlyPlayedThumbCache = []
		self.__desiredThumbWidth = int((screenRect[2] - (self.__showThumbs * self.__thumbXGap)) / self.__showThumbs)
		self.__consoleTexture = None
		self.__consoleSelected = False
		self.__headerLabel = self.addUiObject(Label(self.renderer, self.screenRect[0] + self.screenMargin, self.screenRect[1], "Welcome to PES!", self.app.titleFont, self.app.textColour))
		self.__welcomeText = "The home screen provides you with quick access to your favourite, new additions and most recently played games."
		self.__descriptionLabel = self.addUiObject(Label(self.renderer, self.screenRect[0] + self.screenMargin, self.__headerLabel.y + (self.__headerLabel.height * 2), self.__welcomeText, self.app.bodyFont, self.app.textColour, wrap=self.wrap))
		self.__recentlyAddedText = "Recently Added"
		self.__recentlyAddedLabel = self.addUiObject(Label(self.renderer, self.screenRect[0] + self.screenMargin, self.__headerLabel.y + (self.__headerLabel.height * 2), self.__recentlyAddedText, self.app.bodyFont, self.app.textColour, wrap=self.wrap))
		self.__recentlyPlayedLabel = self.addUiObject(Label(self.renderer, self.screenRect[0] + self.screenMargin, self.__headerLabel.y + (self.__headerLabel.height * 2), "Recently Played", self.app.bodyFont, self.app.textColour, wrap=self.wrap))
		
		#logging.debug("HomeScreen.init: thumbWidth %d" % self.__thumbWidth)
		logging.debug("HomeScreen.init: initialised")
			
	def drawScreen(self):
		super(HomeScreen, self).drawScreen()
		
		self.__headerLabel.draw()
		if self.__consoleSelected:
			sdl2.SDL_RenderCopy(self.renderer, self.__consoleTexture, None, sdl2.SDL_Rect(self.screenRect[0], self.screenRect[1], self.screenRect[2], self.screenRect[3]))
			self.__recentlyAddedLabel.draw()
			for t in self.__recentlyAddedThumbCache:
				t.draw()
			self.__recentlyPlayedLabel.draw()
			for t in self.__recentlyPlayedThumbCache:
				t.draw()
		else:
			self.__descriptionLabel.draw()

	def processEvent(self, event):
		super(HomeScreen, self).processEvent(event)
		if self.menuActive and event.type == sdl2.SDL_KEYDOWN and (event.key.keysym.sym == sdl2.SDLK_UP or event.key.keysym.sym == sdl2.SDLK_DOWN):
			selected = self.menu.getSelectedItem()
			if isinstance(selected, ConsoleMenuItem):
				console = selected.getConsole()
				consoleName = console.getName()
				if self.__consoleTexture:
					sdl2.SDL_DestroyTexture(self.__consoleTexture)
				self.__consoleTexture = sdl2.SDL_CreateTextureFromSurface(self.renderer, self.app.consoleSurfaces[consoleName])
				sdl2.SDL_SetTextureAlphaMod(self.__consoleTexture, CONSOLE_TEXTURE_ALPHA)
				img = Image.open(console.getNoCoverArtImg())
				img.close()
				width, height = img.size
				ratio = float(height) / float(width)
				thumbWidth = self.__desiredThumbWidth
				thumbHeight = int(ratio * thumbWidth)
				self.__headerLabel.setText(consoleName)
				logging.debug("HomeScreen.drawScreen: destroying recently added textures...")
				for t in self.__recentlyAddedThumbCache:
					t.destroy()
				del self.__recentlyAddedThumbCache[:]
				# get recently added
				logging.debug("HomeScreen.drawScreen: getting recently added games for %s..." % consoleName)
				games = console.getRecentlyAddedGames(self.__showThumbs)
				thumbX = self.screenRect[0] + self.screenMargin
				if len(games) > 0:
					for g in games:
						self.__recentlyAddedThumbCache.append(self.addUiObject(Thumbnail(self.renderer, thumbX, self.__recentlyAddedLabel.y + self.__recentlyAddedLabel.height + self.__thumbYGap, thumbWidth, thumbHeight, g, self.app.bodyFont, self.app.textColour)))
						thumbX += thumbWidth + self.__thumbXGap
					self.__recentlyPlayedLabel.y = self.__recentlyAddedLabel.y + self.__recentlyAddedLabel.height + self.__thumbYGap + self.__recentlyAddedThumbCache[0].height + self.__thumbYGap
				else:
					self.__recentlyAddedLabel.setText(self.__recentlyAddedText + ": None added")
				logging.debug("HomeScreen.drawScreen: destorying recently played textures...")
				for t in self.__recentlyPlayedThumbCache:
					t.destroy()
				del self.__recentlyPlayedThumbCache[:]
				# get recently added
				logging.debug("HomeScreen.drawScreen: getting recently played games for %s..." % consoleName)
				games = console.getRecentlyPlayedGames(self.__showThumbs)
				if len(games) > 0:
					thumbX = self.screenRect[0] + self.screenMargin
					for g in games:
						self.__recentlyPlayedThumbCache.append(self.addUiObject(Thumbnail(self.renderer, thumbX, self.__recentlyPlayedLabel.y + self.__recentlyPlayedLabel.height + self.__thumbYGap, thumbWidth, thumbHeight, g, self.app.bodyFont, self.app.textColour)))
						thumbX += thumbWidth + self.__thumbXGap
					self.__recentlyPlayedLabel.setVisible(True)
				else:
					self.__recentlyPlayedLabel.setVisible(False)
					
				self.__consoleSelected = True
			else:
				self.__consoleSelected = False
				if selected.getText() == "Home":
					self.__headerLabel.setText("Welcome to PES!")
					self.__descriptionLabel.setText(self.__welcomeText)
				elif selected.getText() == "Reboot":
					self.__headerLabel.setText("Reboot")
					self.__descriptionLabel.setText("Select this menu item to reboot your system.")
				elif selected.getText() == "Exit":
					self.__headerLabel.setText("Exit")
					self.__descriptionLabel.setText("Select this menu item to exit the PES GUI and return to the command line.")
				elif selected.getText() == "Settings":
					self.__headerLabel.setText("Settings")
					self.__descriptionLabel.setText("Select this menu item to customise PES and to add ROMs to PES' database.")
				elif selected.getText() == "Power Off":
					self.__headerLabel.setText("Power Off")
					self.__descriptionLabel.setText("Select this menu item to power off your system.")
		
	def refreshMenu(self):
		logging.debug("HomeScreen.refreshMenu: refreshing menu contents...")
		items = self.menu.getItems()
		for m in items:
			if isinstance(m, ConsoleMenuItem):
				logging.debug("HomeScreen.refreshMenu: removing %s" % m.getText())
				self.menu.removeItem(m)
			else:
				logging.debug("HomeScreen.refreshMenu: not removing %s" % m.getText())
		for c in self.app.consoles:
			if c.getGameTotal() > 0:
				logging.debug("HomeScreen.refreshMenu: inserting %s" % c.getName())
				self.menu.insertItem(len(self.menu.getItems()) - 4, ConsoleMenuItem(c, False, False, self.app.setScreen, "Console %s" % c.getName()))
		self.menu.setSelected(0, deselectAll=True)
		
	def stop(self):
		super(HomeScreen, self).stop()
		logging.debug("HomeScreen.stop: deleting textures...")
		sdl2.SDL_DestroyTexture(self.__consoleTexture)
		
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
		self.__updateDatabaseMenu = Menu([])
		for c in self.app.consoles:
			self.__updateDatabaseMenu.addItem(ConsoleMenuItem(c, False, True))
		self.__toggleMargin = 20
		self.__updateDbThread = None
		self.__scanProgressBar = None
		self.__defaultHeaderText = "Settings"
		self.__headerLabel = self.addUiObject(Label(self.renderer, self.screenRect[0] + self.screenMargin, self.screenRect[1], self.__defaultHeaderText, self.app.titleFont, self.app.textColour))
		logging.debug("SettingsScreen.init: initialised")
		self.__initText = "Here you can scan for new games, set-up your joysticks as well as being able to reset PES to its default settings\n\nPlease select an item from the menu on the left."
		self.__scanText = "Please use the menu below to select which consoles you wish to include in your search. By default all consoles are selected.\n\nWhen you are ready, please select the \"Begin Scan\" button."
		self.__descriptionLabel = self.addUiObject(Label(self.renderer, self.screenRect[0] + self.screenMargin, self.__headerLabel.y + (self.__headerLabel.height * 2), self.__initText, self.app.bodyFont, self.app.textColour, wrap=self.screenRect[2] - self.screenMargin))
		self.__consoleList = None
		self.__scanButton = None

	def drawScreen(self):
		super(SettingsScreen, self).drawScreen()
		#logging.debug("SettingsScreen.draw: drawing screen at (%d, %d) dimensions (%d, %d)" % (self.screenRect[0], self.screenRect[1], self.screenRect[2], self.screenRect[3]))
		
		currentX = self.screenRect[0] + self.screenMargin
		currentY = self.screenRect[1]
		
		self.__headerLabel.draw()
		self.__descriptionLabel.draw()
		
		if self.__init:
			return
		
		selected = self.menu.getSelectedItem().getText()
		
		if selected == "Update Database":
			if self.__updateDbThread != None:
				if self.__updateDbThread.started and not self.__updateDbThread.done:
					self.__descriptionLabel.setText("Scanned %d out of %d roms... press BACK to abort\n\nElapsed: %s\n\nRemaining: %s\n\nProgress:" % (self.__updateDbThread.getProcessed(), self.__updateDbThread.romTotal, self.__updateDbThread.getElapsed(), self.__updateDbThread.getRemaining()))
					self.__scanProgressBar.y = self.__descriptionLabel.y + self.__descriptionLabel.height + 10
					self.__scanProgressBar.setProgress(self.__updateDbThread.getProgress())
					self.__scanProgressBar.draw()
				elif self.__updateDbThread.done:
					interruptedStr = ""
					if self.__updateDbThread.interrupted:
						interruptedStr = "(scan interrupted)"
					self.__descriptionLabel.setText("Scan completed in %s %s\n\nAdded: %d\n\nUpdated: %d\n\nDeleted: %d\n\nPress BACK to return to the previous screen." % (self.__updateDbThread.getElapsed(), interruptedStr, self.__updateDbThread.added, self.__updateDbThread.updated, self.__updateDbThread.deleted))
			else:
				self.__consoleList.draw()
				self.__scanButton.draw()
		
	def processEvent(self, event):
		selected = self.menu.getSelectedItem().getText()
		oldMenuActive = self.menuActive # store state before parent method changes it!
		
		# don't pass up the event if a db scan is in progress
		if event.type == sdl2.SDL_KEYDOWN and selected == "Update Database" and self.__updateDbThread != None:
			if event.key.keysym.sym == sdl2.SDLK_BACKSPACE:
				if self.__updateDbThread.started and not self.__updateDbThread.done:
					self.setMenuActive(False)
					self.__updateDbThread.stop()
				elif selected == "Update Database" and self.__updateDbThread.done:
					self.setMenuActive(False)
					self.__updateDbThread = None
					self.__descriptionLabel.setText(self.__scanText)
					self.__scanButton.setFocus(False)
					self.__consoleList.setFocus(True)
					self.__updateDatabaseMenu.toggleAll(True)
					self.__updateDatabaseMenu.setSelected(0)
					#self.__consoleList.scrollTop()
			return
		
		super(SettingsScreen, self).processEvent(event)
		
		#if event.type == pes.event.EVENT_TYPE:
		#	(t, d1, d2) = pes.event.decodePesEvent(event)
		#	logging.debug("SettingsScreen.processEvent: trapping PES Event")
		#	if t == pes.event.EVENT_DB_UPDATE and self.__updateDbThread != None:
		#		self.__updateDbThread = None
		
		if oldMenuActive:
			if event.type == sdl2.SDL_KEYDOWN and (event.key.keysym.sym == sdl2.SDLK_RETURN or event.key.keysym.sym == sdl2.SDLK_KP_ENTER):
				logging.debug("SettingsScreen.processEvent: return key trapped for %s" % selected)
				if selected == "Update Database":
					self.__headerLabel.setText(selected)
					self.__updateDatabaseMenu.toggleAll(True)
					self.__descriptionLabel.setText(self.__scanText)
					if self.__consoleList != None:
						self.__consoleList.destroy()
					consoleListY = self.__descriptionLabel.y + self.__descriptionLabel.height + 10
					self.__consoleList = self.addUiObject(List(self.renderer, self.__descriptionLabel.x + self.__toggleMargin, consoleListY, 300, self.screenRect[3] - consoleListY, self.__updateDatabaseMenu, self.app.bodyFont, self.app.textColour, self.app.textColour, self.app.menuSelectedBgColour, self.app.menuTextColour))
					self.__consoleList.setFocus(True)
					self.__updateDatabaseMenu.setSelected(0)
					if self.__scanButton == None:
						self.__scanButton = self.addUiObject(Button(self.renderer, self.__consoleList.x + self.__consoleList.width + 200, self.__consoleList.y, 150, 50, "Begin Scan", self.app.bodyFont, self.app.textColour, self.app.menuSelectedBgColour, self.startScan))
					self.__scanButton.setFocus(False)
				elif selected == "About":
					self.__headerLabel.setText(selected)
					self.__descriptionLabel.setText("Pi Entertainment System version %s\n\nReleased: %s\n\nLicense: Licensed under version 3 of the GNU Public License (GPL)\nAuthor: %s\n\nContributors: Eric Smith\n\nCover art: theGamesDB.net\n\nDocumentation: http://pes.mundayweb.com\n\nFacebook: https://www.facebook.com/pientertainmentsystem\n\nHelp: pes@mundayweb.com" % (VERSION_NUMBER, VERSION_DATE, VERSION_AUTHOR))
				elif selected == "Joystick Set-Up":
					self.__headerLabel.setText(selected)
					self.__descriptionLabel.setText("To be implemented.")
					
				self.__init = False
		else:
				if selected == "Update Database":
					if event.type == sdl2.SDL_KEYDOWN:
						if event.key.keysym.sym == sdl2.SDLK_RIGHT:
							self.__consoleList.setFocus(False)
							self.__scanButton.setFocus(True)
						elif event.key.keysym.sym == sdl2.SDLK_LEFT:
							self.__consoleList.setFocus(True)
							self.__scanButton.setFocus(False)
						else:
							self.__consoleList.processEvent(event)
							if self.__updateDatabaseMenu.getToggledCount() == 0:
								self.__scanButton.setVisible(False)
							else:
								self.__scanButton.setVisible(True)
								self.__scanButton.processEvent(event)

		if self.menuActive: # this will be true if parent method trapped a backspace event
			if event.type == sdl2.SDL_KEYDOWN:
				if event.key.keysym.sym == sdl2.SDLK_BACKSPACE:
					logging.debug("SettingsScreen.processEvent: trapping backspace event")
					self.__init = True
					self.__headerLabel.setText(self.__defaultHeaderText)
					self.__descriptionLabel.setText(self.__initText)

	def startScan(self):
		logging.debug("SettingsScreen.startScan: beginning scan...")
		if self.__scanProgressBar == None:
			self.__scanProgressBar = ProgressBar(self.renderer, self.screenRect[0] + self.screenMargin, self.__descriptionLabel.y + self.__descriptionLabel.height + 10, self.screenRect[2] - (self.screenMargin * 2), 40, self.app.lineColour, self.app.menuBackgroundColour)
		else:
			self.__scanProgressBar.setProgress(0)
		self.__updateDbThread = UpdateDbThread([c.getConsole() for c in self.__updateDatabaseMenu.getToggled()])
		self.__updateDbThread.start()
									
	def stop(self):
		logging.debug("SettingsScreen.stop: deleting UI objects...")
		super(SettingsScreen, self).stop()
		if self.__updateDbThread:
			self.__updateDbThread.stop()