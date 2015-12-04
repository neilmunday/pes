from datetime import datetime
from pes import pesExit, VERSION_NUMBER, VERSION_AUTHOR, VERSION_DATE
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
import sys
from time import sleep
import threading
from ctypes import c_int, c_uint32, byref

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
	for l in lines:
		(w, h) = renderText(renderer, font, l, colour, x, y, wrap)
		y += h

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

	def __init__(self, dimensions, fontFile, backgroundColour, menuBackgroundColour, headerBackgroundColour, lineColour, textColour, menuTextColour, menuSelectedTextColour, consoles):
		super(PESApp, self).__init__()
		self.__dimensions = dimensions
		self.fontFile = fontFile
		self.consoles = consoles
		
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
		
	def exit(self):
		# tidy up
		logging.debug("tidying up...")
		sdl2.sdlttf.TTF_CloseFont(self.headerFont)
		sdl2.sdlttf.TTF_CloseFont(self.bodyFont)
		sdl2.sdlttf.TTF_CloseFont(self.menuFont)
		sdl2.sdlttf.TTF_CloseFont(self.titleFont)
		sdl2.sdlttf.TTF_CloseFont(self.splashFont)
		sdl2.sdlttf.TTF_Quit()
		sdl2.SDL_Quit()
		logging.info("exiting...")
		sys.exit(0)
        
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
			self.__window = sdl2.video.SDL_CreateWindow('PES', sdl2.video.SDL_WINDOWPOS_UNDEFINED, sdl2.video.SDL_WINDOWPOS_UNDEFINED, self.__dimensions[0], self.__dimensions[1], self.__dimensions[0], self.__dimensions[1], sdl2.video.SDL_WINDOW_FULLSCREEN)
		else:
			# windowed
			logging.debug("PESApp.run: running windowed")
			self.__window = sdl2.video.SDL_CreateWindow('PES', sdl2.video.SDL_WINDOWPOS_UNDEFINED, sdl2.video.SDL_WINDOWPOS_UNDEFINED, self.__dimensions[0], self.__dimensions[1], 0)
		
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
		self.menuWidth = 200
		self.menuHeight = self.__dimensions[1] - self.__footerHeight - self.__headerHeight
		
		menuRect = [0, self.__headerHeight + 1, self.menuWidth, self.__dimensions[1] - self.__headerHeight + 1]
		screenRect = [self.menuWidth + 1, self.__headerHeight + 1, self.__dimensions[0] - self.menuWidth + 1, self.__dimensions[1] - self.__headerHeight + 1]
		
		renderer = sdl2.SDL_CreateRenderer(self.__window, -1, sdl2.render.SDL_RENDERER_ACCELERATED)
		#sdl2.SDL_RenderSetLogicalSize(renderer, 1024, 576)
		
		# pre-initialise screens
		self.__screens = {}
		self.__screens["Home"] = HomeScreen(self, renderer, menuRect, screenRect)
		self.__screens["Settings"] = SettingsScreen(self, renderer, menuRect, screenRect)
		self.__screenStack = ["Home"]
		
		headerTexture = createText(renderer, self.headerFont, "Pi Entertainment System", self.textColour)
		(headerTextureWidth, headerTextureHeight) = getTextureDimensions(headerTexture)
		
		dateTexture = None
		
		splashTexture = createText(renderer, self.splashFont, "Pi Entertainment System", self.textColour)
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
		loadingThread = PESLoadingThread()
		
		while running:
			events = sdl2.ext.get_events()
			for event in events:
				if not loading:
					# keyboard events
					if event.type == sdl2.SDL_KEYDOWN:
						if event.key.keysym.sym == sdl2.SDLK_BACKSPACE:
							logging.debug("PESApp.run: trapping backspace key event")
							if not self.__screens[self.__screenStack[-1]].menuActive:
								self.__screens[self.__screenStack[-1]].setMenuActive(True)
							else:
								# pop the screen
								screenStackLen = len(self.__screenStack)
								logging.debug("PESApp.run: popping screen stack, current length: %d" % screenStackLen)
								if screenStackLen > 1:
									self.__screenStack.pop()
									self.setScreen(self.__screenStack[-1])
					self.__screens[self.__screenStack[-1]].processEvent(event)
								
				if event.type == sdl2.SDL_KEYDOWN and event.key.keysym.sym == sdl2.SDLK_ESCAPE:
					logging.debug("PESApp.run: trapping escape key event")
					running = False
					break
					
				# joystick events
				if event.type == sdl2.SDL_QUIT:
					running = False
					break
				
			sdl2.SDL_SetRenderDrawColor(renderer, self.backgroundColour.r, self.backgroundColour.g, self.backgroundColour.b, 255)
			sdl2.SDL_RenderClear(renderer)
			
			if loading:
				if not loadingThread.started:
					loadingThread.start()
				tick = sdl2.timer.SDL_GetTicks()
				if splashTextureAlpha < 255 and tick - lastTick > 200: # a second has passed
					splashTextureAlpha += 25
					if splashTextureAlpha > 255:
						splashTextureAlpha = 255
					lastTick = tick
				sdl2.SDL_SetTextureAlphaMod(splashTexture, splashTextureAlpha)
				sdl2.SDL_RenderCopy(renderer, splashTexture, None, sdl2.SDL_Rect(splashTextureX, splashTextureY, splashTextureWidth, splashTextureHeight))
				if loadingThread.done:
					loading = False
					sdl2.SDL_Delay(500)
				else:
					w = int(progressBarWidth * (loadingThread.progress / 100.0))
					sdl2.sdlgfx.boxRGBA(renderer, progressBarX, progressBarY, progressBarX + w, progressBarY + progressBarHeight, self.lineColour.r, self.lineColour.g, self.lineColour.b, 255)
			else:
				sdl2.SDL_DestroyTexture(splashTexture)
				sdl2.sdlgfx.boxRGBA(renderer, 0, 0, self.__dimensions[0], self.__headerHeight, self.headerBackgroundColour.r, self.headerBackgroundColour.g, self.headerBackgroundColour.b, 255) # header bg
				sdl2.sdlgfx.rectangleRGBA(renderer, 0, self.__headerHeight, self.__dimensions[0], self.__dimensions[1], self.lineColour.r, self.lineColour.g, self.lineColour.b, 255) # header line
				sdl2.SDL_RenderCopy(renderer, headerTexture, None, sdl2.SDL_Rect(5, 0, headerTextureWidth, headerTextureHeight)) # header text
				
				self.__screens[self.__screenStack[-1]].draw()
			
				now = datetime.now()
			
				dateTexture = createText(renderer, self.headerFont, now.strftime("%H:%M:%S %d/%m/%Y"), self.textColour)
				(dateTextureWidth, dateTextureHeight) = getTextureDimensions(dateTexture)
				sdl2.sdlgfx.boxRGBA(renderer, self.__dimensions[0] - dateTextureWidth - 5, 0, self.__dimensions[0] - 5, dateTextureHeight, self.headerBackgroundColour.r, self.headerBackgroundColour.g, self.headerBackgroundColour.b, 255)
				sdl2.SDL_RenderCopy(renderer, dateTexture, None, sdl2.SDL_Rect(self.__dimensions[0] - dateTextureWidth - 5, 0, dateTextureWidth, dateTextureHeight))
			
			sdl2.SDL_RenderPresent(renderer)
		
		sdl2.SDL_DestroyTexture(headerTexture)
		sdl2.SDL_DestroyTexture(dateTexture)
		self.exit()
		
	def setScreen(self, screen):
		if not screen in self.__screens:
			logging.warning("PESApp.setScreen: invalid screen selection \"%s\"" % screen)
		else:
			logging.debug("PESApp.setScreen: setting current screen to \"%s\"" % screen)
			logging.debug("PESApp.setScreen: adding screen \"%s\" to screen stack" % screen)
			self.__screenStack.append(screen)
			self.__screens[screen].setMenuActive(True)
			self.__screens[screen].redraw = True
			
class PESLoadingThread(threading.Thread):
	def __init__(self):
		super(PESLoadingThread, self).__init__()
		self.progress = 0
		self.started = False
		self.done = False
		
	def run(self):
		self.started = True
		for i in range(0, 5):
			sleep(1)
			self.progress += 20
			logging.debug("PESLoadingThread.run: %d complete" % self.progress)
		self.done = True
		return

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
		self.redraw = True
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
		
		#if self.redraw:
		#logging.debug("Screen.draw: drawing menu and screen...")
		self.drawMenu()
		self.drawScreen()
		#	self.redraw = False
		
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
					self.redraw = True
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
					self.redraw = True
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
		self.redraw = True
	
class HomeScreen(Screen):
	
	def __init__(self, app, renderer, menuRect, screenRect):
		super(HomeScreen, self).__init__(app, renderer, "Home", Menu([MenuItem("Home")]), menuRect, screenRect)
		for c in self.app.consoles:
			self.menu.addItem(ConsoleMenuItem(c))
		self.menu.addItem(MenuItem("Settings", False, False, self.app.setScreen, "Settings"))
		self.menu.addItem(MenuItem("Reboot"))
		self.menu.addItem(MenuItem("Power Off"))
		self.menu.addItem(MenuItem("Exit", False, False, self.app.exit))
			
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
		self.__beginScan = False

	def drawScreen(self):
		super(SettingsScreen, self).drawScreen()
		#logging.debug("SettingsScreen.draw: drawing screen at (%d, %d) dimensions (%d, %d)" % (self.screenRect[0], self.screenRect[1], self.screenRect[2], self.screenRect[3]))
		
		currentX = self.screenRect[0] + self.screenMargin
		currentY = self.screenRect[1]
		
		if self.__init:
			(textWidth, textHeight) = renderText(self.renderer, self.app.titleFont, "Settings", self.app.textColour, currentX, currentY)
			#(textWidth, textHeight) = renderText(self.renderer, self.app.bodyFont, "Here you can scan for new games, set-up your joysticks as well as being able to reset PES to its default settings.", self.app.textColour, self.screenRect[0] + self.screenMargin, self.screenRect[1] + (textHeight * 2), self.wrap)
			renderLines(self.renderer, self.app.bodyFont, ["Here you can scan for new games, set-up your joysticks as well as being able to reset PES to its default settings.", " ", "Please select an item from the menu on the left."], self.app.textColour, currentX, currentY + textHeight + self.screenMargin, self.wrap)
			return
		
		selected = self.menu.getSelectedItem().getText()
		#logging.debug("SettingsScreen.drawScreen: selected \"%s\"" % selected)
		
		(textWidth, textHeight) = renderText(self.renderer, self.app.titleFont, selected, self.app.textColour, currentX, currentY)
		
		currentY += textHeight + self.screenMargin
		
		if selected == "Update Database":
			if not self.__beginScan:
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
			else:
				(textWidth, textHeight) = renderText(self.renderer, self.app.bodyFont, "Scan now in progress...", self.app.textColour, currentX , currentY, self.wrap)
				currentY += textHeight + 10
			
		elif selected == "Joystick Set-Up":
			pass
		elif selected == "Reset Database":
			pass
		elif selected == "Reset Config":
			pass
		elif selected == "About":
			renderLines(self.renderer, self.app.bodyFont, ['Pi Entertainment System version %s' % VERSION_NUMBER, ' ', 'Released: %s' % VERSION_DATE, ' ', 'License: Licensed under version 3 of the GNU Public License (GPL)', ' ', 'Author: %s' % VERSION_AUTHOR, ' ', 'Contributors: Eric Smith', ' ', 'Cover art: theGamesDB.net', ' ', 'Documentation: http://pes.mundayweb.com', ' ', 'Facebook: https://www.facebook.com/pientertainmentsystem', ' ', 'Help: pes@mundayweb.com'], self.app.textColour, currentX, currentY, self.wrap)
		
	def processEvent(self, event):
		oldMenuActive = self.menuActive # store state before parent method changes it!
		super(SettingsScreen, self).processEvent(event)
		selected = self.menu.getSelectedItem().getText()
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
				if event.key.keysym.sym == sdl2.SDLK_DOWN:
					logging.debug("SettingsScreen.processEvent: (Update Database) key event: DOWN")
					i = self.__updateDatabaseMenu.getSelectedIndex()
					total = self.__updateDatabaseMenu.getCount()
					if i + 1 > total - 1:
						self.__updateDatabaseMenu.setSelected(0)
					else:
						self.__updateDatabaseMenu.setSelected(i + 1)
					self.redraw = True
				elif event.key.keysym.sym == sdl2.SDLK_UP:
					logging.debug("SettingsScreen.processEvent: (Update Database) key event: UP")
					i = self.__updateDatabaseMenu.getSelectedIndex()
					total = self.__updateDatabaseMenu.getCount()
					if i - 1 < 0:
						self.__updateDatabaseMenu.setSelected(total - 1)
					else:
						self.__updateDatabaseMenu.setSelected(i - 1)
					self.redraw = True
				elif self.menuActive == oldMenuActive and event.key.keysym.sym == sdl2.SDLK_RETURN or event.key.keysym.sym == sdl2.SDLK_KP_ENTER:
					logging.debug("SettingsScreen.processEvent: (Update Database) key event: RETURN")
					m = self.__updateDatabaseMenu.getSelectedItem()
					if m.isToggable():
						m.toggle(not m.isToggled())
					elif m.getText() == "Begin Scan":
						self.__beginScan = True
					self.redraw = True