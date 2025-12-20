import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Controls.Material 2.15
import QtQuick.Layouts 1.15
import QtQuick.Window 2.15

ApplicationWindow {
    id: window
    visible: true
    width: 1280
    height: 800
    title: "HX711 Load Cell"
    color: "#0c0f17"
    Material.theme: Material.Dark
    Material.accent: "#0A84FF"

    // Typography / sizing for touch
    property int pad: 22
    property int gap: 16
    property int btnHeight: 74
    property int btnFont: 22
    property bool readingActive: false
    property bool settingsVisible: false
    property bool calWizardVisible: false
    property int calStep: 1
    property string calWeightText: "1000"
    property bool numpadVisible: false
    property string numpadLabel: ""
    property var numpadTargetField: null
    property string numpadBuffer: ""
    property var languageOptions: []
    property bool fullscreenState: false
    property string langCode: ""

    property var cfg: ({})
    property var reading: ({})
    property var cal: ({})
    property string statusText: ""

    Component.onCompleted: {
        cfg = Object.assign({}, controller.config)
        reading = controller.reading
        cal = controller.calStatus
        statusText = controller.statusText
        readingActive = controller ? controller.isReading : false
        languageOptions = controller ? controller.languagesList : []
        langCode = controller ? controller.language : ""
        fullscreenState = cfg.fullscreen === true
        window.visibility = fullscreenState ? Window.FullScreen : Window.Windowed
    }

    Connections {
        target: controller
        function onConfigChanged() {
            cfg = Object.assign({}, controller.config)
            fullscreenState = cfg.fullscreen === true
            window.visibility = fullscreenState ? Window.FullScreen : Window.Windowed
        }
        function onReadingChanged() { reading = controller.reading }
        function onCalStatusChanged() { cal = controller.calStatus }
        function onStatusChanged() { statusText = controller.statusText }
        function onErrorOccurred(msg) { statusText = msg }
        function onReadingStateChanged() { readingActive = controller ? controller.isReading : false }
        function onLanguagesChanged() { languageOptions = controller ? controller.languagesList : [] }
        function onLanguageChanged() { langCode = controller ? controller.language : "" }
    }

    // Simple translate helper
    function tr(key, fallback) {
        const _lang = langCode
        if (controller && controller.tr) {
            return controller.tr(key, fallback || key)
        }
        return fallback || key
    }

    // Floating calibration/status toast
    Rectangle {
        id: calToast
        width: Math.min(window.width * 0.7, 520)
        height: 44
        radius: 12
        color: cal.level === "good" ? "#34c759" : cal.level === "warn" ? "#ffcc00" : "#ff3b30"
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.top: parent.top
        anchors.topMargin: pad
        visible: true

        RowLayout {
            anchors.fill: parent
            anchors.margins: 12
            Layout.alignment: Qt.AlignCenter
            spacing: 8
            Label {
                text: cal.text || "Calibration"
                color: "#0c0f17"
                font.pixelSize: 16
                font.bold: true
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
                wrapMode: Label.WordWrap
                Layout.alignment: Qt.AlignCenter
            }
        }
    }

    footer: Rectangle {
        id: footer
        height: 52
        color: "#111522"
        Label {
            anchors.verticalCenter: parent.verticalCenter
            anchors.left: parent.left
            anchors.leftMargin: pad
            text: statusText
            color: "#c9ced9"
            font.pixelSize: 16
            elide: Label.ElideRight
        }
    }

    Rectangle {
        id: body
        anchors.fill: parent
        anchors.margins: pad
        anchors.topMargin: calToast.visible ? (calToast.height + pad * 2) : (pad * 2)
        anchors.bottomMargin: footer.height + pad
        radius: 16
        color: "#111522"
        border.color: "#1d2536"
        border.width: 1

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: pad
            spacing: gap

            // Primary metric card
            Rectangle {
                radius: 14
                color: "#151b29"
                border.color: "#1f2a3d"
                Layout.fillWidth: true
                Layout.preferredHeight: 320

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: pad
                    spacing: gap

                    Label {
                        text: (reading.grams !== undefined && reading.grams !== null)
                              ? reading.grams.toFixed(Math.max(cfg.decimals || 0, 0)) + " g"
                              : "—"
                        font.pixelSize: 112
                        font.bold: true
                        color: "#eef0f6"
                        horizontalAlignment: Label.AlignHCenter
                        Layout.alignment: Qt.AlignHCenter
                    }

                    GridLayout {
                        id: metricGrid
                        Layout.alignment: Qt.AlignHCenter
                        columns: 2
                        columnSpacing: gap * 1.5
                        rowSpacing: gap / 2

                        Label {
                            text: "Newtons"
                            font.pixelSize: 18
                            color: "#8f96a6"
                        }
                        Label {
                            text: (reading.newtons !== undefined && reading.newtons !== null)
                                  ? reading.newtons.toFixed(3) + " N"
                                  : "—"
                            font.pixelSize: 24
                            color: "#aeb4c3"
                        }

                        Label {
                            text: "Rate"
                            font.pixelSize: 18
                            color: "#8f96a6"
                        }
                        Label {
                            text: (reading.hz !== undefined && reading.hz !== null)
                                  ? reading.hz.toFixed(2) + " Hz"
                                  : "— Hz"
                            font.pixelSize: 22
                            color: "#aeb4c3"
                        }

                        Label {
                            text: "Raw"
                            font.pixelSize: 18
                            color: "#8f96a6"
                        }
                        Label {
                            text: (reading.raw !== undefined && reading.raw !== null) ? reading.raw : "—"
                            font.pixelSize: 22
                            color: "#aeb4c3"
                        }
                    }
                }
            }

            // Actions row
            RowLayout {
                Layout.fillWidth: true
                spacing: gap

                Button {
                    id: startStopBtn
                    text: readingActive ? tr("btn_stop", "Stop") : tr("btn_start", "Start")
                    highlighted: !readingActive
                    font.pixelSize: btnFont
                    implicitHeight: btnHeight
                    Layout.fillWidth: true
                    onClicked: {
                        if (!controller) return
                        if (readingActive) {
                            controller.stop()
                        } else {
                            controller.applyAndStart(cfg)
                        }
                    }
                }
                Button {
                    text: tr("btn_tare", "Tare")
                    font.pixelSize: btnFont
                    implicitHeight: btnHeight
                    Layout.fillWidth: true
                    onClicked: controller.tare()
                }
                Button {
                    text: tr("btn_calibrate", "Calibrate")
                    font.pixelSize: btnFont
                    implicitHeight: btnHeight
                    Layout.fillWidth: true
                    onClicked: {
                        calStep = 1
                        calWizardVisible = true
                    }
                }
                Button {
                    text: tr("btn_settings", "Settings")
                    font.pixelSize: btnFont
                    implicitHeight: btnHeight
                    Layout.fillWidth: true
                    onClicked: settingsVisible = true
                }
            }
        }
    }

    // Fullscreen settings overlay
    Rectangle {
        id: settingsOverlay
        visible: settingsVisible
        anchors.fill: parent
        color: "#0a0d15cc"
        z: 10

        Rectangle {
            anchors.centerIn: parent
            width: Math.min(window.width * 0.9, 900)
            height: Math.min(window.height * 0.9, 700)
            radius: 16
            color: "#0f1422"
            border.color: "#1d2536"
            border.width: 1

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: pad
                spacing: gap

                RowLayout {
                    Layout.fillWidth: true
                    Label {
                        text: tr("label_settings", "Settings")
                        font.pixelSize: 26
                        font.bold: true
                        color: "#e8ebf2"
                        Layout.alignment: Qt.AlignVCenter
                    }
                    Item { Layout.fillWidth: true }
                    Button {
                        text: tr("btn_cancel", "Close")
                        font.pixelSize: 20
                        implicitHeight: btnHeight
                        onClicked: settingsVisible = false
                    }
                }

                Flickable {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    contentWidth: parent.width
                    contentHeight: contentCol.implicitHeight
                    clip: true

                    ColumnLayout {
                        id: contentCol
                        width: parent.width
                        spacing: gap

                        GridLayout {
                            id: gridInputs
                            columns: 2
                            columnSpacing: gap
                            rowSpacing: gap
                            Layout.fillWidth: true

                        Repeater {
                            model: [
                                {labelKey: "label_dout", fallback: "DOUT pin", key: "dout", digits: true, allowDecimal: false},
                                {labelKey: "label_sck", fallback: "SCK pin", key: "sck", digits: true, allowDecimal: false},
                                {labelKey: "label_gain", fallback: "Gain (32/64/128)", key: "gain", digits: true, allowDecimal: false},
                                {labelKey: "label_scale", fallback: "Scale", key: "scale", digits: true, allowDecimal: true},
                                {labelKey: "label_offset", fallback: "Offset", key: "offset", digits: true, allowDecimal: true},
                                {labelKey: "label_samples", fallback: "Samples", key: "samples", digits: true, allowDecimal: false},
                                {labelKey: "label_interval", fallback: "Interval (s)", key: "interval", digits: true, allowDecimal: true},
                                {labelKey: "label_decimals", fallback: "Decimals", key: "decimals", digits: true, allowDecimal: false}
                            ]

                                delegate: ColumnLayout {
                                    spacing: 6
                                    Layout.fillWidth: true
                                    Label {
                                    text: tr(modelData.labelKey, modelData.fallback)
                                    font.pixelSize: 16
                                    color: "#c9ced9"
                                }
                                    TextField {
                                        placeholderText: ""
                                        text: cfg[modelData.key] !== undefined ? cfg[modelData.key] : ""
                                        inputMethodHints: modelData.allowDecimal ? Qt.ImhFormattedNumbersOnly
                                                              : (modelData.digits ? Qt.ImhDigitsOnly : Qt.ImhNone)
                                        readOnly: modelData.digits || modelData.allowDecimal
                                        Layout.fillWidth: true
                                        onPressed: {
                                            if (modelData.digits || modelData.allowDecimal) {
                                                numpadTargetField = this
                                                numpadLabel = tr(modelData.labelKey, modelData.fallback)
                                                numpadBuffer = text
                                                numpadVisible = true
                                            }
                                        }
                                        onTextChanged: {
                                            cfg[modelData.key] = text
                                        }
                                        font.pixelSize: 20
                                        implicitHeight: 62
                                        background: Rectangle {
                                            radius: 12
                                            color: "#151b29"
                                            border.color: "#243149"
                                        }
                                    }
                                }
                            }
                        }

                        // Rolling window toggle
                        ColumnLayout {
                            spacing: 6
                            Layout.fillWidth: true
                            Label {
                                text: tr("label_rolling_window", "Rolling window")
                                font.pixelSize: 16
                                color: "#c9ced9"
                            }
                            CheckBox {
                                text: tr("label_rolling_window_on", "Enable")
                                checked: !!cfg.rolling_window
                                font.pixelSize: 18
                                onCheckedChanged: cfg.rolling_window = checked
                            }
                        }

                        // Language selector from controller languages
                        ColumnLayout {
                            spacing: 6
                            Layout.fillWidth: true
                            Label {
                                text: tr("label_language", "Language")
                                font.pixelSize: 16
                                color: "#c9ced9"
                            }
                            ComboBox {
                                model: languageOptions
                                implicitHeight: 56
                                font.pixelSize: 18
                                Layout.fillWidth: true
                                currentIndex: Math.max(0, languageOptions.indexOf(cfg.language || "en"))
                                onActivated: (index) => {
                                    if (index >= 0 && index < languageOptions.length) {
                                        cfg.language = languageOptions[index]
                                        controller.setLanguage(cfg.language)
                                    }
                                }
                            }
                        }

                        // Fullscreen toggle
                        ColumnLayout {
                            spacing: 6
                            Layout.fillWidth: true
                            Label {
                                text: "Fullscreen (kiosk)"
                                font.pixelSize: 16
                                color: "#c9ced9"
                            }
                            CheckBox {
                                text: "Enable fullscreen"
                                checked: fullscreenState
                                font.pixelSize: 18
                                onClicked: {
                                    fullscreenState = !fullscreenState
                                    cfg.fullscreen = fullscreenState
                                    window.visibility = fullscreenState ? Window.FullScreen : Window.Windowed
                                    controller.updateConfig(cfg)
                                }
                            }
                        }
                    }
                }

                RowLayout {
                    spacing: gap
                    Layout.fillWidth: true
                    Button {
                        text: tr("btn_save", "Save")
                        font.pixelSize: 20
                        implicitHeight: btnHeight
                        Layout.fillWidth: true
                        onClicked: {
                            controller.updateConfig(cfg)
                            settingsVisible = false
                        }
                    }
                }
            }
        }
    }

    // Calibration wizard (step-by-step with brief loading)
    Rectangle {
        id: calWizard
        visible: calWizardVisible
        anchors.fill: parent
        color: "#0a0d15cc"
        z: 11

        Rectangle {
            anchors.centerIn: parent
            width: Math.min(window.width * 0.85, 820)
            height: Math.min(window.height * 0.7, 560)
            radius: 16
            color: "#0f1422"
            border.color: "#1d2536"
            border.width: 1

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: pad
                spacing: gap

                RowLayout {
                    Layout.fillWidth: true
                    spacing: gap
                    Label {
                        text: calStep === 1
                              ? tr("cal_title", "Calibration")
                              : calStep === 3
                                ? tr("label_known_weight", "Known weight (g)")
                                : tr("cal_title", "Calibration")
                        font.pixelSize: 24
                        font.bold: true
                        color: "#e8ebf2"
                        Layout.alignment: Qt.AlignVCenter
                    }
                    Item { Layout.fillWidth: true }
                    Button {
                        text: tr("btn_cancel", "Cancel")
                        font.pixelSize: 18
                        implicitHeight: btnHeight
                        onClicked: {
                            calTimer1.stop()
                            calTimer2.stop()
                            calWizardVisible = false
                            calStep = 1
                        }
                    }
                }

                Rectangle {
                    radius: 12
                    color: "#151b29"
                    border.color: "#1f2a3d"
                    Layout.fillWidth: true
                    Layout.fillHeight: true

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: pad
                        spacing: gap

                        Label {
                            visible: calStep === 1
                            text: tr("cal_step_remove_all", "Step 1: Remove all weight, then tap Next.")
                            wrapMode: Label.WordWrap
                            font.pixelSize: 18
                            color: "#e8ebf2"
                        }

                        ColumnLayout {
                            visible: calStep === 2
                            spacing: 10
                            Layout.alignment: Qt.AlignHCenter
                            Label {
                                text: tr("status_calibrating_clear", "Preparing…")
                                wrapMode: Label.WordWrap
                                font.pixelSize: 18
                                color: "#e8ebf2"
                                horizontalAlignment: Text.AlignHCenter
                                Layout.alignment: Qt.AlignHCenter
                            }
                            BusyIndicator {
                                running: calStep === 2
                                width: 48
                                height: 48
                                Layout.alignment: Qt.AlignHCenter
                            }
                        }

                        ColumnLayout {
                            visible: calStep === 3
                            spacing: 10
                            Label {
                                text: tr("cal_prompt_place_weight", "Place the known weight, then continue.")
                                wrapMode: Label.WordWrap
                                font.pixelSize: 18
                                color: "#e8ebf2"
                            }
                            Label {
                                text: tr("label_known_weight", "Known weight (g)")
                                font.pixelSize: 16
                                color: "#c9ced9"
                            }
                            TextField {
                                text: calWeightText
                                inputMethodHints: Qt.ImhDigitsOnly
                                font.pixelSize: 20
                                implicitHeight: 62
                                onTextChanged: calWeightText = text
                                background: Rectangle {
                                    radius: 12
                                    color: "#151b29"
                                    border.color: "#243149"
                                }
                            }
                        }

                        ColumnLayout {
                            visible: calStep === 4
                            spacing: 10
                            Layout.alignment: Qt.AlignHCenter
                            Label {
                                text: tr("cal_title", "Calibrating…")
                                wrapMode: Label.WordWrap
                                font.pixelSize: 18
                                color: "#e8ebf2"
                                horizontalAlignment: Text.AlignHCenter
                                Layout.alignment: Qt.AlignHCenter
                            }
                            BusyIndicator {
                                running: calStep === 4
                                width: 48
                                height: 48
                                Layout.alignment: Qt.AlignHCenter
                            }
                        }

                        ColumnLayout {
                            visible: calStep === 5
                            spacing: 10
                            Layout.alignment: Qt.AlignHCenter
                            Label {
                                text: tr("status_calibration_done", "Calibration done")
                                wrapMode: Label.WordWrap
                                font.pixelSize: 18
                                color: "#e8ebf2"
                                horizontalAlignment: Text.AlignHCenter
                                Layout.alignment: Qt.AlignHCenter
                            }
                        }
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: gap
                    Button {
                        text: calStep === 1 ? tr("btn_cancel", "Cancel")
                             : calStep === 5 ? tr("btn_ok", "OK")
                             : tr("btn_back", "Back")
                        font.pixelSize: 18
                        implicitHeight: btnHeight
                        Layout.fillWidth: true
                        onClicked: {
                            if (calStep === 1) {
                                calWizardVisible = false
                            } else if (calStep === 2) {
                                calTimer1.stop()
                                calStep = 1
                            } else if (calStep === 3) {
                                calStep = 1
                            } else if (calStep === 4) {
                                calTimer2.stop()
                                calStep = 3
                            } else {
                                calWizardVisible = false
                            }
                        }
                    }
                    Button {
                        text: calStep === 1 ? tr("btn_next", "Next")
                             : calStep === 3 ? tr("btn_start", "Start")
                             : tr("btn_ok", "OK")
                        highlighted: true
                        font.pixelSize: 18
                        implicitHeight: btnHeight
                        Layout.fillWidth: true
                        enabled: calStep !== 4
                        onClicked: {
                            if (calStep === 1) {
                                calStep = 2
                                calTimer1.restart()
                            } else if (calStep === 3) {
                                const w = parseFloat(calWeightText)
                                if (isNaN(w) || w <= 0) {
                                    statusText = tr("invalid_weight", "Enter a valid weight (grams)")
                                    return
                                }
                                calStep = 4
                                calTimer2.weightVal = w
                                calTimer2.restart()
                            } else if (calStep === 5) {
                                calWizardVisible = false
                            }
                        }
                    }
                }
            }
        }
    }

    // Timers for calibration steps
    Timer {
        id: calTimer1
        interval: 1000
        running: false
        repeat: false
        onTriggered: calStep = 3
    }
    Timer {
        id: calTimer2
        interval: 1000
        running: false
        repeat: false
        property real weightVal: 0
        onTriggered: {
            controller.calibrateWithWeight(weightVal)
            calStep = 5
        }
    }

    // On-screen numpad for numeric fields
    Rectangle {
        id: numpadOverlay
        visible: numpadVisible
        anchors.fill: parent
        color: "#0a0d15cc"
        z: 12

        // Swallow background clicks so underlying inputs aren't triggered
        MouseArea {
            anchors.fill: parent
            acceptedButtons: Qt.AllButtons
            propagateComposedEvents: true
        }

        Rectangle {
            anchors.centerIn: parent
            width: 420
            height: 540
            radius: 16
            color: "#0f1422"
            border.color: "#1d2536"
            border.width: 1

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: pad
                spacing: gap

                Label {
                    text: numpadLabel || "Enter value"
                    font.pixelSize: 20
                    font.bold: true
                    color: "#e8ebf2"
                }

                TextField {
                    text: numpadBuffer
                    readOnly: true
                    font.pixelSize: 24
                    implicitHeight: 60
                    horizontalAlignment: Text.AlignRight
                    background: Rectangle { radius: 10; color: "#151b29"; border.color: "#243149" }
                }

                GridLayout {
                    columns: 3
                    columnSpacing: gap
                    rowSpacing: gap

                    Repeater {
                        model: [
                            "7","8","9",
                            "4","5","6",
                            "1","2","3",
                            ".","0","⌫"
                        ]
                        delegate: Button {
                            text: modelData
                            font.pixelSize: 22
                            implicitHeight: 64
                            onClicked: {
                                if (modelData === "⌫") {
                                    numpadBuffer = numpadBuffer.slice(0, -1)
                                } else {
                                    numpadBuffer += modelData
                                }
                            }
                        }
                    }
                }

                RowLayout {
                    spacing: gap
                    Button {
                        text: "Cancel"
                        implicitHeight: btnHeight
                        Layout.fillWidth: true
                        onClicked: {
                            numpadVisible = false
                        }
                    }
                    Button {
                        text: "OK"
                        highlighted: true
                        implicitHeight: btnHeight
                        Layout.fillWidth: true
                        onClicked: {
                            if (numpadTargetField) {
                                numpadTargetField.text = numpadBuffer.length ? numpadBuffer : "0"
                                // propagate to cfg for digits fields
                                if (typeof numpadTargetField.editingFinished === "function") {
                                    numpadTargetField.editingFinished()
                                }
                            }
                            numpadVisible = false
                        }
                    }
                }
            }
        }
    }
}

