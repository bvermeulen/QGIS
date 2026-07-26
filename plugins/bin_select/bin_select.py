# -*- coding: utf-8 -*-
"""
/***************************************************************************
 BinSelect
                                 A QGIS plugin
 Draws rubberband and displays the pictures within the rectangle
        begin                : 2026-07-18
        copyright            : (C) 2026 by Bruno Vermeulen
        email                : bruno.vermeulen@hotmail.com
 ***************************************************************************/
"""

from pathlib import Path
from qgis.PyQt.QtCore import Qt, QCoreApplication
from qgis.PyQt.QtGui import QIcon, QColorConstants
from qgis.PyQt.QtWidgets import QAction

from qgis.core import (
    QgsSpatialIndex,
    QgsPointXY,
    QgsDataSourceUri,
    QgsClassificationFixedInterval,
)
from qgis.gui import (
    QgsMapToolEmitPoint,
    QgsVertexMarker,
)
from .binplots_pyqt import BinAttributesView
from .bin_select_dlg import BinSelectDialog


class SelectBin:
    def __init__(self, active_layer):
        self.layer = active_layer
        self.spatial_index = QgsSpatialIndex(self.layer.getFeatures())
        self.bin_attr_window = None

    def select_show_bin_attr(self, search_point: QgsPointXY) -> tuple[str, any]:
        select_bin_id = self.spatial_index.nearestNeighbor(search_point, neighbors=1)
        feature = self.layer.getFeature(select_bin_id[0])
        try:
            bin_id = ",".join([str(feature["bin_sp"]), str(feature["bin_rp"])])
        except KeyError:
            return None, None

        if bin_id:
            dbname = QgsDataSourceUri(self.layer.source()).database()
            self.bin_attr_window = BinAttributesView(dbname, bin_id)
            return bin_id, self.bin_attr_window.selected_bin_changed

    def close_attr_window(self):
        if self.bin_attr_window:
            self.bin_attr_window.quit()


class SelectMapTool(QgsMapToolEmitPoint):
    def __init__(self, iface, active_layer):
        self.iface = iface
        self.layer = active_layer
        self.canvas = iface.mapCanvas()
        QgsMapToolEmitPoint.__init__(self, self.canvas)
        self.bin_select = SelectBin(active_layer)
        self.pressed_point = None
        self.marker = None
        self.remove_marker()

    def remove_marker(self):
        self.canvas.scene().removeItem(self.marker)

    def canvasPressEvent(self, e):
        self.remove_marker()
        self.pressed_point = self.toMapCoordinates(e.pos())
        bin_id, bin_changed_handler = self.bin_select.select_show_bin_attr(
            self.pressed_point
        )
        if bin_id:
            self.show_marker()
            bin_changed_handler.connect(self.bin_changed_action)

    def bin_changed_action(self, changed_bin_val):
        if changed_bin_val == "quit":
            self.remove_marker()

        elif changed_bin_val == "new_bin":
            renderer = self.layer.renderer()
            method = QgsClassificationFixedInterval()
            method.setParameterValues({"INTERVAL": 3.0})
            method.setLabelPrecision(0)
            renderer.setClassificationMethod(method)
            self.layer.setRenderer(renderer)
            renderer.updateClasses(self.layer, 0)
            renderer.updateColorRamp()
            self.layer.triggerRepaint()

        else:
            easting, northing = [float(v) for v in changed_bin_val.split(",")]
            self.pressed_point = QgsPointXY(easting, northing)
            self.show_marker()

    def show_marker(self):
        if self.pressed_point:
            self.remove_marker()
            self.marker = QgsVertexMarker(self.canvas)
            self.marker.setColor(QColorConstants.Yellow)
            self.marker.setIconSize(8)
            self.marker.setIconType(QgsVertexMarker.ICON_CROSS)
            self.marker.setPenWidth(3)
            self.marker.setCenter(self.pressed_point)
            self.marker.show()

    def deactivate(self):
        self.remove_marker()
        self.bin_select.close_attr_window()


class BinSelect:
    def __init__(self, iface):
        self.iface = iface
        self.canvas = self.iface.mapCanvas()
        self.menu = self.tr("&Bin Select")
        self.action = None
        self.first_start = True

    def initGui(self):
        icon_path = str(Path(__file__).parent / "resources/images/icon.png")
        self.action = QAction(
            QIcon(icon_path), self.tr("Picture Select"), self.iface.mainWindow()
        )
        self.action.triggered.connect(self.run)
        self.action.setEnabled(True)
        self.action.setCheckable(True)
        self.action.setStatusTip("Select pictures ...")
        self.iface.addToolBarIcon(self.action)
        self.iface.addPluginToMenu(self.menu, self.action)

    def tr(self, message):
        return QCoreApplication.translate("BinSelect", message)

    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        self.iface.removePluginMenu(self.tr("&Bin Select"), self.action)
        self.iface.removeToolBarIcon(self.action)

    def run(self):
        result = False
        if self.first_start:
            self.smt = None
            bin_layer = None
            self.first_start = False
            dlg = BinSelectDialog()
            dlg.show()
            result = dlg.exec()
            bin_layer = dlg.get_selected_layer()
            dlg.close()

        if result:
            if self.action.isChecked() and bin_layer:
                self.smt = SelectMapTool(self.iface, bin_layer)
                self.canvas.setMapTool(self.smt)

        else:
            if self.smt:
                self.smt.deactivate()
                self.canvas.unsetMapTool(self.smt)

            self.action.setChecked(False)
            self.first_start = True
