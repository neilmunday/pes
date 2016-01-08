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

def getTextureDimensions(texture):
	flags = c_uint32()
	access = c_int()
	w = c_int()
	h = c_int()
	ret = sdl2.SDL_QueryTexture(texture, byref(flags), byref(access), byref(w), byref(h))
	return (w.value, h.value)

def renderLines(renderer, font, lines, colour, x, y, wrap):
	w = 0
	totalHeight = 0
	for l in lines:
		(w, h) = renderText(renderer, font, l, colour, x, y, wrap)
		y += h
		totalHeight += h
	return (w, totalHeight)

def renderText(renderer, font, txt, colour, x, y, wrap=0, width=0):
	texture = createText(renderer, font, txt, colour, wrap)
	(w, h) = getTextureDimensions(texture)
	if width > 0 and w > width:
		dotTexture = createText(renderer, font, '...', colour)
		(tw, th) = getTextureDimensions(dotTexture)
		sdl2.SDL_RenderCopy(renderer, texture, sdl2.SDL_Rect(0, 0, width - tw, h), sdl2.SDL_Rect(x, y, width - tw, h))
		sdl2.SDL_RenderCopy(renderer, dotTexture, None, sdl2.SDL_Rect(x + (width - tw), y, tw, th))
		sdl2.SDL_DestroyTexture(texture)
		sdl2.SDL_DestroyTexture(dotTexture)
	else:
		sdl2.SDL_RenderCopy(renderer, texture, None, sdl2.SDL_Rect(x, y, w, h))
		sdl2.SDL_DestroyTexture(texture)
	return (w, h)

def getScaleImageDimensions(texture, bx, by):
	"""
	Original author: Frank Raiser (crashchaos@gmx.net)
	URL: http://www.pygame.org/pcr/transform_scale
	Modified by Neil Munday
	"""
	ix, iy = getTextureDimensions(texture)
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
	return (int(sx),int(sy))

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
		
	def initScreens(self):
		logging.debug("PESApp.initScreens: initialising screens...")
		self.screens["Home"] = HomeScreen(self, self.renderer, self.menuRect, self.screenRect)
		self.screens["Settings"] = SettingsScreen(self, self.renderer, self.menuRect, self.screenRect)
		for c in self.consoles:
			self.screens["Console %s" % c.getName()] = ConsoleScreen(self, self.renderer, self.menuRect, self.screenRect, c)
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
		self.bodyFontHeight = getFontHeight(self.bodyFont)
		
		self.renderer = sdl2.SDL_CreateRenderer(self.__window, -1, sdl2.render.SDL_RENDERER_ACCELERATED)
		
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
				if event.type == pes.event.EVENT_TYPE:
					(t, d1, d2) = pes.event.decodePesEvent(event)
					logging.debug("PESApp.run: trapping PES Event")
					if not loading and t == pes.event.EVENT_DB_UPDATE:
						for c in self.consoles:
							c.refresh()
						self.screens["Home"].refreshMenu()
					elif t == pes.event.EVENT_RESOURCES_LOADED:
						pass
				
				if not loading:
					# keyboard events
					if event.type == sdl2.SDL_KEYDOWN:
						if event.key.keysym.sym == sdl2.SDLK_BACKSPACE:
							logging.debug("PESApp.run: trapping backspace key event")
							if not self.screens[self.screenStack[-1]].menuActive:
								self.screens[self.screenStack[-1]].setMenuActive(True)
							else:
								# pop the screen
								screenStackLen = len(self.screenStack)
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
					progressBar.setProgress(loadingThread.progress)
					progressBar.draw()
			else:
				#self.initTextures()
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
		#if self.consoleTextures:
		#	for key, value in self.consoleTextures.iteritems():
		#		sdl2.SDL_DestroyTexture(value)
		self.exit(0)
		
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
				
		self.progress = 40
		
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
	
class UIObject(object):
	
	def __init__(self, renderer, x, y, width, height):
		self.renderer = renderer
		self.x = x
		self.y = y
		self.width = width
		self.height = height
	
	def destroy(self):
		pass
	
	def draw(self):
		pass
	
	def setCoords(self, x, y):
		self.x = x
		self.y = y
		
	def setSize(self, w, h):
		self.w = w
		self.h = h

class ProgressBar(UIObject):
	
	def __init__(self, renderer, x, y, width, height, colour, backgroundColour):
		super(ProgressBar, self).__init__(renderer, x, y, width, height)
		self.__progress = 0.0 # percent complete
		self.__colour = colour
		self.__backgroundColour = backgroundColour
		logging.debug("ProgressBar.init: initialised")
	
	def draw(self):
		margin = 3
		w = int(self.width * (self.__progress / 100.0))
		sdl2.sdlgfx.boxRGBA(self.renderer, self.x, self.y, self.x + self.width, self.y + self.height, self.__backgroundColour.r, self.__backgroundColour.g, self.__backgroundColour.b, 255)
		sdl2.sdlgfx.boxRGBA(self.renderer, self.x + margin, self.y + margin, self.x + w - margin, self.y + self.height - margin, self.__colour.r, self.__colour.g, self.__colour.b, 255)
	
	def setProgress(self, p):
		if p > 100:
			raise ValueError("%d is greater than 100" % p)
		if p < 0:
			raise ValueError("%d is less than 0" % p)
		self.__progress = p
		
class Thumbnail(UIObject):
	
	__cache = {} # shared texture cache
	
	def __init__(self, renderer, x, y, width, height, game, font, txtColour):
		self.__font = font
		self.__fontHeight = sdl2.sdlttf.TTF_FontHeight(self.__font)
		self.__thumbWidth = width
		self.__thumbHeight = height
		height += 1 + self.__fontHeight # allow space for label
		super(Thumbnail, self).__init__(renderer, x, y, width, height)
		self.__txtColour = txtColour
		self.__game = game
		self.__coverart = game.getCoverArt()
		if self.__coverart == None:
			self.__coverart = game.getConsole().getNoCoverArtImg()
		self.__coverartTexture = None
		logging.debug("Thumbnail.init: initialised for %s" % game.getName())
		
	def draw(self):
		if self.__coverartTexture == None:
			gameId = self.__game.getId()
			if gameId in self.__cache:
				self.__coverartTexture = self.__cache[gameId]
			else:
				logging.debug("Thumbnail.draw: loading texture for %s" % self.__game.getName())
				self.__coverartTexture = sdl2.sdlimage.IMG_LoadTexture(self.renderer, self.__coverart)
				self.__cache[gameId] = self.__coverartTexture
		sdl2.SDL_RenderCopy(self.renderer, self.__coverartTexture, None, sdl2.SDL_Rect(self.x, self.y, self.__thumbWidth, self.__thumbHeight))
		# render text underneath
		renderText(self.renderer, self.__font, self.__game.getName(), self.__txtColour, self.x, self.y + self.__thumbHeight + 1, 0, self.width)
		
	@staticmethod
	def destroyTextures():
		logging.debug("Thumbnail.destroyTextures: purging %d textures..." % len(Thumbnail.__cache))
		keys = []
		for key, value in Thumbnail.__cache.iteritems():
			sdl2.SDL_DestroyTexture(value)
			keys.append(key)
		for k in keys:
			del Thumbnail.__cache[k]

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
		return list(self.__items)
	
	def getSelectedIndex(self):
		return self.__selected
	
	def getSelectedItem(self):
		return self.__items[self.__selected]
	
	def getCount(self):
		return len(self.__items)
	
	def getToggled(self):
		toggled = []
		for i in self.__items:
			if i.isToggled():
				toggled.append(i)
		return toggled
	
	def insertItem(self, i, m):
		self.__items.insert(i, m)
	
	def removeItem(self, m):
		self.__items.remove(m)
		
	def setSelected(self, i, deselectAll=False):
		if i >= 0 and i < len(self.__items):
			if deselectAll:
				for m in self.__items:
					m.setSelected(False)
			else:
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
		
	def isToggable(self):
		return self.__toggable
	
	def setSelected(self, selected):
		self.__selected = selected
	
	def setText(self, text):
		self.__text = text
		
	def toggle(self, t):
		self.__toggled = t
		
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
	
	def __init__(self, console, selected = False, toggable = False, callback = None, *callbackArgs):
		super(ConsoleMenuItem, self).__init__(console.getName(), selected, toggable, callback, *callbackArgs)
		self.__console = console
		
	def getConsole(self):
		return self.__console
		
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
		self.menu.setSelected(0)
		self.__thumbCache = {}
		self.__thumbGap = 10
		self.__recentGameTotal = 10
		self.__thumbWidth = 150
		self.__thumbHeight = self.__thumbWidth
		self.__consoleTexture = None
		
	def drawScreen(self):
		currentX = self.screenRect[0] + self.screenMargin
		currentY = self.screenRect[1]
		consoleName = self.__console.getName()
		selectedItem = self.menu.getSelectedItem()
		selectedText = selectedItem.getText()
		
		if self.__consoleTexture == None:
			self.__consoleTexture = sdl2.SDL_CreateTextureFromSurface(self.renderer, self.app.consoleSurfaces[consoleName])
			sdl2.SDL_SetTextureAlphaMod(self.__consoleTexture, CONSOLE_TEXTURE_ALPHA)
		
		sdl2.SDL_RenderCopy(self.renderer, self.__consoleTexture, None, sdl2.SDL_Rect(self.screenRect[0], self.screenRect[1], self.screenRect[2], self.screenRect[3]))
		(textWidth, textHeight) = renderText(self.renderer, self.app.titleFont, "%s: %s" % (consoleName, selectedText), self.app.textColour, currentX, self.screenRect[1])
		currentY += textHeight * 2
		
		if selectedText == "Recently Added":
			thumbX = currentX
			recentGames = self.__console.getRecentlyAddedGames(self.__recentGameTotal)
			for g in recentGames:
				art = g.getCoverArt()
				if art != None:
					texture = None
					if g.getId() not in self.__thumbCache.keys():
						texture = sdl2.sdlimage.IMG_LoadTexture(self.renderer, art)
						self.__thumbCache[g.getId()] = texture
					else:
						texture = self.__thumbCache[g.getId()]
					
					if thumbX + self.__thumbWidth < self.screenRect[0] + self.screenRect[2]:
						sdl2.SDL_RenderCopy(self.renderer, texture, None, sdl2.SDL_Rect(thumbX, currentY, self.__thumbWidth, self.__thumbHeight))
						# render text underneath
						renderText(self.renderer, self.app.bodyFont, g.getName(), self.app.textColour, thumbX, currentY + self.__thumbHeight + 1, 0, self.__thumbWidth)
						thumbX += self.__thumbWidth + self.__thumbGap
		elif selectedText == "Recently Played":
			thumbX = currentX
			recentGames = self.__console.getRecentlyPlayedGames(self.__recentGameTotal)
			for g in recentGames:
				art = g.getCoverArt()
				if art != None:
					texture = None
					if g.getId() not in self.__thumbCache.keys():
						texture = sdl2.sdlimage.IMG_LoadTexture(self.renderer, art)
						self.__thumbCache[g.getId()] = texture
					else:
						texture = self.__thumbCache[g.getId()]
					
					if thumbX + self.__thumbWidth < self.screenRect[0] + self.screenRect[2]:
						sdl2.SDL_RenderCopy(self.renderer, texture, None, sdl2.SDL_Rect(thumbX, currentY, self.__thumbWidth, self.__thumbHeight))
						# render text underneath
						renderText(self.renderer, self.app.bodyFont, g.getName(), self.app.textColour, thumbX, currentY + self.__thumbHeight + 1, 0, self.__thumbWidth)
						thumbX += self.__thumbWidth + self.__thumbGap
					
	def stop(self):
		logging.debug("ConsoleScreen.stop: deleting %d textures for %s..." % (len(self.__thumbCache), self.__console.getName()))
		if self.__consoleTexture:
			sdl2.SDL_DestroyTexture(self.__consoleTexture)
		for value in self.__thumbCache.itervalues():
			sdl2.SDL_DestroyTexture(value)
	
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
		self.__thumbGap = 20
		self.__showThumbs = 10
		self.__thumbWidth = -1
		self.__thumbHeight = -1
		self.__recentlyAddedThumbCache = []
		self.__recentlyPlayedThumbCache = []
		self.__desiredThumbWidth = int((screenRect[2] - (self.__showThumbs * self.__thumbGap)) / self.__showThumbs)
		self.__consoleTexture = None
		self.__consoleChanged = False
		
		#logging.debug("HomeScreen.init: thumbWidth %d" % self.__thumbWidth)
		logging.debug("HomeScreen.init: initialised")
			
	def drawScreen(self):
		super(HomeScreen, self).drawScreen()
		#logging.debug("HomeScreen.draw: drawing screen at (%d, %d) dimensions (%d, %d)" % (self.screenRect[0], self.screenRect[1], self.screenRect[2], self.screenRect[3]))
		selected = self.menu.getSelectedItem()
		
		currentX = self.screenRect[0] + self.screenMargin
		currentY = self.screenRect[1]
		
		if selected.getText() == "Home":
			(textWidth, textHeight) = renderText(self.renderer, self.app.titleFont, "Welcome to PES!", self.app.textColour, currentX, currentY)
			currentY += (textHeight * 2)
			(textWidth, textHeight) = renderText(self.renderer, self.app.bodyFont, "The home screen provides you with quick access to your favourite, new additions and most recently played games.", self.app.textColour, currentX, currentY, self.wrap)
		elif selected.getText() == "Reboot":
			(textWidth, textHeight) = renderText(self.renderer, self.app.titleFont, "Reboot", self.app.textColour, currentX, self.screenRect[1])
			currentY += (textHeight * 2)
			(textWidth, textHeight) = renderText(self.renderer, self.app.bodyFont, "Select this menu item to reboot your system.", self.app.textColour, self.screenRect[0] + self.screenMargin, currentY, self.wrap)
		elif selected.getText() == "Exit":
			(textWidth, textHeight) = renderText(self.renderer, self.app.titleFont, "Exit", self.app.textColour, currentX, self.screenRect[1])
			currentY += (textHeight * 2)
			(textWidth, textHeight) = renderText(self.renderer, self.app.bodyFont, "Select this menu item to exit the PES GUI and return to the command line.", self.app.textColour, currentX, currentY, self.wrap)
		elif selected.getText() == "Settings":
			(textWidth, textHeight) = renderText(self.renderer, self.app.titleFont, "Settings", self.app.textColour, currentX, self.screenRect[1])
			currentY += (textHeight * 2)
			(textWidth, textHeight) = renderText(self.renderer, self.app.bodyFont, "Select this menu item to customise PES and to add ROMs to PES' database.", self.app.textColour, currentX, currentY, self.wrap)
		elif selected.getText() == "Power Off":
			(textWidth, textHeight) = renderText(self.renderer, self.app.titleFont, "Power Off", self.app.textColour, currentX, self.screenRect[1])
			currentY += (textHeight * 2)
			(textWidth, textHeight) = renderText(self.renderer, self.app.bodyFont, "Select this menu item to turn your system off.", self.app.textColour, currentX, currentY, self.wrap)
		elif isinstance(selected, ConsoleMenuItem):
			
			console = selected.getConsole()
			consoleName = console.getName()
			sdl2.SDL_RenderCopy(self.renderer, self.__consoleTexture, None, sdl2.SDL_Rect(self.screenRect[0], self.screenRect[1], self.screenRect[2], self.screenRect[3]))
			(textWidth, textHeight) = renderText(self.renderer, self.app.titleFont, consoleName, self.app.textColour, currentX, self.screenRect[1])
			
			currentY += (textHeight * 2)
			
			(textWidth, textHeight) = renderText(self.renderer, self.app.bodyFont, "Recently Added:", self.app.textColour, currentX, currentY)
			
			currentY += textHeight + 10
			
			if self.__consoleChanged:
				logging.debug("HomeScreen.drawScreen: destorying recently added textures...")
				for t in self.__recentlyAddedThumbCache:
					t.destroy()
				del self.__recentlyAddedThumbCache[:]
				# get recently added
				logging.debug("HomeScreen.drawScreen: getting recently added games for %s..." % consoleName)
				games = console.getRecentlyAddedGames(self.__showThumbs)
				thumbX = currentX
				for g in games:
					self.__recentlyAddedThumbCache.append(Thumbnail(self.renderer, thumbX, currentY, self.__thumbWidth, self.__thumbHeight, g, self.app.bodyFont, self.app.textColour))
					thumbX += self.__thumbWidth + self.__thumbGap
				
			for t in self.__recentlyAddedThumbCache:
				t.draw()
				
			currentY += self.__recentlyAddedThumbCache[0].height + 10
			
			if len(self.__recentlyPlayedThumbCache) > 0:
				(textWidth, textHeight) = renderText(self.renderer, self.app.bodyFont, "Recently Played:", self.app.textColour, currentX, currentY)
				
				if self.__consoleChanged:
					logging.debug("HomeScreen.drawScreen: destorying recently played textures...")
					for t in self.__recentlyPlayedThumbCache:
						t.destroy()
					del self.__recentlyPlayedThumbCache[:]
					# get recently added
					logging.debug("HomeScreen.drawScreen: getting recently played games for %s..." % consoleName)
					games = console.getRecentlyPlayedGames(self.__showThumbs)
					thumbX = currentX
					for g in games:
						self.__recentlyPlayedThumbCache.append(Thumbnail(self.renderer, thumbX, currentY, self.__thumbWidth, self.__thumbHeight, g, self.app.bodyFont, self.app.textColour))
						thumbX += self.__thumbWidth + self.__thumbGap
					
				for t in self.__recentlyPlayedThumbCache:
					t.draw()
			
			if self.__consoleChanged:
				self.__consoleChanged = False
			
	def processEvent(self, event):
		super(HomeScreen, self).processEvent(event)
		if self.menuActive and event.type == sdl2.SDL_KEYDOWN and (event.key.keysym.sym == sdl2.SDLK_UP or event.key.keysym.sym == sdl2.SDLK_DOWN):
			selected = self.menu.getSelectedItem()
			if isinstance(selected, ConsoleMenuItem):
				console = selected.getConsole()
				self.__consoleTexture = sdl2.SDL_CreateTextureFromSurface(self.renderer, self.app.consoleSurfaces[console.getName()])
				sdl2.SDL_SetTextureAlphaMod(self.__consoleTexture, CONSOLE_TEXTURE_ALPHA)
				img = Image.open(console.getNoCoverArtImg())
				img.close()
				width, height = img.size
				ratio = float(height) / float(width)
				self.__thumbWidth = self.__desiredThumbWidth
				self.__thumbHeight = int(ratio * self.__thumbWidth)
				self.__consoleChanged = True
		
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
				logging.debug("HomeScreen.refreshMenu: adding %s" % c.getName())
				self.menu.insertItem(len(self.menu.getItems()) - 4, ConsoleMenuItem(c))
		self.menu.setSelected(0, True)
		
	def stop(self):
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
		self.__updateDatabaseMenu = Menu([MenuItem("Begin Scan", True)])
		for c in self.app.consoles:
			self.__updateDatabaseMenu.addItem(ConsoleMenuItem(c, False, True))
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
				(textWidth, textHeight) = renderLines(self.renderer, self.app.bodyFont, ["Scanned %d out of %d roms... press BACK to abort" % (self.__updateDbThread.getProcessed(), self.__updateDbThread.romTotal), " ", "Elapsed: %s" % self.__updateDbThread.getElapsed(), " ", "Remaining: %s" % self.__updateDbThread.getRemaining(), " ", "Progress:"], self.app.textColour, currentX, currentY, self.wrap)
				currentY += textHeight + 20
				self.__scanProgressBar.setCoords(currentX, currentY)
				self.__scanProgressBar.setProgress(self.__updateDbThread.getProgress())
				self.__scanProgressBar.draw()
			elif self.__updateDbThread.done:
				interruptedStr = ""
				if self.__updateDbThread.interrupted:
					interruptedStr = "(scan interrupted)"
				renderLines(self.renderer, self.app.bodyFont, ["Scan completed in %s %s" % (self.__updateDbThread.getElapsed(), interruptedStr), " ", "Added: %d" % self.__updateDbThread.added, " ", "Updated: %d" % self.__updateDbThread.updated, " " , "Deleted: %d" % self.__updateDbThread.deleted, " ", "Press BACK to return to the previous screen."], self.app.textColour, currentX, currentY, self.wrap)
				#self.app.screens["Home"].refreshMenu()

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
		if event.type == sdl2.SDL_KEYDOWN and selected == "Update Database" and self.__updateDbThread != None:
			if event.key.keysym.sym == sdl2.SDLK_BACKSPACE:
				if self.__updateDbThread.started and not self.__updateDbThread.done:
					self.setMenuActive(False)
					self.__updateDbThread.stop()
					return
				elif selected == "Update Database"  and self.__updateDbThread != None and self.__updateDbThread.done:
					self.setMenuActive(False)
					self.__updateDbThread = None
					return
			return
		
		super(SettingsScreen, self).processEvent(event)
		
		#if event.type == pes.event.EVENT_TYPE:
		#	(t, d1, d2) = pes.event.decodePesEvent(event)
		#	logging.debug("SettingsScreen.processEvent: trapping PES Event")
		#	if t == pes.event.EVENT_DB_UPDATE and self.__updateDbThread != None:
		#		self.__updateDbThread = None
		
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
							
							consoles = []
							for c in self.__updateDatabaseMenu.getToggled():
								consoles.append(c.getConsole())
								
							self.__updateDbThread = UpdateDbThread(consoles)
							self.__updateDbThread.start()
						
	def stop(self):
		if self.__updateDbThread:
			self.__updateDbThread.stop()