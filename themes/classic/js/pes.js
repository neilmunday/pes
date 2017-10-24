/**
    This file is part of the Pi Entertainment System (PES).

    PES provides an interactive GUI for games console emulators
    and is designed to work on the Raspberry Pi.

    Copyright (C) 2017 Neil Munday (neil@mundayweb.com)

    PES is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    PES is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with PES.  If not, see <http://www.gnu.org/licenses/>.
*/
    
/* Global variables */

var channelLoaded = false;
var menus = {};
var screenStack = [];
var consoles = [];
var keyboardSelect;
var timezoneSelect;

jQuery.extend(jQuery.expr[':'], {
	focus: "a == document.activeElement"
});

/* Functions */

function addLeadingZero(i){
	if (i < 10){
		return '0' + i;
	}
	return i;
}

function commandLineExit(){
	showMsgBox("Are you sure you want to exit to the command line?", function(){
		console.log("exiting")
		handler.exit();
	});
}

function formatTime(s){
	var hours = Math.floor(s / 3600);
	var mins = Math.floor((s % 3600) / 60);
	var secs = s % 60;
	return hours + ':' + addLeadingZero(mins) + ':' + addLeadingZero(secs);
}

function setIconVisible(icon, visible){
	if (visible){
		$('#' + icon).show();
	}
	else{
		$('#' + icon).hide();
	}
}

function showScreen(s){
	$("div[id^='screen_'], div[id^='menu_']").hide();
	$("#screen_" + s).show();
	$("#menu_" + s).show();
	$("#menu_" + s).children().show();
	$("#menu_" + s).focus();
	menus[s].setSelected(0);
	screenStack.push(s);
}

function showMsgBox(msg, fn){
	var obj = document.activeElement;
	$("#msgBoxCancelBtn").show();
	$("#msgBoxLayer, #msgBox").show();
	$("#msgBoxTxt").text(msg);
	
	$("#msgBox").keyup(function(event){
		if (event.key == "Backspace"){
			$("#msgBoxLayer, #msgBox").hide();
			obj.focus(); // return focus
		}
	});
	
	$("#msgBoxOkBtn").on("keyup", function(event){
		if (event.key == "ArrowRight" || event.key == "ArrowLeft"){
			$("#msgBoxCancelBtn").focus();
		}
		else if (event.key == "Enter"){
			fn();
		}
	});
	
	$("#msgBoxCancelBtn").on("keyup", function(event){
		if (event.key == "ArrowRight" || event.key == "ArrowLeft"){
			$("#msgBoxOkBtn").focus();
		}
		else if (event.key == "Enter"){
			$("#msgBoxLayer, #msgBox").hide();
			obj.focus(); // return focus
		}
	});
	$("#msgBoxOkBtn").focus();
}

function showWarningMsgBox(msg){
	var obj = document.activeElement;
	$("#msgBoxCancelBtn").hide();
	$("#msgBoxLayer, #msgBox").show();
	$("#msgBoxTxt").text(msg);
	$("#msgBox").focus();
	
	$("#msgBox").keyup(function(event){
		if (event.key == "Backspace"){
			$("#msgBoxLayer, #msgBox").hide();
			obj.focus(); // return focus
		}
	});
	
	$("#msgBoxOkBtn").on("keyup", function(event){
		if (event.key == "Enter"){
			$("#msgBoxLayer, #msgBox").hide();
			obj.focus(); // return focus
		}
	});
	
	$("#msgBoxOkBtn").focus();
}

function showPopupMenu(){
	var obj = document.activeElement;
	$("#popupMenu").keyup(function(event){
		if (event.key == "Backspace"){
			$("#popupMenu, #dialogueLayer").hide();
			obj.focus();
		}
	});
	$("#dialogueLayer, #popupMenu").show();
	$("#settingsBtn").focus();
	$("#backBtn").keyup(function(event){
		if (event.key == "ArrowUp"){
			$("#exitBtn").focus();
		}
		else if (event.key == "ArrowDown"){
			$("#settingsBtn").focus();
		}
		else if (event.key == "Enter"){
			$("#popupMenu, #dialogueLayer").hide();
			obj.focus();
		}
	});
}

function updateClock(){
	var now = new Date();
	var s = addLeadingZero(now.getHours()) + ':' + addLeadingZero(now.getMinutes()) + ':' + addLeadingZero(now.getSeconds()) + ' ' + addLeadingZero(now.getDate()) + '/' + addLeadingZero(now.getMonth() + 1) + '/' + now.getFullYear();
	$('#clock').html(s);
}

function updateIcons(){
	if (channelLoaded){
		window.handler.getIpAddress(function(ip){
			setIconVisible('networkIcon', ip != '127.0.0.1');
		});
	}
}

/* Objects */

function Menu(el){
	var me = this;
	this.el = el;
	this.selected = 0;
	this.items = [];
	this.addMenuItem = function(text, fn, previewEl){
		var m = new MenuItem(text, fn, previewEl);
		me.items.push(m);
	};
	this.draw = function(){
		$('#' + me.el).empty();
		for (var i = 0; i < me.items.length; i++){
			$('#' + me.el).append("<button class=\"menuBtn\" type=\"button\" id=\"" + me.el + "_" + i + "_btn\">" + me.items[i].text + "</button>\n");
		}
	};
	this.goDown = function(){
		me.setSelected(me.selected + 1);
	};
	this.goUp = function(){
		me.setSelected(me.selected - 1);
	};
	this.insertMenuItem = function(text, pos, fn, previewEl){
		if (pos >= me.items.length){
				me.addMenuItem(text, fn, previewEl);
		}
		else{
			var m = new MenuItem(text, fn);
			me.items.splice(pos, 0, m);
		}
	};
	this.focus = function(){
		$("#" + me.el + "_" + me.selected + "_btn").focus();
	};
	$("#" + this.el).on("keyup", "button", function(event){
		if (event.key == "Enter"){
			me.items[me.selected].fn();
		}
	});
	this.setSelected = function(i){
		//console.log("selecting: " + i);
		if (i > me.items.length - 1){
			i = 0;
		}
		else if (i < 0){
			i = me.items.length - 1;
		}
		me.selected = i;
		$("#" + me.el + "_" + i + "_btn").focus();
		$(".preview").hide();
		if (me.items[me.selected].previewEl){
			$("#" + me.items[me.selected].previewEl).show();
		}
	}
}

function MenuItem(text, fn, previewEl){
	this.text = text;
	this.fn = fn;
	this.previewEl = previewEl;
	console.log(this.previewEl);
}

function HorizontalSelect(el, options, selected){
		var me = this;
		this.el = el;
		this.options = options;
		this.selected = selected;
		this.focusNext = null;
		this.focusPrec = null;
		$("#" + this.el).addClass("horizontalSelect");
		this.draw = function(){
			$("#" + me.el).html(me.options[me.selected]);
		};
		this.focus = function(){
			$("#" + me.el).focus();
		};
		$("#" + this.el).on("keyup", function(event){
			if (event.key == "ArrowLeft"){
				if (me.selected - 1 < 0){
					me.selected = me.options.length - 1;
				}
				else{
					me.selected--;
				}
				me.draw();
			}
			else if (event.key == "ArrowRight"){
				if (me.selected + 1 == me.options.length){
					me.selected = 0;
				}
				else{
					me.selected++;
				}
				me.draw();
			}
			else if (event.key == "ArrowDown"){
				if (me.focusNext){
					$("#" + me.focusNext).focus();
				}
			}
			else if (event.key == "ArrowUp"){
				if (me.focusPrev){
					$("#" + me.focusPrev).focus();
				}
			}
		});
		this.setFocusNext = function(s){
			me.focusNext = s;
		};
		this.setFocusPrev = function(s){
			me.focusPrev = s;
		};
		this.setSelected = function(i){
			if (i >= 0 && i < me.options.length){
				me.selected = i;
				me.draw();
			}
			else{
				console.error("HorizontalSelect.setSelected: index out of range: " + i);
			}
		};
		this.setSelectedOption = function(s){
			var i = me.options.indexOf(s);
			if (i == -1){
				console.error("HorizontalSelect.setSelectedOption: could not find \"" + s + "\"");
			}
			else{
				me.selected = i;
				me.draw();
			}
		}
}

/* Document Ready */

$(document).ready(function(){
	
	var channel = new QWebChannel(qt.webChannelTransport, function(channel){
		window.handler = channel.objects.handler; // make global
		//handler = channel.objects.handler;
		
		channel.objects.loadingThread.progressSignal.connect(function(percent, status){
			$("#loadingProgressBarComplete").width(percent + "%");
			$("#loadingProgressBarTxt").html("Loading: " + status);
		});
		
		channel.objects.loadingThread.finishedSignal.connect(function(){
			handler.getConsoles(function(consoleArray){
				var gamesFound = false;
				$.each(consoleArray, function(i, c)
				{
					if (c.gameTotal > 0){
						gamesFound = true;
						menus["main"].insertMenuItem(c.name, i + 1, function(){
							console.log(c.name);
						});
					}
					consoles.push(c);
				});
				
				menus["main"].draw();
				menus["main"].setSelected(0);
				
				if (!gamesFound){
					$("#panel_main").html("<p>You have not added any ROMs yet to the PES database.</p><p>To perform a ROM scan, please press Home/Guide to access the Settings menu.</p>")
				}
			});
			$("#startUp").hide();
			$("#main").show();
			menus["main"].setSelected(0);
		});
		
		channel.objects.romScanMonitorThread.progressSignal.connect(function(percent, romsRemaining, timeRemaining, romName, coverArtPath){
			$("#scanProgressBarComplete").width(percent + "%");
			$("#romsRemainingCell").html(romsRemaining);
			$("#timeRemainingCell").html(formatTime(timeRemaining));
			if (coverArtPath != "0"){
				$("#romPreviewImg").attr("src", "file://" + coverArtPath);
			}
		});
		
		channel.objects.romScanMonitorThread.romsFoundSignal.connect(function(romTotal){
			$("#romsFoundCell").html(romTotal);
		});
		
		channel.objects.romScanMonitorThread.finishedSignal.connect(function(processed, added, updated, timeTaken){
			$("#panel_update_games_process").hide();
			$("#panel_update_games_finished").show();
			$("#romsProcessedCell").html(processed);
			$("#romsAddedCell").html(added);
			$("#romsUpdatedCell").html(updated);
			$("#timeTakenCell").html(formatTime(timeTaken));
		});
		
		channel.objects.handler.joysticksConnectedSignal.connect(function(total){
			$("#gamepadIcons").empty();
			for (var i = 0; i < total; i++){
				console.log("appending");
				$("#gamepadIcons").append("<img class=\"gamepadIcon\" />");
			}
		});

		channelLoaded = true;
		
		handler.channelReady();
		
		/*window.handler.controllerConnected(function(result){
			setIconVisible('gamepadIcon', result);
		});*/
		
		console.log("QWebChannel ready");
	});
	
	updateClock();
	updateIcons();
	setInterval(updateClock, 1000);
	setInterval(updateIcons, 2000);
	
	/* Define menus */
	
	menus["main"] = new Menu('menu_main');
	menus["main"].addMenuItem('Home', function(){
		console.log("Home");
	}, "screen_main");
	
	menus["main"].addMenuItem('Kodi', function(){
		console.log('Kodi');
	}, "kodi_preview");
	menus["main"].setSelected(0);
	
	menus["settings"] = new Menu('menu_settings');
	menus["settings"].addMenuItem('Update Games', function(){
		$("#update_games_preview").hide();
		$("#panel_update_games").show();
		$("#update_console_list").empty();
		for (var i = 0; i < consoles.length; i++){
			$("#update_console_list").append("<div><input id=\"update_console_list_" + consoles[i].name + "\" checked type=\"checkbox\" value=\"" + consoles[i].name + "\"><label for=\"update_console_list_" + consoles[i].name + "\"><span><span></span></span>" + consoles[i].name + "</label></div>\n");
		}
		$("#updateConsolesBtn").focus();
	}, "update_games_preview");
	menus["settings"].addMenuItem("Update Badges", function(){
		
	}, "update_badges_preview");
	menus["settings"].addMenuItem("Control Pad", function(){
		
	});
	
	menus["settings"].addMenuItem("System", function(){
		$("#system_settings_preview").hide();
		handler.getTimezones(function(timezones){
			handler.getTimezone(function(timezone){
				timezoneSelect = new HorizontalSelect("timezoneSelect", timezones, 0);
				timezoneSelect.setSelectedOption(timezone);
				timezoneSelect.focus();
				timezoneSelect.setFocusNext("keyboardSelect");
			});
		});
		handler.getKeyboardLayouts(function(keyboardLayouts){
			handler.getKeyboardLayout(function(keyboardLayout){
				keyboardSelect = new HorizontalSelect("keyboardSelect", keyboardLayouts, 0);
				keyboardSelect.setSelectedOption(keyboardLayout);
				keyboardSelect.setFocusNext("saveSettingsBtn");
				keyboardSelect.setFocusPrev("timezoneSelect");
			});
		});
		$("#panel_system_settings").show();
	}, "system_settings_preview");

	menus["settings"].addMenuItem("About", function(){

	}, "about");
	menus["settings"].draw();
	
	$(document).on("keyup", function(event){
		if (event.key == "Home"){
			showPopupMenu();
		}
	});
	
	/* Menu functions */
	
	$("#menu_main").focus();
	screenStack.push("main");
	
	$(".menu").on("keyup", "button", function(event){
		if (event.type == "keyup"){
			var menuName = $(this).attr("id").split("_")[1];
			//console.log("key:" + event.key);
			switch (event.key){
				case "ArrowDown": menus[menuName].goDown();; break;
				case "ArrowUp": menus[menuName].goUp(); break;
				case "Backspace": {
					if (screenStack.length > 1){
						screenStack.pop();
						showScreen(screenStack[screenStack.length - 1]);
					}
				}; break;
			}
		}
	});
	
	/* popup events */
	
	$("#settingsBtn").keyup(function(event){
		if (event.key == "ArrowUp"){
			$("#backBtn").focus();
		}
		else if (event.key == "ArrowDown"){
			$("#poweroffBtn").focus();
		}
		else if (event.key == "Enter"){
			$("#popupMenu, #dialogueLayer").hide();
			$(".panel").hide();
			showScreen("settings");
		}
	});
	
	$("#poweroffBtn").keyup(function(event){
		if (event.key == "ArrowUp"){
			$("#settingsBtn").focus();
		}
		else if (event.key == "ArrowDown"){
			$("#rebootBtn").focus();
		}
		else if (event.key == "Enter"){
			console.log("power off");
		}
	});
	
	$("#rebootBtn").keyup(function(event){
		if (event.key == "ArrowUp"){
			$("#poweroffBtn").focus();
		}
		else if (event.key == "ArrowDown"){
			$("#exitBtn").focus();
		}
		else if (event.key == "Enter"){
			console.log("reboot");
		}
	});
	
	$("#exitBtn").keyup(function(event){
		if (event.key == "ArrowUp"){
			$("#rebootBtn").focus();
		}
		else if (event.key == "ArrowDown"){
			$("#backBtn").focus();
		}
		else if (event.key == "Enter"){
			//$("#popupMenu").hide();
			commandLineExit();
		}
	});

	/* System settings screen */
	
	$("#panel_system_settings").keyup(function(event){
		if (event.key == "Backspace"){
			$("#panel_system_settings").hide();
			$("#system_settings_preview").show();
			menus["settings"].focus();
		}
	});
	
	$("#saveSettingsBtn").keyup(function(event){
		if (event.key == "ArrowUp"){
			$("#keyboardSelect").focus();
		}
		else if (event.key == "Enter"){
			handler.saveSettings($("#timezoneSelect").html(), $("#keyboardSelect").html(), function(result){
				if (result[0]){
					$("#panel_system_settings").hide();
					$("#system_settings_preview").show();
					menus["settings"].focus();
				}
				else {
					showWarningMsgBox("Unable to save settings: " + result[1]);
				}
			});
		}
	});
	
	/* Update Games Screen */
	
	$("#panel_update_games").keyup(function(event){
		if (event.key == "Backspace"){
			$("#panel_update_games").hide();
			$("#update_games_preview").show();
			menus["settings"].focus();
		}
	});
	
	$("#updateConsolesBtn").keyup(function(event){
		if (event.key == "ArrowRight"){
			$("#updateSelectAllConsolesBtn").focus();
		}
		else if (event.key == "ArrowUp"){
			//$("#update_console_list").children(":checkbox").last().focus();
			$("#update_console_list").find("input").last().focus();
		}
		else if (event.key == "Enter"){
			$("#panel_update_games").hide();
			$("#panel_update_games_process").show();
			$("#scanProgressBarComplete").width(0);
			var updateArray = [];
			var chkboxes = $("#update_console_list").find("input");
			for (var i = 0; i < chkboxes.length; i++){
				if ($(chkboxes[i]).prop("checked")){
					updateArray.push($(chkboxes[i]).val());
				}
			}
			channel.objects.romScanMonitorThread.startThread(updateArray);
			$("#stopRomScanBtn").prop("disabled", false);
			$("#stopRomScanBtn").focus();
		}
	});
	
	$("#updateSelectAllConsolesBtn").keyup(function(event){
		if (event.key == "ArrowRight"){
			$("#updateSelectNoneConsolesBtn").focus();
		}
		else if (event.key == "ArrowLeft"){
			if (!$("#updateConsolesBtn").prop("disabled")){
				$("#updateConsolesBtn").focus();
			}
		}
		else if (event.key == "ArrowUp"){
			$("#update_console_list").find("input").last().focus();
		}
		else if (event.key == "Enter"){
			$("#update_console_list").find("input").prop("checked", true);
			$("#updateConsolesBtn").prop("disabled", false);
		}
	});
	
	$("#updateSelectNoneConsolesBtn").keyup(function(event){
		if (event.key == "ArrowLeft"){
			$("#updateSelectAllConsolesBtn").focus();
		}
		else if (event.key == "ArrowUp"){
			//$("#update_console_list").children(":checkbox").last().focus();
			$("#update_console_list").find("input").last().focus();
		}
		else if (event.key == "Enter"){
			$("#update_console_list").find("input").prop("checked", false);
			$("#updateConsolesBtn").prop("disabled", true);
		}
	});
	
	$("#panel_update_games").on("keyup", "input", function(event){
		var chkboxes = $("#update_console_list").find("input");
		var selected = -1;
		for (var i = 0; i < chkboxes.length; i++){
			if (chkboxes[i] == event.target){
				selected = i;
				break;
			}
		}
		//console.log("found checkbox at: " + selected);
		if (selected > -1){
			if (event.key == "ArrowUp"){
				if (selected - 1 < 0){
					chkboxes[chkboxes.length - 1].focus();
				}
				else{
					chkboxes[selected - 1].focus();
				}
			}
			else if (event.key == "ArrowDown"){
				if (selected + 1 == chkboxes.length){
					if ($("#updateConsolesBtn").prop("disabled")){
						$("#updateSelectAllConsolesBtn").focus();
					}
					else{
						$("#updateConsolesBtn").focus();
					}
				}
				else{
					chkboxes[selected + 1].focus();
				}
			}
			else if (event.key == "Enter"){
				$(this).prop("checked", !$(this).prop("checked"));
				if ($(this).prop("checked")){
					$("#updateConsolesBtn").prop("disabled", false);
				}
				else{
					var foundChecked = false;
					for (var i = 0; i < chkboxes.length; i++){
						if ($(chkboxes[i]).prop("checked")){
							foundChecked = true;
							break;
						}
					}
					$("#updateConsolesBtn").prop("disabled", !foundChecked);
				}
			}
		}
		else{
			console.error("Could not find checkbox");
		}
	});
	
	/* Update Games Rom Scan Screen */
	
	$("#stopRomScanBtn").keyup(function(event){
		if (event.key == "Enter"){
			channel.objects.romScanMonitorThread.stop();
			$("#stopRomScanBtn").prop("disabled", true);
		}
	});
	
	/* MsgBox functions */
	
	$("#msgBoxOkBtn").on("keyup", function(event){
		if (event.key == "ArrowRight" || event.key == "ArrowLeft"){
			$("#msgBoxCancelBtn").focus();
		}
	});
	
	$("#msgBoxCancelBtn").on("keyup", function(event){
		if (event.key == "ArrowRight" || event.key == "ArrowLeft"){
			$("#msgBoxOkBtn").focus();
		}
	});
	
	/*$("button, input[type='button']").on("keyup", function(event){
		if (event.key == "Enter"){
			console.log("button key up handler");
			event.stopImmediatePropagation();
			$(this).trigger("click");
		}
	});*/
	
	/*$("#startUp").hide();
	$("#main").show();
	menus["main"].draw();
	menus["main"].setSelected(0);*/
});
