import QtQuick 2.7
import QtQuick.Layouts 1.12
import QtQuick.Window 2.2
import QtQuick.Controls 2.5
//import QtGamepad 1.12
import "Components"
import "./Style/" 1.0
import "pes.js" as PES

ApplicationWindow {

  id: mainWindow
  visible: true
  color: Colour.bg
  height: 600
  width: 800
  visibility: "FullScreen"

  onClosing: backend.close()

	Connections {
	    target: backend

			onHomeButtonPress: {
				pesDialog.open();
	      popupMenuView.forceActiveFocus();
			}

			onControlPadButtonPress: {
				console.warn("button: " + button);
				console.warn(mainWindow.activeFocusItem.Keys.downPressed({ key: Qt.KeyDown }));
			}
	}

  Dialog {
    id: closeDialog
    modal: true
    width: 500
    height: 150
    x: (parent.width - width) / 2
    y: (parent.height - height) / 2

    background: Rectangle {
      color: Colour.dialogBg
      border.color: Colour.line
      anchors.fill: parent
    }

    ColumnLayout {
      spacing: 10
      Text {
        color: Colour.text
        font.pointSize: FontStyle.dialogSize
        text: "Are you sure you want to exit?"
      }

      RowLayout {
        spacing: 10

        DialogButton {
					id: exitYesBtn
          Layout.fillWidth: true
          Layout.minimumWidth: 100
					Layout.minimumHeight: 50
          btnText: "Yes"
					focus: true
					KeyNavigation.right: exitNoBtn

					Keys.onReturnPressed: {
						mainWindow.close()
					}
        }

				DialogButton {
					id: exitNoBtn
          Layout.fillWidth: true
          Layout.minimumWidth: 100
					Layout.minimumHeight: 50
          btnText: "No"
					KeyNavigation.left: exitYesBtn

					Keys.onReturnPressed: {
						closeDialog.close()
					}
        }
      }
    }

		onOpened: {
			exitYesBtn.forceActiveFocus()
		}
  }

  Dialog {
    id: pesDialog
    modal: true
    width: 500
    height: 274
    x: (parent.width - width) / 2
    y: (parent.height - height) / 2

    background: Rectangle {
      color: Colour.menuBg
      border.color: Colour.line
    }

    ListModel {
      id: popupMenu

      ListElement {
        name: "Update Games"
      }

      ListElement {
        name: "Settings"
      }

      ListElement {
        name: "Reboot"
      }

      ListElement {
        name: "Shutdown"
      }

      ListElement {
        name: "Exit"
      }
    }

    ListView {
      id: popupMenuView
      anchors.fill: parent
      focus: true
      model: popupMenu
      delegate: MenuDelegate {
				Keys.onReturnPressed: PES.pesDialogEvent(text);
			}
      keyNavigationEnabled: true
      keyNavigationWraps: true
    }

		onOpened: popupMenuView.forceActiveFocus()
  }

  Shortcut {
    sequence: "Home"
    onActivated: pesDialog.open()
  }

  Shortcut {
    sequence: "Esc"
    onActivated: closeDialog.open()
  }

	Text {
		id: titleTxt
		text: "Pi Entertainment System"
		x: 0
		y: 0
		font.pointSize: FontStyle.titleSize
		font.bold: true
		font.family: FontStyle.font
		color: Colour.text
	}

	Text {
		id: clockTxt
		text: "Time"
		x: mainWindow.width - clockTxt.width
		y: 0
		font.pointSize: FontStyle.titleSize
		font.bold: true
		font.family: FontStyle.font
		color: Colour.text
		rightPadding: 5
	}

	Timer {
		interval: 1000
		running: true
		repeat: true
		onTriggered: {
      clockTxt.text = backend.getTime();
    }
	}

	Rectangle {
		id: headerLine
		x: 0
		y: 32
		height: 2
		width: mainWindow.width
		color: Colour.line
	}

  Rectangle {
    x: 0
    y: headerLine.y + headerLine.height + 1
    width: parent.width
    height: parent.height - (headerLine.y + headerLine.height + 1)

    id: mainScreen
    color: mainWindow.color

    ListModel {
      id: menuModel

      ListElement {
        name: "Home"
      }
    }

    Rectangle {
      id: menuRect
      x: 0
      y: 0
      width: 400
      height: parent.height
      color: Colour.menuBg

      Rectangle {
        x: 0
        y: parent.y
        width: parent.width
        height: parent.height - this.y
        color: parent.color

        ScrollView {
          width: parent.width
          height: parent.height
          clip: true

          focus: true

          ListView {
            id: menuView
            anchors.fill: parent
            focus: true
            model: menuModel
            delegate: MenuDelegate {
							Keys.onReturnPressed: PES.mainMenuEvent(text);
						}
            keyNavigationEnabled: true
            keyNavigationWraps: false
          }
        }
      }
    }

    Component.onCompleted: PES.updateMenuModel()
  }

	StackLayout {
		id: screenLayout
		x: menuRect.width + 1
		y: headerLine.y + headerLine.height + 1
		width: mainWindow.width - menuRect.width
		height: parent.height - (headerLine.y + headerLine.height + 1)
		currentIndex: 0

    Rectangle {
      id: homeScreen
      width: parent.width
      color: Colour.bg

      Text {
        id: welcomeText
        padding: 10
        text: "Welcome to PES!"
        font.pointSize: FontStyle.headerSize
    		font.bold: true
    		font.family: FontStyle.font
    		color: Colour.text
      }

      Text {
        id: noGamesText
        y: welcomeText.height + 10
        visible: false
        padding: 10
        text: "You have not added any games to PES yet. To do so press the Home button and select 'Update Games' option."
        font.pointSize: FontStyle.bodySize
    		font.bold: true
    		font.family: FontStyle.font
    		color: Colour.text
        wrapMode: Text.Wrap
        width: parent.width // must set width for wrapping to work
      }

      Component.onCompleted: PES.updateHomeScreen()
    }
	}
}
