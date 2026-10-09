import sys
import json
from PySide6.QtCore import QObject, Slot, QUrl
from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QMessageBox, QLabel, QWidget
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebChannel import QWebChannel

# Right1 = [
#     (15.671705804283203, 120.89280010517078),
#     (15.671700639286055, 120.89283162112696),
#     (15.671638659310162, 120.89281888063405),
#     (15.671645761183346, 120.89278870578238),
# ]
# Right2 = [
#     (15.671700524681192, 120.89283495354036),
#     (15.671694714059244, 120.89286110507848),
#     (15.67163337970641, 120.89285104679456),
#     (15.671637253455568, 120.89282221304742),
# ]
# Right3 = [
#     (15.671696650933242, 120.89285976397396),
#     (15.67168954906183, 120.8928919504824),
#     (15.671627569082567, 120.89288323330304),
#     (15.67163337970641, 120.8928523878991),
# ]

BASE = [
    (15.671705804283203, 120.89280010517078),
    (15.671700639286055, 120.89283162112696),
    (15.671638659310162, 120.89281888063405),
    (15.671645761183346, 120.89278870578238),
]

def shifted(coords, dlat, dlng):
    """Copy of a polygon moved by dlat/dlng degrees (placeholder areas for the demo)."""
    return [(lat + dlat, lng + dlng) for lat, lng in coords]
 
 
# Every area has a unique ID (the key) and its list of corners.
# Replace the shifted copies with your real coordinates.
AREAS = {
    "A1": BASE,
    "A2": shifted(BASE, -0.000005, 0.000036),
    "A3": shifted(BASE, -0.000010, 0.000072),
    "A4": shifted(BASE, -0.000015, 0.000108),
}
 
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
  var AREAS = %AREAS%;          // {"A1": [[lat, lng], ...], "A2": ...}
  var polygons = {};            // id -> Leaflet polygon, so we can find them later
 
  var map = L.map('map').setView([15.67178, 120.89277], 19);
  L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxNativeZoom: 19,   // highest zoom the server actually has
    maxZoom: 22,         // how far the user may zoom (tiles get upscaled)
    attribution: '&copy; OpenStreetMap contributors'
  }).addTo(map);
 
  var bridge = null;
  new QWebChannel(qt.webChannelTransport, function (channel) {
    bridge = channel.objects.bridge;
  });
 
  // Create one polygon per area
  for (var id in AREAS) {
    (function (id) {                       // closure so each click handler keeps its own id
      var poly = L.polygon(AREAS[id], {color: 'blue', fillOpacity: 0.3}).addTo(map);
      poly.bindTooltip(id);                // label shown on hover
      poly.on('click', function () {
        if (bridge) bridge.areaClicked(id);
      });
      polygons[id] = poly;
    })(id);
  }
 
  // Zoom to show all areas
  map.fitBounds(L.featureGroup(Object.values(polygons)).getBounds(), {maxZoom: 20});
 
  // Python -> Leaflet: recolour one area by its id
  function setColor(id, color) {
    if (polygons[id]) polygons[id].setStyle({color: color, fillColor: color});
  }
</script>
</body>
</html>
""".replace("%AREAS%", json.dumps(AREAS))
 
 
class Bridge(QObject):
    def __init__(self, window):
        super().__init__()
        self.window = window
 
    @Slot(str)
    def areaClicked(self, area_id):
        # This is where you would query your database using area_id
        QMessageBox.information(self.window, "Area clicked", f"You clicked area: {area_id}")
        self.window.view.page().runJavaScript(f"setColor({json.dumps(area_id)}, 'green');")
 
 
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PySide6 + Leaflet (multiple areas)")
        self.resize(900, 650)
 
        self.view = QWebEngineView()
        self.setCentralWidget(self.view)
 
        self.channel = QWebChannel()
        self.bridge = Bridge(self)
        self.channel.registerObject("bridge", self.bridge)
        self.view.page().setWebChannel(self.channel)
 
        self.view.setHtml(HTML, QUrl("https://localhost/"))
 
 
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())