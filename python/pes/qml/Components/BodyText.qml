import QtQuick 2.7
import "../Style/" 1.0

Text {
	text: "null"
	padding: 10
	font.pointSize: FontStyle.bodySize
	font.bold: true
	font.family: FontStyle.font
	color: Colour.text
	wrapMode: Text.Wrap
	width: parent.width // must set width for wrapping to work
}
