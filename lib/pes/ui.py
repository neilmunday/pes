#
#    This file is part of the Pi Entertainment System (PES).
#
#    PES provides an interactive GUI for games console emulators
#    and is designed to work on the Raspberry Pi.
#
#    Copyright (C) 2014-2021 Neil Munday (neil@mundayweb.com)
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
from collections import deque
from PIL import Image
import logging
import sdl2
import sdl2.sdlimage
import sdl2.joystick
import sdl2.video
import sdl2.render
import sdl2.sdlgfx
import sdl2.sdlttf
import sdl2.timer

def getTextureDimensions(texture):
	flags = c_uint32()
	access = c_int()
	w = c_int()
	h = c_int()
	ret = sdl2.SDL_QueryTexture(texture, byref(flags), byref(access), byref(w), byref(h))
	return (w.value, h.value)

class Menu(object):

	# listen events
	LISTEN_ITEM_ADDED = 1
	LISTEN_ITEM_REMOVED = 2
	LISTEN_ITEM_SELECTED = 3
	LISTEN_ITEM_INSERTED = 4
	LISTEN_ITEM_TOGGLED = 5

	def __init__(self, items, canToggleAll=True):
		super(Menu, self).__init__()
		self.__selected = 0
		self.__items = items
		self.__canToggleAll = canToggleAll
		self.__listeners = []
		logging.debug("Menu.init: Menu initialised")

	def addItem(self, item):
		self.__items.append(item)
		self.__fireListenEvent(Menu.LISTEN_ITEM_ADDED, item)

	def addListener(self, l):
		if l not in self.__listeners:
			self.__listeners.append(l)

	def __fireListenEvent(self, eventType, item):
		for l in self.__listeners:
			l.processMenuEvent(self, eventType, item)

	def getItem(self, i):
		maxIndex = len(self.__items) - 1
		if i < 0 or i > maxIndex:
			raise IndexError("Menu.getItem: List index %d out of range, max: %d" % (i, maxIndex))
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

	def getToggledCount(self):
		toggled = 0
		for i in self.__items:
			if i.isToggled():
				toggled += 1
		return toggled

	def insertItem(self, i, item):
		self.__items.insert(i, item)
		self.__fireListenEvent(Menu.LISTEN_ITEM_INSERTED, item)

	def removeItem(self, item):
		self.__items.remove(item)
		self.__fireListenEvent(Menu.LISTEN_ITEM_REMOVED, item)

	def removeListener(self, l):
		if l in self.__listeners:
			self.__listeners.remove(l)

	def setSelected(self, i, deselectAll=False, fireEvent=True):
		if i >= 0 and i < len(self.__items):
			if deselectAll:
				for m in self.__items:
					m.setSelected(False)
			else:
				self.__items[self.__selected].setSelected(False)
			self.__selected = i
			self.__items[self.__selected].setSelected(True)
			if fireEvent:
				self.__fireListenEvent(Menu.LISTEN_ITEM_SELECTED, self.__items[self.__selected])
			return
		raise ValueError("Menu.setSelected: invalid value for i: %s" % i)

	def sort(self):
		self.__items = sorted(self.__items, key=lambda item: item.getText())

	def toggleAll(self, toggle):
		if self.__canToggleAll or (not self.__canToggleAll and not toggle):
			for i in self.__items:
				if i.isToggable():
					i.toggle(toggle)
					self.__fireListenEvent(Menu.LISTEN_ITEM_TOGGLED, i)
		else:
			raise Exception("Menu.toggleAll: cannot toggle all when canToggleAll is False!")

	def toggle(self, i, t):
		if i >= 0 and i < len(self.__items):
			if not self.__canToggleAll:
				self.toggleAll(False)
			if self.__items[i].isToggable():
				self.__items[i].toggle(t)
				self.__fireListenEvent(Menu.LISTEN_ITEM_TOGGLED, self.__items[i])
			return
		raise ValueError("Menu.toggle: invalid value for i: %s" % i)

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

class AchievementGameMenuItem(MenuItem):

	def __init__(self, game, callback=None, *callbackArgs):
		super(AchievementGameMenuItem, self).__init__("%s (%s) %dpts %.1f%%" % (game.getName(), game.getConsoleName(), game.getUserPointsTotal(), game.getPercentComplete()), False, False, callback, *callbackArgs)

	def __repr__(self):
		return "<AchievementGameMenuItem>"

class ConsoleMenuItem(MenuItem):

	def __init__(self, console, selected = False, toggable = False, callback = None, *callbackArgs):
		super(ConsoleMenuItem, self).__init__(console.getName(), selected, toggable, callback, *callbackArgs)
		self.__console = console

	def getConsole(self):
		return self.__console

	def __repr__(self):
		return "<ConsoleMenuItem: text: %s >" % self.__console.getName()

class DataMenuItem(MenuItem):

	def __init__(self, dataObj, selected = False, toggable = False, callback = None, *callbackArgs):
		super(DataMenuItem, self).__init__(dataObj.getTitle(), selected, toggable, callback, *callbackArgs)
		self.__dataObj = dataObj

	def getDataObject(self):
		return self.__dataObj

	def __repr__(self):
		return "<DataMenuItem: text: %s >" % self.__dataObj.getTitle()

class GameMenuItem(MenuItem):

	def __init__(self, game, selected = False, toggable = False, callback = None, *callbackArgs):
		super(GameMenuItem, self).__init__(game.getName(), selected, toggable, callback, *callbackArgs)
		self.__game = game

	def getGame(self):
		return self.__game

	def toggle(self, t):
		super(GameMenuItem, self).toggle(t)
		self.__game.setFavourite(t)

	def isToggled(self):
		return self.__game.isFavourite()

	def __repr__(self):
		return "<GameMenuItem: text: %s >" % self.__game.getName()

class UIObject(object):

	def __init__(self, renderer, x, y, width, height):
		self.renderer = renderer
		self.x = x
		self.y = y
		self.width = width
		self.height = height
		self.visible = True
		self.__focus = False
		self.__borderColour = None
		self.__drawBorder = False

	def destroy(self):
		pass

	def draw(self):
		if self.visible and self.__drawBorder:
			drawBorder()

	def drawBorder(self):
		sdl2.sdlgfx.rectangleRGBA(self.renderer, self.x, self.y, self.x + self.width, self.y + self.height, self.__borderColour.r, self.__borderColour.g, self.__borderColour.b, 255)

	def hasBorder(self):
		return self.__drawBorder

	def hasFocus(self):
		return self.__focus

	def isVisible(self):
		return self.visible

	def setAlpha(self, alpha):
		if alpha < 0 or alpha > 255:
			raise ValueError("Invalid alpha value!")
		self.alpha = alpha

	def setBorderColour(self, colour):
		# crap hack as the PySDL2 authors have overridden the __ne__ operator for colours and can't handle None
		self.__borderColour = colour
		try:
			if self.__borderColour != None:
				self.__drawBorder = True
			self.__drawBorder = False
		except AttributeError:
			self.__drawBorder = True

	def setCoords(self, x, y):
		self.x = x
		self.y = y

	def setFocus(self, focus):
		self.__focus = focus

	def setSize(self, w, h):
		self.width = w
		self.height = h

	def setVisible(self, visible):
		self.visible = visible

class IconPanel(UIObject):

	def __init__(self, renderer, x, y, width, font, smallFont, colour, bgColour, selectedBgColour, title, description, icon, dataObj):
		self.__margin = 5
		self.__iconGap = 10
		self.__title = title
		self.__description = description
		labelWidth = width - (self.__margin * 2)
		self.__titleLabel = Label(renderer, x + self.__margin, y, self.__title, font, colour, fixedWidth=labelWidth)
		height = self.__titleLabel.height
		self.__bgColour = bgColour
		self.__icon = Icon(renderer, x + self.__margin, self.__titleLabel.y + self.__titleLabel.height, 64, 64, icon)
		height = self.__titleLabel.height + self.__icon.height + self.__margin
		super(IconPanel, self).__init__(renderer, x, y, width, height)
		labelWidth = width - (self.__margin + self.__icon.width + self.__iconGap)
		labelHeight = height - (self.__icon.y)
		self.__descriptionLabel = Label(renderer, self.__icon.x + self.__icon.width + self.__iconGap, self.__icon.y, self.__description, smallFont, colour, fixedWidth=labelWidth, fixedHeight=labelHeight)
		self.__dataObj = dataObj

	def destroy(self):
		logging.debug("IconPanel.destroy: destroying icon panel: \"%s\"" % self.__title)
		self.__titleLabel.destroy()
		self.__icon.destroy()
		self.__descriptionLabel.destroy()

	def draw(self):
		if self.visible:
			if self.__bgColour:
				sdl2.sdlgfx.boxRGBA(self.renderer, self.x, self.y, self.x + self.width, self.y + self.height, self.__bgColour.r, self.__bgColour.g, self.__bgColour.b, 255)
			self.__titleLabel.draw()
			self.__descriptionLabel.draw()
			self.__icon.draw()
			if self.hasBorder():
				self.drawBorder()

	def setCoords(self, x, y):
		super(IconPanel, self).setCoords(x, y)
		self.__titleLabel.setCoords(self.x + self.__margin, y)
		if self.__icon:
			self.__icon.setCoords(self.x + self.__margin, self.__titleLabel.y + self.__titleLabel.height)
			self.__descriptionLabel.setCoords(self.__icon.x + self.__icon.width + self.__iconGap, self.__icon.y)

	def getDataObject(self):
		return self.__dataObj

	def setDataObject(self, obj):
		self.__dataObj = obj

	def setDescription(self, txt):
		self.__descriptionLabel.setText(txt, True)

	def setIcon(self, icon):
		self.__icon.setImage(icon)

	#def setSize(self, w, h):
	#	super(IconPanel, self).setSize(w, h)

	def setTitle(self, txt):
		self.__titleLabel.setText(txt, True)

class BadgePanel(IconPanel):

	def __init__(self, renderer, x, y, width, font, smallFont, colour, bgColour, selectedBgColour, badge):
		super(BadgePanel, self).__init__(renderer, x, y, width, font, smallFont, colour, bgColour, selectedBgColour, badge.getTitle(), self.__createDescription(badge), badge.getPath(), badge)

	def __createDescription(self, badge):
		dateEarned = badge.getDateEarned(fmt="%d/%m/%Y")
		if dateEarned == None:
			dateEarned = "N/A"
		dateEarnedHardcore = badge.getDateEarned(hardcore=True, fmt="%d/%m/%Y")
		if dateEarnedHardcore == None:
			dateEarnedHardcore = "N/A"
		return "%s\nPoints: %d\nEarned: %s     Earned Hardcore: %s" % (badge.getDescription(), badge.getPoints(), dateEarned, dateEarnedHardcore)

	def setDataObject(self, badge):
		super(BadgePanel, self).setDataObject(badge)
		self.setTitle(badge.getTitle())
		self.setDescription(self.__createDescription(badge))
		self.setIcon(badge.getPath())

#class GameAchievementPanel(IconPanel):

#	def __init__(self, renderer, x, y, width, font, smallFont, colour, bgColour, selectedBgColour, game):
#		super(BadgePanel, self).__init__(renderer, x, y, width, font, smallFont, colour, bgColour, selectedBgColour, badge.getTitle(), self.__createDescription(badge), badge.getPath(), badge)

class Button(UIObject):

	def __init__(self, renderer, x, y, width, height, text, font, colour, selectedBgColour, callback = None, *callbackArgs):
		super(Button, self).__init__(renderer, x, y, width, height)
		txtWidth = c_int()
		txtHeight = c_int()
		sdl2.sdlttf.TTF_SizeText(font, text, txtWidth, txtHeight)
		self.__labelWidth = txtWidth.value
		if self.__labelWidth > width:
			self.__labelWidth = width
		self.__labelHeight = txtHeight.value
		self.__labelX = self.x + int((self.width - self.__labelWidth) / 2)
		self.__labelY = self.y + int((self.height - self.__labelHeight) / 2)
		self.__colour = colour
		self.__selectedBgColour = selectedBgColour
		self.__texture = None
		self.__font = font
		self.__text = text
		self.__callback = callback
		self.__callbackArgs = callbackArgs

	def destroy(self):
		logging.debug("Button.destroy: destroying button \"%s\"" % self.__text)
		if self.__texture:
			sdl2.SDL_DestroyTexture(self.__texture)
			self.__texture = None

	def draw(self):
		if self.visible:
			if self.__texture == None:
				surface = sdl2.sdlttf.TTF_RenderText_Blended(self.__font, self.__text, self.__colour)
				self.__texture = sdl2.SDL_CreateTextureFromSurface(self.renderer, surface)
				sdl2.SDL_FreeSurface(surface)
			if self.hasFocus():
				sdl2.sdlgfx.boxRGBA(self.renderer, self.x, self.y, self.x + self.width, self.y + self.height, self.__selectedBgColour.r, self.__selectedBgColour.g, self.__selectedBgColour.b, 255)
			else:
				sdl2.sdlgfx.rectangleRGBA(self.renderer, self.x, self.y, self.x + self.width, self.y + self.height, self.__selectedBgColour.r, self.__selectedBgColour.g, self.__selectedBgColour.b, 255)
			sdl2.SDL_RenderCopy(self.renderer, self.__texture, sdl2.SDL_Rect(0, 0, self.__labelWidth, self.__labelHeight), sdl2.SDL_Rect(self.__labelX, self.__labelY, self.__labelWidth, self.__labelHeight))

	def processEvent(self, event):
		if self.visible and self.hasFocus():
			if event.type == sdl2.SDL_KEYDOWN and (event.key.keysym.sym == sdl2.SDLK_RETURN or event.key.keysym.sym == sdl2.SDLK_KP_ENTER):
				if self.__callback:
					logging.debug("Button.processEvent: calling callback for button \"%s\"" % self.__text)
					if self.__callbackArgs:
						self.__callback(*self.__callbackArgs)
					else:
						self.__callback()
				else:
					logging.debug("Button.processEvent: no callback for button \"%s\"" % self.__text)

class Icon(UIObject):

	CACHE_LEN = 200
	__cache = {} # shared texture cache
	__queue = deque()

	def __init__(self, renderer, x, y, width, height, image, useCache=True):
		super(Icon, self).__init__(renderer, x, y, width, height)
		self.__image = image
		self.__texture = None
		self.__useCache = useCache
		logging.debug("Icon.init: initialised for \"%s\", using cache: %s" % (self.__image, self.__useCache))

	@staticmethod
	def __addToCache(path, texture):
		Icon.__cache[path] = texture
		Icon.__queue.append(path)
		cacheLength = len(Icon.__queue)
		if cacheLength > Icon.CACHE_LEN:
			logging.debug("Icon.__addToCache: cache length %d exceeded, removing item from cache to make room..." % Icon.CACHE_LEN)
			path = Icon.__queue.popleft()
			sdl2.SDL_DestroyTexture(Icon.__cache[path])
			del Icon.__cache[path]
		else:
			logging.debug("Icon.__addToCache: cache length: %d" % cacheLength)

	def destroy(self):
		if not self.__useCache and self.__texture:
			logging.debug("Icon.destroy: destroying texture for %s" % self.__image)
			sdl2.SDL_DestroyTexture(self.__texture)
			self.__texture = None

	@staticmethod
	def destroyTextures():
		logging.debug("Icon.destroyTextures: purging %d textures..." % len(Icon.__cache))
		keys = []
		for key, value in Icon.__cache.iteritems():
			sdl2.SDL_DestroyTexture(value)
			keys.append(key)
		for k in keys:
			del Icon.__cache[k]
		Icon.__queue.clear()

	def draw(self):
		if self.visible:
			if self.__useCache:
				if self.__image not in Icon.__cache:
					logging.debug("Icon.draw: loading texture for %s (using cache)" % self.__image)
					self.__addToCache(self.__image, sdl2.sdlimage.IMG_LoadTexture(self.renderer, self.__image))
				texture = Icon.__cache[self.__image]
			else:
				if self.__texture == None:
					logging.debug("Icon.draw: loading texture for %s (no cache)" % self.__image)
					self.__texture = sdl2.sdlimage.IMG_LoadTexture(self.renderer, self.__image)
				texture = self.__texture
			sdl2.SDL_RenderCopy(self.renderer, texture, None, sdl2.SDL_Rect(self.x, self.y, self.width, self.height))

	def setImage(self, image):
		self.__image = image

class Label(UIObject):

	def __init__(self, renderer, x, y, text, font, colour, bgColour=None, fixedWidth=0, fixedHeight=0, autoScroll=False, bgAlpha=255, pack=False):
		self.__text = text
		self.__colour = colour
		self.__font = font
		if fixedWidth == 0: # no wrap
			self.__surface = sdl2.sdlttf.TTF_RenderText_Blended(self.__font, self.__text, self.__colour)
			width = self.__surface.contents.w
		else:
			self.__surface = sdl2.sdlttf.TTF_RenderText_Blended_Wrapped(self.__font, self.__text, self.__colour, fixedWidth)
			if pack:
				s = sdl2.sdlttf.TTF_RenderText_Blended(self.__font, self.__text, self.__colour)
				if s.contents.w < self.__surface.contents.w:
					sdl2.SDL_FreeSurface(self.__surface)
					self.__surface = s
				width = self.__surface.contents.w
			else:
				width = fixedWidth
		self.__fixedWidth = fixedWidth
		self.__textWidth = self.__surface.contents.w
		self.__textHeight = self.__surface.contents.h
		if fixedHeight > 0:
			height = fixedHeight
		else:
			height = self.__textHeight
		super(Label, self).__init__(renderer, x, y, width, height)
		self.__texture = None
		self.__drawBackground = False
		self.__autoScroll = autoScroll
		self.__scrollY = 0
		self.__scrollTick = 0
		self.__firstDraw = True
		self.__bgAlpha = bgAlpha
		self.setBackgroundColour(bgColour)

	def destroy(self):
		logging.debug("Label.destroy: destroying label \"%s\"" % self.__text)
		self.setVisible(False)
		if self.__surface != None:
			sdl2.SDL_FreeSurface(self.__surface)
			self.__surface = None
		if self.__texture:
			sdl2.SDL_DestroyTexture(self.__texture)
			self.__texture = None

	def draw(self):
		if self.visible:
			super(Label, self).draw()
			if self.__drawBackground:
				sdl2.sdlgfx.boxRGBA(self.renderer, self.x, self.y, self.x + self.width, self.y + self.height, self.__bgColour.r, self.__bgColour.g, self.__bgColour.b, self.__bgAlpha)
			if self.__texture == None and self.__surface != None:
					self.__texture = sdl2.SDL_CreateTextureFromSurface(self.renderer, self.__surface)
					sdl2.SDL_FreeSurface(self.__surface)
					self.__surface = None
			if self.__textWidth < self.width:
				w = self.__textWidth
			else:
				w = self.width
			if self.__textHeight < self.height:
				h = self.__textHeight
			else:
				h = self.height
			if self.__autoScroll and self.__textHeight > self.height:
				tick = sdl2.timer.SDL_GetTicks()
				if self.__firstDraw:
					self.__scrollTick = tick
					self.__firstDraw = False
				if self.__scrollY == 0:
					if tick - self.__scrollTick > 2000:
						self.__scrollTick = tick
						self.__scrollY += 1
				elif tick - self.__scrollTick > 75:
					self.__scrollTick = tick
					self.__scrollY += 1
				if self.__scrollY > self.__textHeight - self.height:
					self.__scrollY = 0
			sdl2.SDL_RenderCopy(self.renderer, self.__texture, sdl2.SDL_Rect(0, self.__scrollY, w, h), sdl2.SDL_Rect(self.x, self.y, w, h))

	def getText(self):
		return self.__text

	def setAlpha(self, alpha):
		super(Label, self).setAlpha(alpha)
		if self.__texture:
			sdl2.SDL_SetTextureAlphaMod(self.__texture, alpha)

	def setBackgroundColour(self, colour):
		# crap hack as the PySDL2 authors have overridden the __ne__ operator for colours and can't handle None
		self.__bgColour = colour
		try:
			if self.__bgColour != None:
				self.__drawBackground = True
			self.__drawBackground = False
		except AttributeError:
			self.__drawBackground = True

	def setColour(self, colour):
		self.__colour = colour
		if self.__texture:
			sdl2.SDL_DestroyTexture(self.__texture)
			surface = sdl2.sdlttf.TTF_RenderText_Blended_Wrapped(self.__font, self.__text, self.__colour, self.width)
			self.__texture = sdl2.SDL_CreateTextureFromSurface(self.renderer, surface)
			sdl2.SDL_FreeSurface(surface)

	def setText(self, text, pack=False):
		if text == self.__text:
			return False
		if text == None or text == "":
			self.__text = " "
		else:
			self.__text = text
		self.__scrollY = 0
		self.__firstDraw = True
		sdl2.SDL_DestroyTexture(self.__texture)
		if self.__fixedWidth == 0:
			surface = sdl2.sdlttf.TTF_RenderText_Blended(self.__font, self.__text, self.__colour)
			self.width = surface.contents.w
		else:
			surface = sdl2.sdlttf.TTF_RenderText_Blended_Wrapped(self.__font, self.__text, self.__colour, self.width)
		self.__textWidth = surface.contents.w
		self.__textHeight = surface.contents.h
		self.__texture = sdl2.SDL_CreateTextureFromSurface(self.renderer, surface)
		sdl2.SDL_FreeSurface(surface)
		if pack:
			self.height = self.__textHeight
		return True

class List(UIObject):

	# listen events
	LISTEN_ITEM_ADDED = 1
	LISTEN_ITEM_REMOVED = 2
	LISTEN_ITEM_SELECTED = 3
	LISTEN_ITEM_INSERTED = 4
	LISTEN_ITEM_TOGGLED = 5

	SCROLLBAR_AUTO = 1
	SCROLLBAR_DISABLED = 2
	SCROLLBAR_ENABLED = 3

	def __init__(self, renderer, x, y, width, height, menu, font, colour, selectedColour, selectedBgColour, selectedBgColourNoFocus, showScrollbarPref=1, drawBackground=False, allowSelectAll=True, labelMargin=12, graphicalToggle=True):
		super(List, self).__init__(renderer,x, y, width, height)
		self.__drawBackground = drawBackground
		self.__graphicalToggle = graphicalToggle
		self.__menu = None
		self.__font = font
		self.__colour = colour
		self.__selectedColour = selectedColour
		self.__selectedBgColour = selectedBgColour
		self.__selectedBgColourNoFocus = selectedBgColourNoFocus
		self.__fontHeight = sdl2.sdlttf.TTF_FontHeight(self.__font)
		self.__labels = None
		self.__showScrollbarPref = showScrollbarPref
		self.__allowSelectAll = allowSelectAll
		self.__labelMargin = labelMargin
		self.setMenu(menu)
		self.__toggleRad = 3
		self.__toggleCenterY = self.__fontHeight / 2
		self.__listeners = []
		logging.debug("List.init: created List with %d labels for %d menu items, width: %d, height: %d" % (len(self.__labels), self.__menuCount, self.width, self.height))

	def addListener(self, l):
		if l not in self.__listeners:
			self.__listeners.append(l)

	def destroy(self):
		self.__menu.removeListener(self)
		logging.debug("List.destroy: destroying %d labels..." % len(self.__labels))
		for l in self.__labels:
			l.destroy()

	def draw(self):
		if self.visible:
			super(List, self).draw()
			i = self.__firstMenuItem
			for l in self.__labels:
				m = self.__menu.getItem(i)
				if m.isToggable():
					if self.__graphicalToggle:
						l.draw()
						if m.isToggled():
							sdl2.sdlgfx.filledCircleRGBA(self.renderer, l.x - 7, self.__toggleCenterY + l.y, self.__toggleRad, self.__colour.r, self.__colour.g, self.__colour.b, 255)
					else:
						if m.isToggled():
							l.setText("%s: On" % m.getText())
						else:
							l.setText("%s: Off" % m.getText())
						l.draw()
				else:
						l.draw()


				#l.draw()
				#if self.__menu.getItem(i).isToggled():
				#	sdl2.sdlgfx.filledCircleRGBA(self.renderer, l.x - 7, self.__toggleCenterY + l.y, self.__toggleRad, self.__colour.r, self.__colour.g, self.__colour.b, 255)

				i += 1
			if self.__drawBackground:
				sdl2.sdlgfx.boxRGBA(self.renderer, self.x, self.y, self.x + self.width, self.y + self.height, self.__selectedBgColourNoFocus.r, self.__selectedBgColourNoFocus.g, self.__selectedBgColourNoFocus.b, 50)
			if self.__showScrollbar:
				sdl2.sdlgfx.boxRGBA(self.renderer, self.__sliderX, self.__sliderY, self.__sliderX + self.__sliderWidth, self.__sliderY + self.__sliderHeight, self.__selectedColour.r, self.__selectedColour.g, self.__selectedColour.b, 50)

	def __fireListenEvent(self, eventType, item):
		for l in self.__listeners:
			l.processListEvent(self, eventType, item)

	def getMenu(self):
		return self.__menu

	def processEvent(self, event):
		if self.visible and self.hasFocus():
			if event.type == sdl2.SDL_KEYUP:
				if event.key.keysym.sym == sdl2.SDLK_DOWN or event.key.keysym.sym == sdl2.SDLK_UP:
					self.__fireListenEvent(List.LISTEN_ITEM_SELECTED, self.__menu.getSelectedItem())
			elif event.type == sdl2.SDL_KEYDOWN:
				if event.key.keysym.sym == sdl2.SDLK_DOWN:
					#logging.debug("List.processEvent: key event: DOWN")
					menuIndex = self.__menu.getSelectedIndex()
					self.__labels[self.__labelIndex].setBackgroundColour(None)
					self.__labels[self.__labelIndex].setColour(self.__colour)
					#print "menuIndex: %d, labelIndex: %d, visibleMenuItems: %d, menuCount: %d" % (menuIndex, self.__labelIndex, self.__visibleMenuItems, self.__menuCount)
					if self.__labelIndex + 1 > self.__visibleMenuItems - 1:
						if menuIndex + 1 > self.__menuCount - 1:
							self.__firstMenuItem = 0
							self.__labelIndex = 0
							menuIndex = 0
							if self.__menuCount > self.__visibleMenuItems:
								for i in xrange(self.__visibleMenuItems):
									self.__labels[i].setText(self.__menu.getItem(i + self.__firstMenuItem).getText())
						else:
							self.__firstMenuItem += 1
							menuIndex += 1
							if self.__menuCount > self.__visibleMenuItems:
								labelY = self.y
								lbl = self.__labels.popleft()
								lbl.setText(self.__menu.getItem(self.__firstMenuItem - 1 + self.__visibleMenuItems).getText())
								self.__labels.append(lbl)
								for l in self.__labels:
									l.y = labelY
									labelY += self.__fontHeight
					else:
						self.__labelIndex += 1
						menuIndex += 1
					self.__labels[self.__labelIndex].setBackgroundColour(self.__selectedBgColour)
					self.__labels[self.__labelIndex].setColour(self.__selectedColour)
					self.__menu.setSelected(menuIndex, fireEvent=False)
					if self.__showScrollbar:
						self.__updateScrollbar()
				elif event.key.keysym.sym == sdl2.SDLK_UP:
					#logging.debug("List.processEvent: key event: UP")
					menuIndex = self.__menu.getSelectedIndex()
					self.__labels[self.__labelIndex].setBackgroundColour(None)
					self.__labels[self.__labelIndex].setColour(self.__colour)
					if self.__labelIndex - 1 < 0:
						if menuIndex - 1 < 0:
							self.__firstMenuItem = self.__menuCount - self.__visibleMenuItems
							self.__labelIndex = self.__visibleMenuItems - 1
							menuIndex = self.__menuCount - 1
							if self.__menuCount > self.__visibleMenuItems:
								for i in xrange(self.__visibleMenuItems):
									self.__labels[i].setText(self.__menu.getItem(i + self.__firstMenuItem).getText())
						else:
							self.__firstMenuItem -= 1
							menuIndex -= 1
							if self.__menuCount > self.__visibleMenuItems:
								labelY = self.y
								lbl = self.__labels.pop()
								lbl.setText(self.__menu.getItem(self.__firstMenuItem).getText())
								self.__labels.appendleft(lbl)
								for l in self.__labels:
									l.y = labelY
									labelY += self.__fontHeight
					else:
						self.__labelIndex -= 1
						menuIndex -= 1
					self.__labels[self.__labelIndex].setBackgroundColour(self.__selectedBgColour)
					self.__labels[self.__labelIndex].setColour(self.__selectedColour)
					self.__menu.setSelected(menuIndex, fireEvent=False)
					if self.__showScrollbar:
						self.__updateScrollbar()
				elif event.key.keysym.sym == sdl2.SDLK_RETURN or event.key.keysym.sym == sdl2.SDLK_KP_ENTER:
					logging.debug("List.processEvent: key event: RETURN")
					m = self.__menu.getSelectedItem()
					m.trigger()
				elif event.key.keysym.sym == sdl2.SDLK_s:
					self.__menu.toggle(self.__menu.getSelectedIndex(), not self.__menu.getSelectedItem().isToggled())
				#elif event.key.keysym.sym == sdl2.SDLK_PAGEDOWN and self.__allowSelectAll:
				#	self.__menu.toggleAll(False)
				#elif event.key.keysym.sym == sdl2.SDLK_PAGEUP and self.__allowSelectAll:
				#	self.__menu.toggleAll(True)
				elif event.key.keysym.sym == sdl2.SDLK_PAGEDOWN or event.key.keysym.sym == sdl2.SDLK_PAGEUP:
					menuIndex = self.__menu.getSelectedIndex()
					if event.key.keysym.sym == sdl2.SDLK_PAGEDOWN:
						if menuIndex + self.__visibleMenuItems < self.__menuCount:
							menuIndex = menuIndex + self.__visibleMenuItems
						else:
							menuIndex = 0
					else:
						if menuIndex - self.__visibleMenuItems >= 0:
							menuIndex = menuIndex - self.__visibleMenuItems
						else:
							menuIndex = self.__menuCount - self.__visibleMenuItems
					self.__menu.setSelected(menuIndex)

	def processMenuEvent(self, menu, eventType, item):
		if eventType == Menu.LISTEN_ITEM_ADDED:
			logging.debug("List.processMenuEvent: item added: %s" % item.getText())
			self.__menuCount = self.__menu.getCount()
			self.__visibleMenuItems = int(self.height / self.__fontHeight)
			if self.__visibleMenuItems > self.__menuCount:
				self.__visibleMenuItems = self.__menuCount
			else:
				if self.__showScrollbarPref == List.SCROLLBAR_AUTO or self.__showScrollbarPref == List.SCROLLBAR_ENABLED:
					self.__setupScrollbar()
			labelLen = len(self.__labels)
			if labelLen < self.__visibleMenuItems:
				self.__labels.append(Label(self.renderer, self.__labelX, (labelLen * self.__fontHeight) + self.y, item.getText(), self.__font, self.__colour, fixedWidth=self.__labelWidth, fixedHeight=self.__fontHeight))
				if self.__showScrollbar:
					self.__sliderHeight = int((float(self.__visibleMenuItems) / float(self.__menuCount)) * self.__scrollbarHeight)
			self.__fireListenEvent(List.LISTEN_ITEM_ADDED, item)
		elif eventType == Menu.LISTEN_ITEM_INSERTED:
			logging.debug("List.processMenuEvent: item inserted")
			self.__menuCount = self.__menu.getCount()
			self.__visibleMenuItems = int(self.height / self.__fontHeight)
			if self.__visibleMenuItems > self.__menuCount:
				self.__visibleMenuItems = self.__menuCount
			else:
				if self.__showScrollbarPref == List.SCROLLBAR_AUTO or self.__showScrollbarPref == List.SCROLLBAR_ENABLED:
					self.__setupScrollbar()
			labelLen = len(self.__labels)
			if labelLen < self.__visibleMenuItems:
				self.__labels.append(Label(self.renderer, self.__labelX, (labelLen * self.__fontHeight) + self.y, " ", self.__font, self.__colour, fixedWidth=self.__labelWidth, fixedHeight=self.__fontHeight))
				if self.__showScrollbar:
					self.__sliderHeight = int((float(self.__visibleMenuItems) / float(self.__menuCount)) * self.__scrollbarHeight)
			# update label text
			for i in xrange(self.__visibleMenuItems):
				self.__labels[i].setText(self.__menu.getItem(self.__firstMenuItem + i).getText())
			self.__fireListenEvent(List.LISTEN_ITEM_INSERTED, item)
		elif eventType == Menu.LISTEN_ITEM_SELECTED:
			logging.debug("List.processMenuEvent: item selected")
			self.__selectLabel(self.__menu.getSelectedIndex())
			self.__fireListenEvent(List.LISTEN_ITEM_SELECTED, item)
		elif eventType == Menu.LISTEN_ITEM_REMOVED:
			logging.debug("List.processMenuEvent: item removed")
			self.__menuCount = self.__menu.getCount()
			self.__visibleMenuItems = int(self.height / self.__fontHeight)
			if self.__visibleMenuItems > self.__menuCount:
				# get last label and destroy it
				l = self.__labels[-1]
				self.__labels.remove(l)
				l.destroy()
				self.__visibleMenuItems = self.__menuCount
			else:
				if self.__showScrollbarPref == List.SCROLLBAR_AUTO or self.__showScrollbarPref == List.SCROLLBAR_ENABLED:
					self.__setupScrollbar()
			# update label text
			self.__selectLabel(0)
			self.__fireListenEvent(List.LISTEN_ITEM_REMOVED, item)
		elif eventType == Menu.LISTEN_ITEM_TOGGLED:
			logging.debug("List.processMenuEvent: item toggled")
			self.__fireListenEvent(List.LISTEN_ITEM_TOGGLED, item)

	def removeListener(self, l):
		if l in self.__listeners:
			self.__listeners.remove(l)

	def __selectLabel(self, menuIndex):
		logging.debug("List.__selectLabel: selecting index %d (%s)" % (menuIndex, self.__menu.getItem(menuIndex).getText()))
		self.__labels[self.__labelIndex].setBackgroundColour(None)
		self.__labels[self.__labelIndex].setColour(self.__colour)
		if menuIndex < self.__visibleMenuItems:
			self.__labelIndex = menuIndex
			self.__firstMenuItem = 0
			if self.__menuCount > self.__visibleMenuItems:
				for i in xrange(self.__visibleMenuItems):
					self.__labels[i].setText(self.__menu.getItem(i + self.__firstMenuItem).getText())
		else:
			if self.__menuCount - menuIndex > self.__visibleMenuItems:
				self.__firstMenuItem = menuIndex
				self.__labelIndex = 0
				# shift labels
				for i in xrange(self.__visibleMenuItems):
					self.__labels[i].setText(self.__menu.getItem(i + self.__firstMenuItem).getText())
			else:
				self.__firstMenuItem = self.__menuCount - self.__visibleMenuItems
				self.__labelIndex = self.__visibleMenuItems - (self.__menuCount - menuIndex)
				# shift labels
				for i in xrange(self.__visibleMenuItems):
					self.__labels[i].setText(self.__menu.getItem(i + self.__firstMenuItem).getText())
		self.__labels[self.__labelIndex].setBackgroundColour(self.__selectedBgColour)
		self.__labels[self.__labelIndex].setColour(self.__selectedColour)
		self.__updateScrollbar()

	def setFocus(self, focus):
		color = None
		if focus:
			colour = self.__selectedBgColour
		else:
			colour = self.__selectedBgColourNoFocus
		self.__labels[self.__labelIndex].setBackgroundColour(colour)
		super(List, self).setFocus(focus)

	def setMenu(self, menu):
		if self.__menu:
			self.__menu.removeListener(self)
		self.__menu = menu
		self.__menuCount = self.__menu.getCount()
		self.__visibleMenuItems = int(self.height / self.__fontHeight)
		if self.__visibleMenuItems > self.__menuCount:
			self.__visibleMenuItems = self.__menuCount
		if self.__showScrollbarPref == List.SCROLLBAR_ENABLED or (self.__showScrollbarPref == List.SCROLLBAR_AUTO and self.__menuCount > self.__visibleMenuItems):
			self.__setupScrollbar()
		else:
			self.__labelX = self.x + self.__labelMargin
			self.__labelWidth = self.width - self.__labelMargin
			self.__showScrollbar = False
		if self.__labels:
			for l in self.__labels:
				l.destroy()
				del l
			self.__labels.clear()
		else:
			self.__labels = deque()
		self.__labels.append(Label(self.renderer, self.__labelX, self.y, self.__menu.getItem(0).getText(), self.__font, self.__selectedColour, self.__selectedBgColour, fixedWidth=self.__labelWidth, fixedHeight=self.__fontHeight))
		labelY = self.y + self.__fontHeight
		for i in xrange(1, self.__visibleMenuItems):
			self.__labels.append(Label(self.renderer, self.__labelX, labelY, self.__menu.getItem(i).getText(), self.__font, self.__colour, fixedWidth=self.__labelWidth, fixedHeight=self.__fontHeight))
			labelY += self.__fontHeight
		self.__firstMenuItem = 0
		self.__labelIndex = 0
		self.__menu.addListener(self)

	def __setupScrollbar(self):
		self.__scrollbarWidth = 20
		self.__scrollbarHeight = self.height
		self.__scrollbarX = self.x
		self.__scrollbarY = self.y
		self.__sliderGap = 2
		self.__labelX = self.__scrollbarX + self.__scrollbarWidth + self.__labelMargin
		self.__labelWidth = self.width - self.__scrollbarWidth - self.__labelMargin
		# work out slider height
		self.__sliderHeight = int((float(self.__visibleMenuItems) / float(self.__menuCount)) * self.__scrollbarHeight) - (self.__sliderGap * 2)
		self.__sliderX = self.__scrollbarX + 2
		self.__sliderWidth = self.__scrollbarWidth - (self.__sliderGap * 2)
		self.__showScrollbar = True
		self.__updateScrollbar()

	def __updateScrollbar(self):
		if self.__showScrollbar:
				self.__sliderY = int(((float(self.__menu.getSelectedIndex()) / float(self.__menuCount)) * float(self.__scrollbarHeight - self.__sliderHeight)) + self.__scrollbarY) + self.__sliderGap

class IconPanelList(UIObject):

	# listen events
	LISTEN_ITEM_ADDED = 1
	LISTEN_ITEM_REMOVED = 2
	LISTEN_ITEM_SELECTED = 3
	LISTEN_ITEM_INSERTED = 4
	LISTEN_ITEM_TOGGLED = 5

	SCROLLBAR_AUTO = 1
	SCROLLBAR_DISABLED = 2
	SCROLLBAR_ENABLED = 3

	def __init__(self, renderer, x, y, width, height, menu, font, smallFont, colour, selectedColour, bgColour, selectedBgColour, selectedBgColourNoFocus, showScrollbarPref=1, drawBackground=False, allowSelectAll=True, panelMargin=12):
		super(IconPanelList, self).__init__(renderer,x, y, width, height)
		self.__drawBackground = drawBackground
		self.__menu = None # DataMenuItems
		self.__font = font
		self.__smallFont = smallFont
		self.__colour = colour
		self.__selectedColour = selectedColour
		self.__selectedBgColourNoFocus = selectedBgColourNoFocus
		self.__bgColour = bgColour
		self.__selectedBgColour = selectedBgColour
		self.__fontHeight = sdl2.sdlttf.TTF_FontHeight(self.__font)
		self.__panels = None
		self.__showScrollbarPref = showScrollbarPref
		self.__allowSelectAll = allowSelectAll
		self.__panelMargin = panelMargin
		self.__panelGap = 10
		self.__listeners = []
		self.setMenu(menu)
		logging.debug("IconPanelList.init: created List with %d panels for %d menu items, width: %d, height: %d" % (len(self.__panels), self.__menuCount, self.width, self.height))

	def addListener(self, l):
		if l not in self.__listeners:
			self.__listeners.append(l)

	def destroy(self):
		self.__menu.removeListener(self)
		logging.debug("List.destroy: destroying %d panels..." % len(self.__panels))
		for p in self.__panels:
			p.destroy()

	def draw(self):
		if self.visible:
			super(IconPanelList, self).draw()
			i = self.__firstMenuItem
			for p in self.__panels:
				p.draw()
				i += 1
			if self.__drawBackground:
				sdl2.sdlgfx.boxRGBA(self.renderer, self.x, self.y, self.x + self.width, self.y + self.height, self.__selectedBgColourNoFocus.r, self.__selectedBgColourNoFocus.g, self.__selectedBgColourNoFocus.b, 50)
			if self.__showScrollbar:
				sdl2.sdlgfx.boxRGBA(self.renderer, self.__sliderX, self.__sliderY, self.__sliderX + self.__sliderWidth, self.__sliderY + self.__sliderHeight, self.__selectedColour.r, self.__selectedColour.g, self.__selectedColour.b, 50)

	def __fireListenEvent(self, eventType, item):
		for l in self.__listeners:
			l.processListEvent(self, eventType, item)

	def processEvent(self, event):
		if self.visible and self.hasFocus():
			if event.type == sdl2.SDL_KEYUP:
				if event.key.keysym.sym == sdl2.SDLK_DOWN or event.key.keysym.sym == sdl2.SDLK_UP:
					self.__fireListenEvent(List.LISTEN_ITEM_SELECTED, self.__menu.getSelectedItem())
			elif event.type == sdl2.SDL_KEYDOWN:
				if event.key.keysym.sym == sdl2.SDLK_DOWN:
					#logging.debug("List.processEvent: key event: DOWN")
					menuIndex = self.__menu.getSelectedIndex()
					self.__panels[self.__panelIndex].setBorderColour(None)
					#print "menuIndex: %d, labelIndex: %d, visibleMenuItems: %d, menuCount: %d" % (menuIndex, self.__panelIndex, self.__visibleMenuItems, self.__menuCount)
					if self.__panelIndex + 1 > self.__visibleMenuItems - 1:
						if menuIndex + 1 > self.__menuCount - 1:
							self.__firstMenuItem = 0
							self.__panelIndex = 0
							menuIndex = 0
							if self.__menuCount > self.__visibleMenuItems:
								for i in xrange(self.__visibleMenuItems):
									self.__panels[i].setDataObject(self.__menu.getItem(i + self.__firstMenuItem).getDataObject())
						else:
							self.__firstMenuItem += 1
							menuIndex += 1
							if self.__menuCount > self.__visibleMenuItems:
								panelY = self.y
								panel = self.__panels.popleft()
								panel.setDataObject(self.__menu.getItem(self.__firstMenuItem - 1 + self.__visibleMenuItems).getDataObject())
								self.__panels.append(panel)
								for p in self.__panels:
									p.setCoords(p.x, panelY)
									panelY += p.height + self.__panelGap
					else:
						self.__panelIndex += 1
						menuIndex += 1
					self.__panels[self.__panelIndex].setBorderColour(self.__selectedBgColour)
					self.__menu.setSelected(menuIndex, fireEvent=False)
					if self.__showScrollbar:
						self.__updateScrollbar()
				elif event.key.keysym.sym == sdl2.SDLK_UP:
					#logging.debug("List.processEvent: key event: UP")
					menuIndex = self.__menu.getSelectedIndex()
					self.__panels[self.__panelIndex].setBorderColour(None)
					if self.__panelIndex - 1 < 0:
						if menuIndex - 1 < 0:
							self.__firstMenuItem = self.__menuCount - self.__visibleMenuItems
							self.__panelIndex = self.__visibleMenuItems - 1
							menuIndex = self.__menuCount - 1
							if self.__menuCount > self.__visibleMenuItems:
								for i in xrange(self.__visibleMenuItems):
									self.__panels[i].setDataObject(self.__menu.getItem(i + self.__firstMenuItem).getDataObject())
						else:
							self.__firstMenuItem -= 1
							menuIndex -= 1
							if self.__menuCount > self.__visibleMenuItems:
								panelY = self.y
								panel = self.__panels.pop()
								panel.setDataObject(self.__menu.getItem(self.__firstMenuItem).getDataObject())
								self.__panels.appendleft(panel)
								for p in self.__panels:
									p.setCoords(p.x, panelY)
									panelY += p.height + self.__panelGap
					else:
						self.__panelIndex -= 1
						menuIndex -= 1
					self.__panels[self.__panelIndex].setBorderColour(self.__selectedBgColour)
					self.__menu.setSelected(menuIndex, fireEvent=False)
					if self.__showScrollbar:
						self.__updateScrollbar()
				elif event.key.keysym.sym == sdl2.SDLK_RETURN or event.key.keysym.sym == sdl2.SDLK_KP_ENTER:
					logging.debug("IconPanelList.processEvent: key event: RETURN")
					m = self.__menu.getSelectedItem()
					m.trigger()
				elif event.key.keysym.sym == sdl2.SDLK_s:
					self.__menu.toggle(self.__menu.getSelectedIndex(), not self.__menu.getSelectedItem().isToggled())
				#elif event.key.keysym.sym == sdl2.SDLK_PAGEDOWN and self.__allowSelectAll:
				#	self.__menu.toggleAll(False)
				#elif event.key.keysym.sym == sdl2.SDLK_PAGEUP and self.__allowSelectAll:
				#	self.__menu.toggleAll(True)
				elif event.key.keysym.sym == sdl2.SDLK_PAGEDOWN or event.key.keysym.sym == sdl2.SDLK_PAGEUP:
					menuIndex = self.__menu.getSelectedIndex()
					if event.key.keysym.sym == sdl2.SDLK_PAGEDOWN:
						if menuIndex + self.__visibleMenuItems < self.__menuCount:
							menuIndex = menuIndex + self.__visibleMenuItems
						else:
							menuIndex = 0
					else:
						if menuIndex - self.__visibleMenuItems >= 0:
							menuIndex = menuIndex - self.__visibleMenuItems
						else:
							menuIndex = self.__menuCount - self.__visibleMenuItems
					self.__menu.setSelected(menuIndex)

	def processMenuEvent(self, menu, eventType, item):
		if eventType == Menu.LISTEN_ITEM_ADDED:
			logging.debug("IconPanelList.processMenuEvent: item added: %s" % item.getText())
			self.__menuCount = self.__menu.getCount()
			self.__visibleMenuItems = int(self.height / self.__panels[0].height)
			if self.__visibleMenuItems > self.__menuCount:
				self.__visibleMenuItems = self.__menuCount
			else:
				if self.__showScrollbarPref == IconPanelList.SCROLLBAR_AUTO or self.__showScrollbarPref == IconPanelList.SCROLLBAR_ENABLED:
					self.__setupScrollbar()
			panelLen = len(self.__panels)
			if panelLen < self.__visibleMenuItems:
				self.__panels.append(BadgePanel(self.renderer, self.__panelX, self.__panels[-1].height + self.__panels[-1].y + self.__panelGap, self.width, self.__font, self.__smallFont, self.__colour, self.__bgColour, self.__selectedBgColour, item.getDataObject()))
				if self.__showScrollbar:
					self.__sliderHeight = int((float(self.__visibleMenuItems) / float(self.__menuCount)) * self.__scrollbarHeight)
			self.__fireListenEvent(IconPanelList.LISTEN_ITEM_ADDED, item)
		elif eventType == Menu.LISTEN_ITEM_INSERTED:
			logging.debug("IconPanelList.processMenuEvent: item inserted")
			self.__menuCount = self.__menu.getCount()
			self.__visibleMenuItems = int(self.height / self.__panels[0])
			if self.__visibleMenuItems > self.__menuCount:
				self.__visibleMenuItems = self.__menuCount
			else:
				if self.__showScrollbarPref == IconPanelList.SCROLLBAR_AUTO or self.__showScrollbarPref == IconPanelList.SCROLLBAR_ENABLED:
					self.__setupScrollbar()
			panelLen = len(self.__panels)
			if panelLen < self.__visibleMenuItems:
				self.__panels.append(BadgePanel(self.renderer, self.__panelX, self.__panels[-1].height + self.__panels[-1].y + self.__panelGap, self.width, self.__font, self.__smallFont, self.__colour, self.__bgColour, self.__selectedBgColour, item.getDataObject()))
				if self.__showScrollbar:
					self.__sliderHeight = int((float(self.__visibleMenuItems) / float(self.__menuCount)) * self.__scrollbarHeight)
			# update label text
			for i in xrange(self.__visibleMenuItems):
				self.__panels[i].setDataObject(self.__menu.getItem(self.__firstMenuItem + i).getDataObject())
			self.__fireListenEvent(IconPanelList.LISTEN_ITEM_INSERTED, item)
		elif eventType == Menu.LISTEN_ITEM_SELECTED:
			logging.debug("IconPanelList.processMenuEvent: item selected")
			self.__selectLabel(self.__menu.getSelectedIndex())
			self.__fireListenEvent(IconPanelList.LISTEN_ITEM_SELECTED, item)
		elif eventType == Menu.LISTEN_ITEM_TOGGLED:
			logging.debug("IconPanelList.processMenuEvent: item toggled")
			self.__fireListenEvent(IconPanelList.LISTEN_ITEM_TOGGLED, item)

	def removeListener(self, l):
		if l in self.__listeners:
			self.__listeners.remove(l)

	def __selectLabel(self, menuIndex):
		logging.debug("IconPanelList.__selectLabel: selecting index %d (%s)" % (menuIndex, self.__menu.getSelectedItem().getText()))
		self.__panels[self.__panelIndex].setBorderColour(None)
		if menuIndex < self.__visibleMenuItems:
			self.__panelIndex = menuIndex
			self.__firstMenuItem = 0
			if self.__menuCount > self.__visibleMenuItems:
				for i in xrange(self.__visibleMenuItems):
					self.__panels[i].setDataObject(self.__menu.getItem(i + self.__firstMenuItem).getDataObject())
		else:
			if self.__menuCount - menuIndex > self.__visibleMenuItems:
				self.__firstMenuItem = menuIndex
				self.__panelIndex = 0
				# shift panels
				for i in xrange(self.__visibleMenuItems):
					self.__panels[i].setDataObject(self.__menu.getItem(i + self.__firstMenuItem).getDataObject())
			else:
				self.__firstMenuItem = self.__menuCount - self.__visibleMenuItems
				self.__panelIndex = self.__visibleMenuItems - (self.__menuCount - menuIndex)
				# shift panels
				for i in xrange(self.__visibleMenuItems):
					self.__panels[i].setDataObject(self.__menu.getItem(i + self.__firstMenuItem).getDataObject())
		if self.hasFocus():
			self.__panels[self.__panelIndex].setBorderColour(self.__selectedBgColour)
		self.__updateScrollbar()

	def setFocus(self, focus):
		color = None
		if focus:
			colour = self.__selectedBgColour
			self.__panels[self.__panelIndex].setBorderColour(self.__selectedBgColour)
		else:
			colour = self.__selectedBgColourNoFocus
			self.__panels[self.__panelIndex].setBorderColour(None)
		super(IconPanelList, self).setFocus(focus)

	def setMenu(self, menu):
		if self.__menu:
			self.__menu.removeListener(self)
		self.__menu = menu
		self.__menuCount = self.__menu.getCount()
		if self.__panels:
			for p in self.__panels:
				p.destroy()
				del p
			self.__panels.clear()
		else:
			self.__panels = deque()
		p = BadgePanel(self.renderer, 0, self.y, self.width, self.__font, self.__smallFont, self.__colour, self.__bgColour, self.__selectedBgColour, self.__menu.getItem(0).getDataObject())

		self.__visibleMenuItems = int(self.height / p.height)
		if self.__visibleMenuItems > self.__menuCount:
			self.__visibleMenuItems = self.__menuCount
		if self.__showScrollbarPref == List.SCROLLBAR_ENABLED or (self.__showScrollbarPref == List.SCROLLBAR_AUTO and self.__menuCount > self.__visibleMenuItems):
			self.__setupScrollbar()
		else:
			self.__panelX = self.x + self.__panelMargin
			self.__panelWidth = self.width - self.__panelMargin
			self.__showScrollbar = False

		p.setCoords(self.__panelX, p.y)
		p.setSize(self.__panelWidth, p.height)
		self.__panels.append(p)
		panelY = self.y + p.height + self.__panelGap
		for i in xrange(1, self.__visibleMenuItems):
			p = BadgePanel(self.renderer, self.__panelX, panelY, self.__panelWidth, self.__font, self.__smallFont, self.__colour, self.__bgColour, self.__selectedBgColour, self.__menu.getItem(i).getDataObject())
			self.__panels.append(p)
			panelY += p.height + self.__panelGap
		self.__firstMenuItem = 0
		self.__panelIndex = 0
		self.__menu.addListener(self)
		self.__menu.setSelected(0, fireEvent=True)

	def __setupScrollbar(self):
		self.__scrollbarWidth = 20
		self.__scrollbarHeight = self.height
		self.__scrollbarX = self.x
		self.__scrollbarY = self.y
		self.__sliderGap = 2
		self.__panelX = self.__scrollbarX + self.__scrollbarWidth + self.__panelMargin
		self.__panelWidth = self.width - self.__scrollbarWidth - self.__panelMargin
		# work out slider height
		self.__sliderHeight = int((float(self.__visibleMenuItems) / float(self.__menuCount)) * self.__scrollbarHeight) - (self.__sliderGap * 2)
		self.__sliderX = self.__scrollbarX + 2
		self.__sliderWidth = self.__scrollbarWidth - (self.__sliderGap * 2)
		self.__showScrollbar = True
		self.__updateScrollbar()

	def __updateScrollbar(self):
		if self.__showScrollbar:
				self.__sliderY = int(((float(self.__menu.getSelectedIndex()) / float(self.__menuCount)) * float(self.__scrollbarHeight - self.__sliderHeight)) + self.__scrollbarY) + self.__sliderGap

class MessageBox(UIObject):

	def __init__(self, renderer, text, font, colour, bgColour, borderColour, callback, *callbackArgs):
		# renderer, x, y, text, font, colour, bgColour=None, fixedWidth=0, fixedHeight=0, autoScroll=False, bgAlpha=255):
		rendererWidth = c_int()
		rendererHeight = c_int()
		sdl2.SDL_RenderGetLogicalSize(renderer, byref(rendererWidth), byref(rendererHeight))
		if rendererWidth.value == 0 and rendererHeight.value == 0:
			logging.debug("MessageBox:__init__: renderer logical size not set")
			sdl2.SDL_GetRendererOutputSize(renderer, byref(rendererWidth), byref(rendererHeight))
		else:
			logging.debug("MessageBox:__init__: renderer logical size set to: %d x %d" % (rendererWidth.value, rendererHeight.value))
		self.__labelMargin = 20
		width = int(rendererWidth.value) - 100
		labelWidth = width - (self.__labelMargin * 2)
		self.__label = Label(renderer, 0, 0, text, font, colour, bgColour, fixedWidth=labelWidth, pack=True)
		labelWidth = self.__label.width # may have been resized by packing
		height = self.__label.height + (self.__labelMargin * 2)
		x = int((rendererWidth.value - width) / 2.0)
		y = int((rendererHeight.value - height) / 2.0)
		super(MessageBox, self).__init__(renderer, x, y, width, height)
		self.__borderColour = borderColour
		self.__bgColour = bgColour
		self.__label.setText(text, True)
		self.__label.setCoords(x + self.__labelMargin + ((width - labelWidth - (self.__labelMargin * 2)) / 2), y + self.__labelMargin)
		self.__rendererWidth = rendererWidth.value
		self.__rendererHeight = rendererHeight.value
		self.__callback = callback
		self.__callbackArgs = callbackArgs
		logging.debug("MessageBox.init: initialised")

	def destroy(self):
		logging.debug("MessageBox.destroy: destroying...")
		self.__label.destroy()

	def draw(self):
		if self.visible:
			sdl2.sdlgfx.boxRGBA(self.renderer, 0, 0, self.__rendererWidth, self.__rendererHeight, self.__bgColour.r, self.__bgColour.g, self.__bgColour.b, 200)
			sdl2.sdlgfx.boxRGBA(self.renderer, self.x, self.y, self.x + self.width, self.y + self.height, self.__bgColour.r, self.__bgColour.g, self.__bgColour.b, 255)
			self.__label.draw()
			sdl2.sdlgfx.rectangleRGBA(self.renderer, self.x, self.y, self.x + self.width, self.y + self.height, self.__borderColour.r, self.__borderColour.g, self.__borderColour.b, 255) # border

	def processEvent(self, event):
		if self.visible and event.type == sdl2.SDL_KEYDOWN and (event.key.keysym.sym == sdl2.SDLK_RETURN or event.key.keysym.sym == sdl2.SDLK_KP_ENTER):
			if self.__callback:
				logging.debug("MessageBox: calling callback...")
				if self.__callbackArgs:
					self.__callback(*self.__callbackArgs)
				self.__callback
			self.visible = False

class ProgressBar(UIObject):

	def __init__(self, renderer, x, y, width, height, colour, backgroundColour):
		super(ProgressBar, self).__init__(renderer, x, y, width, height)
		self.__progress = 0.0 # percent complete
		self.__colour = colour
		self.__backgroundColour = backgroundColour
		logging.debug("ProgressBar.init: initialised")

	def draw(self):
		if self.visible:
			margin = 3
			sdl2.sdlgfx.boxRGBA(self.renderer, self.x, self.y, self.x + self.width, self.y + self.height, self.__backgroundColour.r, self.__backgroundColour.g, self.__backgroundColour.b, 255)
			if self.__progress > 0:
				w = int(self.width * (self.__progress / 100.0))
				sdl2.sdlgfx.boxRGBA(self.renderer, self.x + margin, self.y + margin, self.x + w - margin, self.y + self.height - margin, self.__colour.r, self.__colour.g, self.__colour.b, 255)

	def setProgress(self, p):
		if p > 100:
			raise ValueError("%d is greater than 100" % p)
		if p < 0:
			raise ValueError("%d is less than 0" % p)
		self.__progress = p

class Thumbnail(UIObject):

	CACHE_LEN = 100
	__cache = {} # shared texture cache
	__queue = deque()

	def __init__(self, renderer, x, y, width, height, game, font, txtColour, drawLabel=True):
		self.__font = font
		self.__fontHeight = sdl2.sdlttf.TTF_FontHeight(self.__font)
		self.__thumbWidth = width
		self.__thumbHeight = height
		self.__labelHeight = self.__fontHeight * 2
		if drawLabel:
			height += 1 + self.__labelHeight # allow space for label
		super(Thumbnail, self).__init__(renderer, x, y, width, height)
		self.__txtColour = txtColour
		self.__game = game
		self.__gameId = game.getId()
		self.__coverart = game.getCoverArt()
		if self.__coverart == None:
			self.__coverart = game.getConsole().getNoCoverArtImg()
		self.__coverartTexture = None
		if drawLabel:
			self.__label = Label(self.renderer, self.x, self.y + self.__thumbHeight + 1, self.__game.getName(), self.__font, self.__txtColour, fixedWidth=self.width, fixedHeight=self.__labelHeight)
		else:
			self.__label = None
		logging.debug("Thumbnail.init: initialised for %s" % game.getName())

	@staticmethod
	def __addToCache(gameId, texture):
		Thumbnail.__cache[gameId] = texture
		Thumbnail.__queue.append(gameId)
		cacheLength = len(Thumbnail.__queue)
		if cacheLength > Thumbnail.CACHE_LEN:
			logging.debug("Thumbnail.__addToCache: cache length %d exceeded, removing item from cache to make room..." % Thumbnail.CACHE_LEN)
			gameId = Thumbnail.__queue.popleft()
			sdl2.SDL_DestroyTexture(Thumbnail.__cache[gameId])
			del Thumbnail.__cache[gameId]
		else:
			logging.debug("Thumbnail.__addToCache: cache length: %d" % cacheLength)

	def draw(self):
		if self.visible:
			super(Thumbnail, self).draw()
			self.loadTexture()
			sdl2.SDL_RenderCopy(self.renderer, self.__coverartTexture, None, sdl2.SDL_Rect(self.x, self.y, self.__thumbWidth, self.__thumbHeight))
			# render text underneath
			if self.__label:
				self.__label.draw()

	def destroy(self):
		if self.__label:
			self.__label.destroy()

	@staticmethod
	def destroyTextures():
		logging.debug("Thumbnail.destroyTextures: purging %d textures..." % len(Thumbnail.__cache))
		keys = []
		for key, value in Thumbnail.__cache.iteritems():
			sdl2.SDL_DestroyTexture(value)
			keys.append(key)
		for k in keys:
			del Thumbnail.__cache[k]
		Thumbnail.__queue.clear()

	def loadTexture(self):
		if self.__gameId not in Thumbnail.__cache:
			logging.debug("Thumbnail.draw: loading texture for %s" % self.__game.getName())
			self.__coverartTexture = sdl2.sdlimage.IMG_LoadTexture(self.renderer, self.__coverart)
			self.__addToCache(self.__gameId, self.__coverartTexture)
		else:
			self.__coverartTexture = Thumbnail.__cache[self.__gameId]

	def setCoords(self, x, y):
		super(Thumbnail, self).setCoords(x, y)
		self.__label.setCoords(self.x, self.y + self.__thumbHeight + 1)

	def setGame(self, game):
		if self.__gameId == game.getId():
			return
		if self.__label:
			self.__label.setText(game.getName())
		self.__game = game
		self.__gameId = game.getId()
		self.__coverart = game.getCoverArt()
		if self.__coverart == None:
			self.__coverart = game.getConsole().getNoCoverArtImg()
		self.__coverartTexture = None

class ThumbnailPanel(UIObject):

	def __init__(self, renderer, x, y, width, games, font, txtColour, selectedColour, gap=10, drawLabels=True, maxThumbs=0):
		super(ThumbnailPanel, self).__init__(renderer, x, y, width, 1) # height is overridden later
		self.__gap = gap
		self.__thumbnails = []
		self.__font = font
		self.__txtColour = txtColour
		self.__selectedColour = selectedColour
		self.__drawLabels = drawLabels
		self.__maxThumbs = maxThumbs
		self.setGames(games)

	def draw(self):
		if self.visible:
			for t in self.__thumbnails:
				t.draw()

	def destroy(self):
		logging.debug("ThumbnailPanel.destroy: destroying...")
		for t in self.__thumbnails:
			t.destroy()

	def loadTextures(self):
		logging.debug("ThumbnailPanel.loadTextures: loading %d textures..."  % len(self.__thumbnails))
		for t in self.__thumbnails:
			t.loadTexture()

	def setCoords(self, x, y):
		super(ThumbnailPanel, self).setCoords(x, y)
		currentX = self.x
		for t in self.__thumbnails:
			t.setCoords(currentX, self.y)
			currentX += self.__thumbWidth + self.__gap

	def setGames(self, games):
		self.__games = games
		if self.__maxThumbs > 0:
			maxThumbs = self.__maxThumbs
		else:
			maxThumbs = len(games)
		desiredThumbWidth = int((self.width - (maxThumbs * self.__gap)) / maxThumbs)
		img = Image.open(games[0].getConsole().getNoCoverArtImg())
		img.close()
		w, h = img.size
		ratio = float(h) / float(w)
		self.__thumbWidth = desiredThumbWidth
		self.__thumbHeight = int(ratio * self.__thumbWidth)
		for t in self.__thumbnails:
			t.destroy()
		self.__thumbnails = []
		currentX = self.x
		for g in self.__games:
			self.__thumbnails.append(Thumbnail(self.renderer, currentX, self.y, self.__thumbWidth, self.__thumbHeight, g, self.__font, self.__txtColour, self.__drawLabels))
			currentX += self.__thumbWidth + self.__gap
		self.height = self.__thumbnails[0].height
