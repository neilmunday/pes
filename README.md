PES
===

PES is a graphical front end for a variety of games console emulators that has been written in [Python](https://www.python.org>) which is intended for use on the Raspberry Pi.

At the heart of PES is the PES GUI. This can be used on any OS that supports [Python](https://www.python.org>) and [PySDL2](http://pysdl2.readthedocs.org/>).

![PES GUI 1](http://pes.mundayweb.com/html/_images/pes-main.png?)
![PES GUI 2](http://pes.mundayweb.com/html/_images/pes-nes.png?)

For use on the Raspberry Pi, PES is distributed via an ArchLinux image (see http://pes.mundayweb.com/html/Installation.html#downloading for the latest image) which contains pre-compiled emulators for the Raspberry Pi. The configuration and compilation scripts used to create the image are also included in this repository.

The PES Raspberry Pi image has the following features:

* Graphical interface
* Works with HDMI CEC enabled displays thus allowing you to use your TV remote control to navigate the interface
* Automatic downloading of game cover art (requires network connection)
* Works with USB game pads
* PS3 control pad support via Bluetooth (requires compatible Bluetooth dongle)
* Automatic pairing of PS3 control pads
* File sharing support to allow you to install new games (requires network connection)
* Uses ArchLinux for a minimal system installation
* Provides game platform emulation for:

  * Atari 2600
  * Commodore64
  * Final Burn Alpha (FBA)
  * MAME
  * MSX
  * Neo Geo
  * Nintendo 64 (N64)
  * Nintendo Entertainment System (NES)
  * Nintendo Game Boy
  * Nintendo Game Boy Advance
  * Nintendo Game Boy Color
  * Nintendo Super Entertainment System (SNES)
  * Sega CD
  * Sega Game Gear
  * Sega Master System
  * Sega Mega Drive (aka Genesis)
  * Sega Mega Drive (aka Genesis) 32x
  * Sony PlayStation
  * Sony PSP
  * Turbo Grafx 16 (aka PC Engine)
  * ZX Spectrum

The documentation and Raspberry Pi image for PES can be found at: http://pes.mundayweb.com

Starting PES
------------

From the command line run:

```bash
/opt/pes/bin/pes
```

By default PES will start in fullscreen mode. To start in windowed mode, please use the `-w` command line option.

To enable debug messages, use the `-v` command line option.

To enable Python profiling of the PES code, please use the `-p` command line option.

You can also turn profiling on and off whilst PES is executing by sending the `SIGHUP` signal to the main.py Python process. Once profiling is disabled, the stats for the last profiling session will be printed.

Acknowledgements
----------------

I would like to thank the following people/groups as without them PES would not be possible:

* Frank Raiser for his [image scaling code](http://www.pygame.org/pcr/transform_scale) that I have modified for use by PES to scale thumbnail images
* The maintainers of [RetroArch](http://www.libretro.com) and all of the emulators that PES uses:

  * beetle-pce-fast https://github.com/libretro/beetle-pce-fast-libretro
  * blueMSX-libretro https://github.com/libretro/blueMSX-libretro
  * fceu-next https://github.com/libretro/fceu-next
  * fuse-libretro https://github.com/libretro/fuse-libretro
  * gambatte-libretro https://github.com/libretro/gambatte-libretro
  * Genesis-Plus-GX https://github.com/ekeeke/Genesis-Plus-GX
  * gpsp https://github.com/libretro/gpsp
  * imame4all-libretro https://github.com/libretro/imame4all-libretro
  * mame2003-libretro https://github.com/libretro
  * libretro-fba https://github.com/libretro/libretro-fba
  * pcsx_rearmed https://github.com/notaz/pcsx_rearmed
  * PicoDrive https://github.com/libretro/picodrive
  * Pocket SNES https://github.com/libretro/pocketsnes-libretro
  * ppsspp https://github.com/hrydgard/ppsspp
  * Ric RPi's Mupen64Plus fork https://github.com/ricrpi
  * stella-libretro https://github.com/libretro/stella-libretro
  * vice-emu https://sourceforge.net/projects/vice-emu

* falkTX for creating the [QtSixA](http://qtsixa.sourceforge.net) daemon and utilities which is used by PES for using Sony PlayStation 3 control pads via Bluetooth.
* All the maintainers of [Arch Linux](http://archlinuxarm.org/platforms/armv6/raspberry-pi>)
* [theGamesDB.net](http://thegamesdb.net) for their comprehensive game meta data API
* All the maintainers of the [Python](https://www.python.org>) programming language in which PES is written
* Marcus von Appen for [PySDL2](http://pysdl2.readthedocs.org/>) which PES uses to create its GUI
* [Game-icons.net](http://game-icons.net) for providing some of the icons used by PES
* The [Raspberry Pi Foundation](http://www.raspberrypi.org)
* Eric Smith for his many hours of testing, finding bugs, suggesting new features and for supplying graphics for PES
* Alex Moriarty for finding and fixing bugs in some of PES' set-up scripts.
* Steve McNamara for reporting bugs and testing fixes.
* David Murray for his bug finding skills and testing
* Gerald Davies for lending me his NES and SNES USB control pads for testing
* Paul Palmer for lending me his XBOX 360 control pad for testing
* [Michell F](https://github.com/mfwhite) for testing and reviewing PES
* Paul Panther for testing and suggesting features for PES
* Fredrik for testing and suggesting features for PES
* nwildner for testing and suggesting features for PES
* Albert Schmalzried for helping test PES

BerryBoot Images
----------------

If you are interested in creating a PES BerryBoot image then please see BERRYBOOT.md.

It is also possible that PES BerryBoot images might be available at https://pes.mundayweb.com.
