import sys
import os
# if using Linux then add path to site-packages, add path to scripts for any system
if os.name == 'posix':
    import_path = os.path.expanduser(
        '~/Python/QGIS/venv/lib/python3.8/site-packages')
    sys.path.insert(0, import_path)
    import_path = os.path.expanduser('~/Python/QGIS/scripts')
    sys.path.append(import_path)

elif os.name == 'nt':
    sys.path.append('D:\\OneDrive\\QGIS\\scripts')

else:
    pass

from qgis.gui import (
    QgsMapToolEmitPoint, QgsMapToolEmitPoint, QgsVertexMarker,
)
from qgis.PyQt.QtWidgets import QAction, QMainWindow
from qgis.PyQt.QtCore import Qt

from pyqt_picture import Mode, PictureShow


class SelectRectanglePicLayer:
    def __init__(self):
        pictures_layer = 'picture year'
        self.layer = QgsProject.instance().mapLayersByName(pictures_layer)[0]
        self.tr_wgs = QgsCoordinateTransform(
            QgsCoordinateReferenceSystem(QgsProject.instance().crs().authid()),
            QgsCoordinateReferenceSystem('EPSG:4326'),
            QgsProject.instance().transformContext()
        )

    def select_pics_in_rectangle(self, start_point, end_point):
        if start_point is None or end_point is None:
            return []

        elif (start_point.x() == end_point.x() or
            start_point.y() == end_point.y()):
            return []

        start_point = self.tr_wgs.transform(start_point)
        end_point = self.tr_wgs.transform(end_point)

        select_area = QgsRectangle(start_point, end_point)
        self.selection = QgsFeatureRequest()
        self.selection.setFilterRect(select_area)

        picture_ids = []
        for feature in self.layer.getFeatures(self.selection):
            picture_ids.append(feature.attributes()[2])

        return picture_ids

    def get_mappoint(self, pic_id):
        for feature in self.layer.getFeatures(self.selection):
            if pic_id == feature.attributes()[2]:
                return self.tr_wgs.transform(
                    feature.geometry().asPoint(), QgsCoordinateTransform.ReverseTransform)

        return None


class SelectRectanglePicMapTool(QgsMapToolEmitPoint):
    def __init__(self, canvas):
        self.canvas = canvas
        QgsMapToolEmitPoint.__init__(self, self.canvas)

        self.select_rect_pic = SelectRectanglePicLayer()
        self.pic_show = PictureShow(mode=Mode.Multi)

        self.rubberBand = QgsRubberBand(self.canvas, True)
        self.rubberBand.setColor(Qt.blue)
        self.rubberBand.setFillColor(Qt.transparent)
        self.rubberBand.setWidth(2)

        self.marker = None
        self.pic_show.selected_id_changed.connect(self.show_marker)
        self.reset()

    def reset(self):
        self.startPoint = self.endPoint = None
        self.isEmittingPoint = False
        self.rubberBand.reset(True)
        self.pic_id = None
        self.canvas.scene().removeItem(self.marker)
        #self.pic_show.cntr_quit()

    def canvasPressEvent(self, e):
        self.reset()
        self.start_point = self.toMapCoordinates(e.pos())
        self.end_point = self.start_point
        self.isEmittingPoint = True
        self.show_rect(self.start_point, self.end_point)

    def canvasReleaseEvent(self, e):
        self.isEmittingPoint = False
        pic_ids = self.select_rect_pic.select_pics_in_rectangle(self.start_point, self.end_point)

        if pic_ids:
            self.pic_show.call_by_list(pic_ids)

    def canvasMoveEvent(self, e):
        if not self.isEmittingPoint:
            return

        self.end_point = self.toMapCoordinates(e.pos())
        self.show_rect(self.start_point, self.end_point)

    def show_rect(self, start_point, end_point):
        self.rubberBand.reset(QgsWkbTypes.PolygonGeometry)
        if start_point.x() == end_point.x() or start_point.y() == end_point.y():
            return

        self.rubberBand.addPoint(QgsPointXY(start_point.x(), start_point.y()), False)
        self.rubberBand.addPoint(QgsPointXY(start_point.x(), end_point.y()), False)
        self.rubberBand.addPoint(QgsPointXY(end_point.x(), end_point.y()), False)
        # true to update canvas
        self.rubberBand.addPoint(QgsPointXY(end_point.x(), start_point.y()), True)
        self.rubberBand.show()

    def show_marker(self, _id):
        point = self.select_rect_pic.get_mappoint(_id)
        if point:
            self.canvas.scene().removeItem(self.marker)
            self.marker = QgsVertexMarker(self.canvas)
            self.marker.setColor(Qt.yellow)
            self.marker.setIconSize(6)  # or ICON_BOX, ICON_X
            self.marker.setIconType(QgsVertexMarker.ICON_CROSS)
            self.marker.setPenWidth(3)
            self.marker.setCenter(point)
            self.marker.show()

    def deactivate(self):
        self.reset()
        QgsMapTool.deactivate(self)
        self.deactivated.emit()

canvas = iface.mapCanvas()
rb = SelectRectanglePicMapTool(canvas)
canvas.setMapTool(rb)
