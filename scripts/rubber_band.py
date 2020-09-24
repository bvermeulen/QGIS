from qgis.gui import *
from qgis.PyQt.QtWidgets import QAction, QMainWindow
from qgis.PyQt.QtCore import Qt

pictures_layer = 'picture year'

class RectangleMapTool(QgsMapToolEmitPoint):
  def __init__(self, canvas):
    self.canvas = canvas
    self.layer = QgsProject.instance().mapLayersByName(pictures_layer)[0]

    QgsMapToolEmitPoint.__init__(self, self.canvas)
    self.rubberBand = QgsRubberBand(self.canvas, True)
    self.rubberBand.setColor(Qt.blue)
    self.rubberBand.setFillColor(Qt.transparent)
    self.rubberBand.setWidth(2)
    self.select_area = None
    self.reset()
    
    self.tr_wgs = QgsCoordinateTransform(
      QgsCoordinateReferenceSystem(QgsProject.instance().crs().authid()),
      QgsCoordinateReferenceSystem('EPSG:4326'),
      QgsProject.instance().transformContext()
    )


  def reset(self):
    self.startPoint = self.endPoint = None
    self.isEmittingPoint = False
    self.rubberBand.reset(True)

  def canvasPressEvent(self, e):
    print('key pressed ...')
    self.startPoint = self.toMapCoordinates(e.pos())
    self.endPoint = self.startPoint
    self.isEmittingPoint = True
    self.showRect(self.startPoint, self.endPoint)

  def canvasReleaseEvent(self, e):
    print('release ....')
    self.isEmittingPoint = False
    self.rectangle()
    if self.select_area is not None:
      print(
        "Rectangle:", 
        self.select_area.xMinimum(),
        self.select_area.yMinimum(), 
        self.select_area.xMaximum(), 
        self.select_area.yMaximum()
    )

  def canvasMoveEvent(self, e):
    if not self.isEmittingPoint:
      return

    self.endPoint = self.toMapCoordinates(e.pos())
    self.showRect(self.startPoint, self.endPoint)

  def showRect(self, startPoint, endPoint):
    self.rubberBand.reset(QgsWkbTypes.PolygonGeometry)
    if startPoint.x() == endPoint.x() or startPoint.y() == endPoint.y():
      return

    point1 = QgsPointXY(startPoint.x(), startPoint.y())
    point2 = QgsPointXY(startPoint.x(), endPoint.y())
    point3 = QgsPointXY(endPoint.x(), endPoint.y())
    point4 = QgsPointXY(endPoint.x(), startPoint.y())
        
    self.rubberBand.addPoint(point1, False)
    self.rubberBand.addPoint(point2, False)
    self.rubberBand.addPoint(point3, False)
    self.rubberBand.addPoint(point4, True)    # true to update canvas
    self.rubberBand.show()

  def rectangle(self):
    if self.startPoint is None or self.endPoint is None:
      return None
      
    elif (self.startPoint.x() == self.endPoint.x() or \
          self.startPoint.y() == self.endPoint.y()):
      return None

    start_point = self.tr_wgs.transform(self.startPoint)
    end_point = self.tr_wgs.transform(self.endPoint)
    
    self.select_area = QgsRectangle(start_point, end_point)
    selection = QgsFeatureRequest()
    selection.setFilterRect(self.select_area)
    for feature in self.layer.getFeatures(selection):
      print(feature.attributes()[2])

  def deactivate(self):
    QgsMapTool.deactivate(self)
    self.deactivated.emit()

canvas = iface.mapCanvas()
rb = RectangleMapTool(iface.mapCanvas())
canvas.setMapTool(rb)

