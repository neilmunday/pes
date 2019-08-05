import QtQuick 2.7
import "../Style/" 1.0

Rectangle {
  color: focus ? Colour.menuFocus : Colour.menuBg
  property alias btnText: btnText.text

  Text {
    id: btnText
    anchors.centerIn: parent
    text: "Undefined"
    color: parent.focus ? Colour.text : Colour.menuText
    font.pointSize: FontStyle.menuSize
  }
}
