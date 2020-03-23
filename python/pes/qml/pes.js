
function getConsolesWithGames() {
  return backend.getConsoles();
}

function mainMenuEvent(text) {
	switch(text) {

	}
}

function pesDialogEvent(text) {
	switch(text) {
		case "Update Games": {
			break;
		}
		case "Exit": {
			pesDialog.close();
			closeDialog.open();
			break;
		}
	}
}

function updateHomeScreen() {
  if (menuModel.count == 1) {
    noGamesText.visible = true;
  }
}

function updateMenuModel() {
  // remove existing entries
  if (menuModel.count > 1) {
    for (var i = menuModel.count - 1; i > 1; i--) {
      menuModel.remove(i);
    }
  }
  var consoles = getConsolesWithGames();
  for (var i = 0; i < consoles.length; i++) {
    menuModel.append(consoles[i]);
  }
}
