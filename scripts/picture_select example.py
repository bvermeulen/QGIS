from qgis.PyQt.QtCore import Qt, QTimer
from qgis.core import QgsProject, QgsRectangle, QgsWkbTypes
from qgis.gui import QgsMapToolEmitPoint, QgsRubberBand


POLLING_RATE_MS = 250


class WindowShow(QWidget):

    def __init__(self, mode='single_picture'):
        super().__init__()

        self.initUI()
        self._button_counter = 0

    def initUI(self):
        vbox = QVBoxLayout()

        hbox_text = QHBoxLayout()
        self.text_lbl = QLabel()
        self.text_lbl.setAlignment(Qt.AlignTop)
        hbox_text.addWidget(self.text_lbl)

        hbox_button = QHBoxLayout()
        button = QPushButton('press me')
        button.clicked.connect(self.add_counter_button_pressed)
        hbox_button.addWidget(button)

        vbox.addLayout(hbox_text)
        vbox.addLayout(hbox_button)

        self.setLayout(vbox)

        self.move(400, 300)
        self.setWindowTitle('Picture ... ')
        self.show()

    @property
    def button_counter(self):
        return self._button_counter

    def show_text(self):
        self.text_lbl.setText('Something more interesting ...')

    def add_counter_button_pressed(self):
        self._button_counter += 1


class SelectRectangleMapTool(QgsMapToolEmitPoint):
    def __init__(self, canvas):
        self.canvas = canvas
        QgsMapToolEmitPoint.__init__(self, self.canvas)

        self.rubberBand = QgsRubberBand(self.canvas, True)
        self.rubberBand.setColor(Qt.blue)
        self.rubberBand.setFillColor(Qt.transparent)
        self.rubberBand.setWidth(2)

        self.timer_poll_id = QTimer()
        self.timer_poll_id.timeout.connect(self.call_button_counter)
        self.reset()

    def reset(self):
        self.startPoint = self.endPoint = None
        self.isEmittingPoint = False
        self.rubberBand.reset(True)
        self.timer_poll_id.stop()
        self.window_show = None
        self.counter = 0

    def canvasPressEvent(self, e):
        self.reset()
        self.start_point = self.toMapCoordinates(e.pos())
        self.end_point = self.start_point
        self.isEmittingPoint = True

    def canvasReleaseEvent(self, e):
        self.isEmittingPoint = False
        self.show_rect(self.start_point, self.end_point)

        self.window_show = WindowShow()
        self.window_show.show_text()
        self.counter = 0
        self.timer_poll_id.start(POLLING_RATE_MS)

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
        self.rubberBand.addPoint(QgsPointXY(end_point.x(), start_point.y()), True)
        self.rubberBand.show()

    def call_button_counter(self):
        if not self.window_show:
            return

        new_counter = self.window_show.button_counter
        if new_counter != self.counter:
            self.counter = new_counter
            print(f'Button pressed in WindowShow: {self.counter}')

        else:
            return

    def deactivate(self):
        self.reset()
        QgsMapTool.deactivate(self)
        self.deactivated.emit()


canvas = iface.mapCanvas()
select_pic = SelectRectangleMapTool(canvas)
canvas.setMapTool(select_pic)
