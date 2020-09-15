# normal imports
import numpy as np
from qgis.gui import *
from qgis.PyQt.QtWidgets import QAction, QMainWindow
from qgis.PyQt.QtCore import Qt

AZIMUTH = 0.0            # degrees [0 .. 360]
OFFSET_INLINE = 6000     # meters
OFFSET_CROSSLINE = 3000  # meters

class CalcMap:

    def __init__(self, azimuth):
        self.azimuth = azimuth

    def offset_transformation(self, inline_offset, crossline_offset):
        '''  transformation from inline_offset, crossline offset to delta_easting,
        delta_northing. self.azimuth angle of prospect in degrees

        Arguments:
            :inline_offset: inline offset in meters, negative along azimuth vector (float)
            :crossline_offset: crossline offset in meters, positive counterclockwise (float)

        :Returns:
            :dx: (m) change in x direction (float)
            :dy: (m) change in y direction (float)
        '''
        azimuth = (np.pi / 180 * self.azimuth)  # converted to radians
        dx_crossline = crossline_offset * np.cos(azimuth)
        dy_crossline = -crossline_offset * np.sin(azimuth)
        dx_inline = -inline_offset * np.sin(azimuth)
        dy_inline = -inline_offset * np.cos(azimuth)

        return dx_inline + dx_crossline, dy_inline + dy_crossline

    def add_patch(self, x, y):
        ''' create 4 corner coordinates beased inline and crossline distance

        '''
        p1 = tuple([x + self.offset_transformation(OFFSET_INLINE, OFFSET_CROSSLINE)[0],
                    y + self.offset_transformation(OFFSET_INLINE, OFFSET_CROSSLINE)[1]])
        p2 = tuple([x + self.offset_transformation(OFFSET_INLINE, -OFFSET_CROSSLINE)[0],
                    y + self.offset_transformation(OFFSET_INLINE, -OFFSET_CROSSLINE)[1]])
        p3 = tuple([x + self.offset_transformation(-OFFSET_INLINE, -OFFSET_CROSSLINE)[0],
                    y + self.offset_transformation(-OFFSET_INLINE, -OFFSET_CROSSLINE)[1]])
        p4 = tuple([x + self.offset_transformation(-OFFSET_INLINE, OFFSET_CROSSLINE)[0],
                    y + self.offset_transformation(-OFFSET_INLINE, OFFSET_CROSSLINE)[1]])

        return p1, p2, p3, p4

class ActiveSpreadMapTool(QgsMapToolEmitPoint):
    def __init__(self, canvas):
        self.canvas = canvas
        self.cm = CalcMap(AZIMUTH);
        QgsMapToolEmitPoint.__init__(self, self.canvas)

        self.rubber_band = None
        self.marker = None

    def create_spread(self):
        self.rubber_band = QgsRubberBand(self.canvas, True)
        self.rubber_band.setColor(Qt.blue)
        self.rubber_band.setFillColor(Qt.transparent)
        self.rubber_band.setWidth(2)
        self.rubber_band.reset(QgsWkbTypes.PolygonGeometry)

        self.marker = QgsVertexMarker(self.canvas)
        self.marker.setColor(Qt.red)
        self.marker.setIconSize(3)
        self.marker.setIconType(QgsVertexMarker.ICON_CROSS)  # or ICON_BOX, ICON_X
        self.marker.setPenWidth(3)

    def reset(self):
        self.canvas.scene().removeItem(self.marker)
        self.canvas.scene().removeItem(self.rubber_band)
        #self.rubber_band.reset(True)

    def canvasPressEvent(self, e):
        point = self.toMapCoordinates(e.pos())
        print(f'x: {point.x():.2f}, y: {point.y():.2f}')
        point = QgsPoint(point.x(), point.y())

        self.reset()
        self.create_spread()
        self.show_rect(point)
        self.show_marker(point)

    def show_marker(self, point):
        self.marker.setCenter(QgsPointXY(point.x(), point.y()))

    def show_rect(self, point):
        p1, p2, p3, p4 = self.cm.add_patch(point.x(), point.y())

        point1 = QgsPointXY(p1[0], p1[1])
        point2 = QgsPointXY(p2[0], p2[1])
        point3 = QgsPointXY(p3[0], p3[1])
        point4 = QgsPointXY(p4[0], p4[1])

        self.rubber_band.addPoint(point1, False)
        self.rubber_band.addPoint(point2, False)
        self.rubber_band.addPoint(point3, False)
        self.rubber_band.addPoint(point4, True)    # true to update canvas
        self.rubber_band.show()

    def deactivate(self):
        print('Deactivate spread tool ...')
        self.reset()
        QgsMapTool.deactivate(self)
        self.deactivated.emit()

canvas = iface.mapCanvas()
spread = ActiveSpreadMapTool(iface.mapCanvas())
canvas.setMapTool(spread)
