import QtQuick 2.7
import "../Style/" 1.0

Rectangle {
	id: menuDelegateRect
	height: 50
	width: parent.width
	color: focus ? Colour.menuFocus : Colour.menuBg
	property alias text: menuDelegateText.text

	//Keys.onReturnPressed: {
	//	parent.foo(event);
	//}

	Text {
		id: menuDelegateText
		text: name
		color: parent.focus ? Colour.text : Colour.menuText
		font.pointSize: FontStyle.menuSize
	}
}
