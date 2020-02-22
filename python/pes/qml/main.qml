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

  onClosing: backend.close()

	Connections {
	    target: backend

			onHomeButtonPress: {
				dialog.open();
	      popupMenuView.forceActiveFocus()
			}

			onControlPadButtonPress: {
				console.warn("button: " + button)
				console.warn(mainWindow.activeFocusItem.Keys.downPressed({ key: Qt.KeyDown }))
			}

			onPopulateDbProgress: {
				populateDbProgressBar.avlue = progress
			}
	}

  Dialog {
    id: closeDialog
    modal: true
    width: 500
    height: 300
    x: (parent.width - width) / 2
    y: (parent.height - height) / 2

    background: Rectangle {
      color: Colour.dialogBg
      border.color: Colour.line
      anchors.fill: parent
    }

    ColumnLayout {
      spacing: 50
      Text {
        color: Colour.text
        font.pointSize: FontStyle.dialogSize
        text: "Are you sure you want to exit?"
      }

      RowLayout {
        spacing: 50

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
  }

  Dialog {
    id: dialog
    modal: true
    width: 500
    height: 600
    x: (parent.width - width) / 2
    y: (parent.height - height) / 2

    background: Rectangle {
      color: Colour.dialogBg
      border.color: Colour.line
    }

    ListModel {
      id: popupMenu

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
      delegate: menuDelegate
      keyNavigationEnabled: true
      keyNavigationWraps: true
    }
  }

  Shortcut {
    sequence: "Home"
    onActivated: {
      dialog.open();
      popupMenuView.forceActiveFocus()
    }
  }

  Shortcut {
    sequence: "Esc"
    onActivated: {
      console.debug("exit dialog");
      closeDialog.open()
			exitYesBtn.forceActiveFocus()
    }
  }

	Text {
		id: titleTxt
		text: "Pi Entertainment System"
		x: 0
		y: 0
		font.pointSize: 20
		font.bold: true
		font.family: "Arial"
		color: Colour.text
	}

	Text {
		id: clockTxt
		text: "Time"
		x: mainWindow.width - clockTxt.width
		y: 0
		font.pointSize: 20
		font.bold: true
		font.family: "Arial"
		color: Colour.text
		width: 400
	}

	Timer {
		interval: 1000
		running: true
		repeat: true
		//onTriggered: clockTxt.text = PES.getTime()
		onTriggered: clockTxt.text = backend.getTime()
	}

	Rectangle {
		id: headerLine
		x: 0
		y: 32
		height: 2
		width: mainWindow.width
		color: Colour.line
	}

	StackLayout {
		id: screenLayout
		x: 0
		y: headerLine.y + headerLine.height + 1
		width: parent.width
		height: parent.height - (headerLine.y + headerLine.height + 1)
		currentIndex: backend.getPopulateDb() ? 0: 1

		Rectangle {
			id: populateDbScreen
			color: mainWindow.color

			ColumnLayout {
				spacing: 10

				anchors {
        	left: parent.left
          right: parent.right
          verticalCenter: parent.verticalCenter
        }

				Text {
					id: populateDbText
					color: Colour.text
					font.pointSize: FontStyle.loadingSize
					Layout.alignment: Qt.AlignCenter
					text: "Creating PES database..."
				}

				ProgressBar {
					id: populateDbProgressBar
					from: 0
					value: 0
					to: 100
					Layout.alignment: Qt.AlignCenter
					Layout.preferredWidth: 500

					background: Rectangle {
						implicitWidth: 200
						implicitHeight: 30
						color: Colour.progressBarBg
						radius: 3
					}

					contentItem: Item {
						implicitWidth: 200
						implicitHeight: 25

						Rectangle {
							width: populateDbProgressBar.visualPosition * parent.width
							height: parent.height
							radius: 2
							color: Colour.progressBar
						}
					}

					Component.onCompleted: {
						if (backend.getPopulateDb()){
							backend.populateDb();
						}
					}
				}
			}
		}

		Rectangle {
			id: mainScreen
			color: mainWindow.color

		  ListModel {
		    id: menuModel

		    ListElement {
		      name: "Home"
		    }

		    ListElement {
		      name: "NES"
		    }

		    ListElement {
		      name: "Mega Drive"
		    }
		  }

		  Component {
		    id: menuDelegate
		    Rectangle {
		      height: 50
		      width: parent.width
		      color: focus ? Colour.menuFocus : Colour.menuBg

		      Keys.onPressed: {

		      }

		      Text {
		        text: name
		        color: parent.focus ? Colour.text : Colour.menuText
		        font.pointSize: FontStyle.menuSize
		      }
		    }
		  }

		  Rectangle {
		    id: menuRect
		    x: 0
		    y: parent.y
		    width: 400
		    height: parent.height
		    color: Colour.menuBg

		    Rectangle {
		      x: 0
		      y: parent.y + 20
		      width: parent.width
		      height: parent.height - this.y
		      color: parent.color
		      ListView {
		        id: menuView
		        anchors.fill: parent
		        focus: true
		        model: menuModel
		        delegate: menuDelegate
		        keyNavigationEnabled: true
		        keyNavigationWraps: true
		      }
		    }
		  }
		}
	}
}
