import sys
import json
from PySide6.QtCore import QObject, Slot, QUrl
from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QMessageBox, QLabel, QWidget
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebChannel import QWebChannel

# The four corners of the clickable area (lat, lng)
FRASS2 = [
    (14.609079413700655, 120.99226983635191),   # WEST
    (14.60916076765254, 120.9923572487653),     # NORTH
    (14.609062787880237, 120.99245179663252),   # EAST
    (14.60898622087547, 120.99235322545181),    # SOUTH
]

HTML = """
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
  <script src="qrc:///qtwebchannel/qwebchannel.js"></script>
  <style>html, body, #map { height: 100%; margin: 0; }</style>
</head>
<body>
<div id="map"></div>
<script>
  var map = L.map('map').setView([14.60908, 120.99236], 19);
  L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19, attribution: '&copy; OpenStreetMap contributors'
  }).addTo(map);

  // The interactive area
  var area = L.polygon(%`FRASS2%, {color: 'blue', fillOpacity: 0.3}).addTo(map);
  map.fitBounds(area.getBounds(), {maxZoom: 20});

  // Leaflet -> Python: tell Python when the area is clicked
  var bridge = null;
  new QWebChannel(qt.webChannelTransport, function (channel) {
    bridge = channel.objects.bridge;
  });
  area.on('click', function () {
    if (bridge) bridge.areaClicked("Area 1");
  });

  // Python -> Leaflet: change the area's colour
  function setColor(color) {
    area.setStyle({color: color, fillColor: color});
  }
</script>
</body>
</html>
""".replace("%`FRASS2%", json.dumps(FRASS2))


class Bridge(QObject):
    def __init__(self, window):
        super().__init__()
        self.window = window

    @Slot(str)
    def areaClicked(self, name):
        # This is where you would query your database
        QMessageBox.information(self.window, "Area clicked", f"Clicked: {name}")
        # Python -> JS: turn the area green after the click
        self.window.view.page().runJavaScript("setColor('green');")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PySide6 + Leaflet")
        self.resize(900, 650)

        layout = QVBoxLayout()

        map_label = QLabel("Map:")
        map_label.setFixedHeight(40)
        self.setMenuWidget(map_label)
        # layout.addWidget(map_label)

        self.view = QWebEngineView()
        self.setCentralWidget(self.view)
        # layout.addWidget(self.view)

        # Connect Python and JavaScript
        self.channel = QWebChannel()
        self.bridge = Bridge(self)
        self.channel.registerObject("bridge", self.bridge)
        self.view.page().setWebChannel(self.channel)

        # baseUrl gives the page a real origin so map tiles load
        self.view.setHtml(HTML, QUrl("https://localhost/"))


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())