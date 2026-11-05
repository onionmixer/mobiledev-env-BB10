import bb.cascades 1.4

Page {
    Container {
        topPadding: ui.du(4)
        leftPadding: ui.du(3)
        rightPadding: ui.du(3)
        Label {
            text: "Hello, BlackBerry 10"
            textStyle.base: SystemDefaults.TextStyles.BigText
            multiline: true
        }
        Label {
            text: app.message
            multiline: true
        }
        Button {
            text: "Count"
            onClicked: app.increment()
        }
    }
}
