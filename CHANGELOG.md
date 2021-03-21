PES Changelog
=============

PES 2.9
-------

Date: 2021-03-04

Changes:

* Incorporated https://github.com/Pi-Entertainment-System/rasum to address issue #47
* Added RetroArch assets
* Updated Vice to use libretro version
* Updated SDL2 to version 2.0.14
* Updated RetroArch to commit 9086d241a7f20208cf279f6a7e877ae7bdca325d (v1.90 + updates)
* Updated mupen64plus-libretro-nx to commit b494ebf2da202f67dbd88c3c915262bb58f1c6ba
* Removed install-pi-bluetooth.sh install-bluez-ps3.sh as no longer required with recent Arch Linux updates
* Add the ability for the user to specify the ALSA audio device to use
* For Raspberry Pi2/3, added install-kodi.sh script to build Kodi 18.9 for /opt/vc drivers as Arch Linux now uses Kodi 19 KMS version

PES 2.8
-------

Date: 2020-02-15

Changes:

* Added desiredScreenWidth and desiredScreenHeight settings to set maximum screen size for the PES GUI - useful for large screens.
* Updated theGamesDb.net API URL for issue #43
* Updated RetroAchievements API for issue #44

PES 2.7
-------

Date: 2019-08-06

Changes:

* Fix for issue #40 - Fix string encoding error in dbupdate.py

PES 2.6
-------

Date: 2019-07-19

Changes:

* Fix for issue #37 - Handle when game overview is null from theGamesDb.net
* Fix for issue #38 - Add support for six button control pad support for MegaDive/Genesis games
* Fix for issue #39 - RetroAchievements not found for SNES and MegaDrive/Genesis games
* Added midnight commander package

PES 2.5
-------

Date: 2019-04-30

Changes:

* Updated consoles.ini to include support for missing Mupen64 ROM extensions thanks to Albert Schmalzried
* Updated dbupdate.py to use the new API for thegamesdb.net
* Updated SDL2 to version 2.0.9
* Updated to RetroArch 1.7.6
* Updated emulators to latest versions
* Added patches for PPSSPP to fix build process
* Updated libcec version to 4.0.4

PES 2.4.1
---------

Date: 2018-07-17

Changes:

* Updated thegamesdb.net URL for downloading game meta data and cover art (issue #34)

PES 2.4
-------

Date: 2018-05-02

Changes (and bug fixes):

* Updated SDL2 to version 2.0.8 as well as updating add-ons to latest versions
* Added framerate limiting code to improve GUI responsiveness
* Had to build and install gcc 5.4 to allow mupen64plus-video-gles2n64 to compile, ref: https://github.com/ricrpi/mupen64plus-video-gles2n64/issues/25
* Updated emulators to their latest versions

PES 2.3
-------

Date: 2017-11-23

Changes (and bug fixes):

* Added confirmation upon escape key event (issue #26)
* Added Bluetooth (Bluez) support for additional PS3 control pad clones (issue #28)
* Added Sony PS3 control pad mapping when connected via Bluez
* Improved image scaling code to handle images that are in the incorrect image format

PES 2.2
-------

Date: 2017-06-13

Changes (and bug fixes):

* Added support for Kodi (issue #14)
* Added support for hardcore RetroAchievements (issue #20)
* Added required files feature to emulators in consoles.ini (issue #23)
* Updated RetroArch to version 1.6
* Additional Atari 2600 extensions added
* Fixed time sync on Raspberry Pi
* Added guide for creating BerryBoot images (issue #19)

PES 2.1
-------

Date: 2017-02-10

Changes (and bug fixes):

* Added support for Commodore 64 thanks to the Vice emulator (issue #18)
* Added suupport for MSX thanks to libretro BlueMSX core (issue #16)
* Added support for MAME 2003 thanks to libretro MAME 2003 core (issue #11)
* Added support for PSP thanks to the PPSSPP emulator (issue #11)
* Updated RetroArch to version 1.3.6.
* Layout config options added to pes.ini.
* Splash screen added for Raspberry Pi Arch Linux builds.
* Remote control icon updated.
* Re-organised set-up scripts.
* Python profiling support added for debugging purposes.


PES 2.0
-------

Date: 2016-06-17

Brand new version of PES with a new GUI that is based on PySDL 2.0!

* ROM scanning is now up to 5x faster thanks to a parallel (multi processor) approach
* New GUI with various features!
* Added PS3 GASIA support
* Added support for RetroAchievements.org (issue #13)
* FAT32 now used for /data partition (issue #15)

PES 1.5.2
---------

Date: 2015-11-15

Changes (and bug fixes):

* Updated list of support extensions for Atari 2600.

PES 1.5.1
---------

Date: 2015-11-08

Changes (and bug fixes):

* Corrected build flags for the picodrive libretro core to produce a more optimized version. Thanks to Michell F for pointing out the error.

PES 1.5.0
---------

Date: 2015-10-22

Changes (and bug fixes):

* Added support for the Atari 2600 thanks to the Stella Libretro core.
* Added support for the Sega Mega Drive (Genesis) 32x thanks to the Picodrive core.
* Added support for Turbo Grafx 16 (PC Engine) thanks to the beetle-pce-fast core.
* Added p7zip package.

PES 1.4.1
---------

Date: 2015-08-26

Changes (and bug fixes):

* Fixed bug in Mupen64Plus config generation when four control pads are connected.
* Added missing crda ArchLinux package to remove CRDA warnings at boot time when using a WiFi network connection with the ArchLinux Raspberry Pi and ArchLinux Raspberry Pi 2 images.
* Added missing wpa_supplicant package to ArchLinux Raspberry Pi image.

PES 1.4
-------

Date: 2015-08-19

Changes (and bug fixes):

* Fixed incorrect L2 / R2 button mappings. Thanks to Steve McNamara for reporting the bug.
* Added libcec install script for ArchLinux from source to enable Python bindings as python-cec does not support libcec above version 2 (current version of libcec is 3)
* Updated joystick config files with correct L2 / R2 button mappings
* Updated install/remove packages scripts to add/remove to include cmake and swig for libcec build process
* Updated PES to use libcec Python bindings - this allows PES to set its name on the CEC network too unlike before
* Removed Python packages that are no longer required since moving to libcec rather than python-cec.

PES 1.3
-------

Date: 2015-07-05

Changes (and bug fixes):

* Fixed bug in game scraper where games with missing cover art were removed unintentionally from the PES database
* Fixed page total bug in game thumbnail menus
* Fixed minor game favouriting bug
* Fixed two button detection bugs when configuring control pads
* Fixed incorrect title on game info panel when switching games
* Updated set-up scripts to work out the location of the set-up directory dynamically
* Game object loading now more efficient which should reduce game pages loading time
* More than one console can now use the same API ID
* Added support for L3 and R3 buttons
* Added Sony PlayStation 4 control pad configuration files
* Added N64 support thanks to ricrpi's Mupen64Plus Raspberry Pi port
* Added control pad button configuration generation for Mupen64Plus
* Added SDL2 GLES installation for use by Mupen64Plus
* Added ability to favourite games using the select button or the S key
* Added netplay support to RetroArch installations
* Added Final Burn Alpha libretro core which also supports Neo Geo and Colecovision games
* Added ZX Spectrum support thanks to libretro's Fuse core
* Added MAME support thanks to libretro's imame4all core
* Added auto-partitioning of the user's SD card to take advantage of all available space
* Added support for user supplied cover art
* Added PES "games catalogue" to allow short ROM names to be mapped to their full names (e.g. for MAME and FBA ROM sets)
* Added ability to select which consoles are updated when scanning for ROMs

PES 1.2
-------

Date: 2015-02-11

Changes (and bug fixes):

* Added support for favourite games
* Added support for additional game info including last played, played count and year published
* Added separate BIOS directory for RetroArch
* Added support for GameBoy Advance thanks to gpsp
* Added HDMI-CEC config option
* Added Record object for handling SQLite calls
* Added the ability to browse by "page" for games
* Added joystick axis support at last!
* Added custom build of pygame to remove debug statements in joystick.c
* Added Raspberry Pi 2 support!
* Added paging support for game thumbnail menus
* Improved logging for unhandled exceptions
* Updated jstest.py utility
* Restructured conf.d directory
* Various fixes for the setup scripts
* Corrected bug in image auto resizing code for the console menu

PES 1.1
-------

Date: 2014-11-14

Changes (and bug fixes):

* console blanking disabled in Arch Linux
* ROM additions now possible via GUI, reboots no longer required
* Moved all PES classes into the new peslib.py module
* Arch Linux packages updated
* Raspberry Pi B+ now supported
* Console screen added
* Missing cover art graphics revamped (graphics from Eric Smith)
* PESPad added thus allowing players to use their tablets and smart phones as control pads
* Game info screen added
* Game data now sourced from theGamesDB.net rather than GiantBomb.com
* ROM scraping code now faster than in previous release
* Improved ROM name matching
* Automatic resizing of downloaded cover art added to minimise disk space and improve image load times
* Joystick configuration bug fixes
* RetroArch control pad hot plugging support added
* Ability to assign load/save state buttons for RetroArch added
* Database reset option added
* Python logging support added
* Fixed PES screen title changes between screens
* Fixed PyGame/SDL issue where multiple control pad models could not be used with the PES GUI (removed evdev kernel module)
* Added patches for QtSixAd to rename PS3 control pads without their Bluetooth MACs included therefore allows only one control pad config for all PS3 control pads
* Fixed RetroArch sound issue (Eric Smith)

PES 1.0
-------

Date: 2014-09-22

Initial release.
