Setting PES up from scratch
===========================

Notes:

* this requires a Linux system and at least a 4GB SD card ideally.
* unless otherwise stated all commands are to be run as root.

Format SD card
==============

Take a note of which device your SD card is presented as (hint: use dmesg).

Use gparted to remove all existing partitions, then use gparted to create two partitions on your SD card:

	- First partition, 50MB fat16 with the label BOOT
	- Second partition 2GB ext4 with the label ROOT

Note not all the space on the SD card will be used, we will be leaving some free for PES to set-up automatically as a /data partition when it first boots.

Install ArchLinux
=================

cd ~
mkdir rpi
cd rpi
mkdir boot root
wget http://archlinuxarm.org/os/ArchLinuxARM-rpi-4-latest.tar.gz
mount /dev/sdd1 boot
mount /dev/sdd2 root
cd root
tar xvfz ../ArchLinuxARM-rpi4-latest.tar.gz
cd boot
mv * ../../boot/

Check that ~/rpi/boot/cmdline.txt contains:

	root=/dev/mmcblk0p2

This option tells the boot loader which device to use as the root partition. In our case it must be the second partition on the SD card.

Edit ~/rpi/boot/cmdline.txt and uncomment the Turbo over clocking section.

Also set check the following are set:

	hdmi_ignore_edid=0xa5000080
	gpu_mem=384
	dtparam=audio=on
	dtoverlay=vc4-fkms-v3d
	disable_overscan=0
	overscan_scale=1

The extra GPU RAM is required for some of the emulators, e.g. Mupen64Plus and the "dtpara=audio" parameter enables the ALSA kernel module required for sound.

Note: if you want to do the rest of configuration via SSH of your Raspberry Pi also edit ~/rpi/root/ssh/sshd_config and add the line:

	PermitRootLogin yes

Umount the SD card:

umount ~/rpi/boot
umount ~/rpi/root

Now put the SD card into your Raspberry Pi, plug in an Ethernet cable and boot it.

First Boot
==========

Once booted run the following commands to begin setting up PES:

Add pi user:

	useradd -d /home/pi -m -U -G audio,video,input,users pi

Set password (use "raspberry" by default):

	passwd pi

Update packages:

	pacman-key --init
	pacman-key --populate archlinuxarm
	pacman -Syu

Install git and sudo:

	pacman -S git sudo

Set-Up sudo:

	groupadd sudoers
	usermod -a -G sudoers pi

Run visudo and add a line like so:

	%sudoers ALL=(ALL) NOPASSWD: ALL

Now reboot.

Second Boot
===========

Log in as the "pi" user either at the keyboard or via SSH.

Edit /etc/motd and set as you wish, e.g. sudo nano /etc/motd

	Welcome to the Pi Entertainment System (PES)

	Image Version: 2015-08-17 (Raspberry Pi 2, Arm7)

	PES Version: 1.4

	Website: http://pes.mundayweb.com

Check out the PES git repo:

	cd ~
	git clone https://github.com/neilmunday/pes

Make some extra directories and links needed by PES:

	cd pes
	mkdir log
	ln -s /data/roms roms
	ln -s /data/coverart coverart

Note: the /data partition will be automatically created when PES first loads.

Now put the kettle on for the next step (you might need to leave this going overnight):

	cd ~/pes/setup/arch-rpi2
	./setup.sh

Or you can opt to run each "install-" script yourself. Note: not all are run by setup.sh as some install emulators etc. that are not production ready.

Now reboot and you should be good to go!
