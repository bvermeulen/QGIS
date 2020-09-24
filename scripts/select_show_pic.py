# Note: to import libraries use the OSGeo4W shell, and run
# python-qgis -m pip install
import sys
import os
# if using Linux then add path to site-packages, add path to scripts for any system
if os.name == 'posix':
    import_path = os.path.expanduser('~/Python/QGIS/venv/lib/python3.8/site-packages')
    sys.path.insert(0, import_path)
    import_path = os.path.expanduser('~/Python/QGIS/scripts')
    sys.path.append(import_path)

elif os.name == 'nt':
    sys.path.append('D:\\OneDrive\\QGIS\\scripts')

else:
    pass

from qgis.gui import *
from qgis.PyQt.QtWidgets import QAction, QMainWindow
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QImage, QPixmap

# add scripts folder to the path to import modules
from pyqt_picture import PictureShow


pictures_layer = 'picture year'
d = QgsDistanceArea()
d.setEllipsoid('WGS84')


class PicLayer():
    def __init__(self):
        layer = QgsProject.instance().mapLayersByName(pictures_layer)[0]
        self._features = list(layer.getFeatures(QgsFeatureRequest()))

        self.tr_wgs = QgsCoordinateTransform(
            QgsCoordinateReferenceSystem(QgsProject.instance().crs().authid()),
            QgsCoordinateReferenceSystem('EPSG:4326'),
            QgsProject.instance().transformContext()
        )

    @property
    def nearest_feature(self):
        return self._nearest_feature

    def select_nearest_picture(self, point: QgsPointXY) -> QgsPoint:
        ''' Calculates the distance from point and all pictures and selects the
            one with the minimum distance. Returns point either of closest
            picture or original point if not picture is found
                argument: point: QgsPointXY
                returns: point: QgsPointXY
        '''

        point = self.tr_wgs.transform(point)
        print(f'---> x = {point.x()}, y = {point.y()}')
        min_distance = float('inf')
        self._nearest_feature = None
        for feature in self._features:
            distance = d.measureLine(feature.geometry().asPoint(), point)
            if distance < min_distance:
                min_distance = distance
                self._nearest_feature = feature


        if self._nearest_feature:
            point = self._nearest_feature.geometry().asPoint()
            return self.tr_wgs.transform(point, QgsCoordinateTransform.ReverseTransform)

        else:
            return self.tr_wgs.transform(point, QgsCoordinateTransform.ReverseTransform)


class SelectPicMapTool(QgsMapToolEmitPoint):
    def __init__(self, canvas):
        self.canvas = canvas
        QgsMapToolEmitPoint.__init__(self, self.canvas)
        self.pic_layer = PicLayer()
        self.marker = None
        self.picshow = PictureShow()

    def reset(self):
        self.canvas.scene().removeItem(self.marker)

    def canvasPressEvent(self, e):
        point = self.toMapCoordinates(e.pos())
        point = QgsPointXY(point.x(), point.y())
        print(f'x={point.x()}, y={point.y()}')

        self.reset()
        point = self.pic_layer.select_nearest_picture(point)
        print(
            f'picture id: {self.pic_layer.nearest_feature.attributes()[2]} - '
            f'year taken: {self.pic_layer.nearest_feature.attributes()[3]:.0f} - '
            f'x: {point.x():.6f}, y: {point.y():.6f}'
        )
        self.show_marker(point)
        self.show_picture()

    def show_marker(self, point):
        self.marker = QgsVertexMarker(self.canvas)
        self.marker.setColor(Qt.yellow)
        self.marker.setIconSize(6)
        self.marker.setIconType(QgsVertexMarker.ICON_CROSS)  # or ICON_BOX, ICON_X
        self.marker.setPenWidth(3)
        self.marker.setCenter(point)
        self.marker.show()

    def show_picture(self):
        self.picshow.cntr_select_pic(self.pic_layer.nearest_feature.attributes()[2])
        self.picshow.show_picture()

    def deactivate(self):
        print('Deactivate select picture ...')
        self.reset()
        QgsMapTool.deactivate(self)
        self.deactivated.emit()

canvas = iface.mapCanvas()
select_pic = SelectPicMapTool(canvas)
canvas.setMapTool(select_pic)

