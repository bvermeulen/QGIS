# -*- coding: utf-8 -*-
"""
/***************************************************************************
 ActiveReceivers
                                 A QGIS plugin
 Shows a rectangle centered on source point
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                              -------------------
        begin                : 2020-09-29
        git sha              : $Format:%H$
        copyright            : (C) 2020 by Bruno Vermeulen
        email                : bruno_vermeulen2001@yahoo.com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
import os
import numpy as np
if os.name == 'posix':
    import sys
    import_path = os.path.expanduser(
        '~/.local/share/QGIS/QGIS3/profiles/default/python/site-packages')
    sys.path.insert(0, import_path)

from qgis.PyQt.QtCore import Qt, QCoreApplication
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction

from qgis.core import QgsPoint, QgsPointXY, QgsWkbTypes
from qgis.gui import QgsMapToolEmitPoint, QgsRubberBand, QgsVertexMarker

from .resources import qInitResources
qInitResources()

from .active_receivers_dialog import ActiveReceiversDialog

AZIMUTH = 0.0            # degrees [0 .. 360]
OFFSET_INLINE = 1000     # meters
OFFSET_CROSSLINE = 500   # meters


class CalcMap:

    def __init__(self, azimuth, inline, crossline):
        self.azimuth = (np.pi / 180 * azimuth)  # converted to radians
        self.inline_offset = inline
        self.crossline_offset = crossline

    def offset_transformation(self, inline_offset, crossline_offset):
        '''  transformation from inline_offset, crossline offset to delta_easting,
             delta_northing. self.azimuth angle of prospect in degrees

        :Returns:
            :dx: (m) change in x direction (float)
            :dy: (m) change in y direction (float)
        '''
        dx_crossline = crossline_offset * np.cos(self.azimuth)
        dy_crossline = -crossline_offset * np.sin(self.azimuth)
        dx_inline = -inline_offset * np.sin(self.azimuth)
        dy_inline = -inline_offset * np.cos(self.azimuth)

        return dx_inline + dx_crossline, dy_inline + dy_crossline

    def add_patch(self, x, y):
        ''' create 4 corner coordinates based inline and crossline distance
        '''
        p1 = tuple([x + self.offset_transformation(
            self.inline_offset, self.crossline_offset)[0],
                    y + self.offset_transformation(
            self.inline_offset, self.crossline_offset)[1]])

        p2=tuple([x + self.offset_transformation(
            self.inline_offset, -self.crossline_offset)[0],
                  y + self.offset_transformation(
            self.inline_offset, -self.crossline_offset)[1]])

        p3 = tuple([x + self.offset_transformation(
            -self.inline_offset, -self.crossline_offset)[0],
                    y + self.offset_transformation(
            -self.inline_offset, -self.crossline_offset)[1]])

        p4 = tuple([x + self.offset_transformation(
            -self.inline_offset, self.crossline_offset)[0],
                    y + self.offset_transformation(
            -self.inline_offset, self.crossline_offset)[1]])

        return p1, p2, p3, p4


class ActiveSpreadMapTool(QgsMapToolEmitPoint):
    def __init__(self, canvas, azimuth, inline, crossline):
        self.canvas = canvas
        self.cm = CalcMap(azimuth, inline, crossline)
        QgsMapToolEmitPoint.__init__(self, self.canvas)

        self.rubber_band = None
        self.marker = None

    def create_spread(self):
        self.rubber_band = QgsRubberBand(self.canvas)
        self.rubber_band.setColor(Qt.blue)
        self.rubber_band.setFillColor(Qt.transparent)
        self.rubber_band.setWidth(2)
        self.rubber_band.reset(QgsWkbTypes.PolygonGeometry)

        self.marker = QgsVertexMarker(self.canvas)
        self.marker.setColor(Qt.red)
        self.marker.setIconSize(3)
        # or ICON_BOX, ICON_X
        self.marker.setIconType(QgsVertexMarker.ICON_CROSS)
        self.marker.setPenWidth(3)

    def reset(self):
        self.canvas.scene().removeItem(self.marker)
        self.canvas.scene().removeItem(self.rubber_band)
        # self.rubber_band.reset()

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
        self.reset()


class ActiveReceivers:
    """QGIS Plugin Implementation."""

    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """
        self.iface = iface
        self.plugin_dir = os.path.dirname(__file__)

        self.actions = []
        self.menu = self.tr(u'&Active Receivers')
        self.first_start = None
        self.spread = None
        self.azimuth = AZIMUTH
        self.inline_offset = OFFSET_INLINE
        self.crossline_offset = OFFSET_CROSSLINE

    def tr(self, message):
        return QCoreApplication.translate('ActiveReceivers', message)

    def add_action(
        self, icon_path, text, callback,
        checkable_flag=True, enabled_flag=True, add_to_menu=True, add_to_toolbar=True,
        status_tip=None, whats_this=None, parent=None):

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)
        action.setCheckable(checkable_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            self.iface.addToolBarIcon(action)

        if add_to_menu:
            self.iface.addPluginToMenu(
                self.menu,
                action)

        self.actions.append(action)

        return action

    def initGui(self):
        icon_path = os.path.join(self.plugin_dir, 'icon.png')
        self.add_action(
            icon_path,
            text=self.tr(u'Show active receivers'),
            callback=self.run,
            parent=self.iface.mainWindow())

        self.first_start = True


    def unload(self):
        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u'&Active Receivers'),
                action)
            self.iface.removeToolBarIcon(action)

    def run(self):
        try:
            self.spread.deactivate()

        except AttributeError:
            pass

        result = False
        if self.first_start:
            self.first_start = False
            dlg = ActiveReceiversDialog()
            dlg.lineEdit_azimuth.setText(str(self.azimuth))
            dlg.lineEdit_inline.setText(str(self.inline_offset))
            dlg.lineEdit_crossline.setText(str(self.crossline_offset))

            dlg.show()
            result = dlg.exec_()

        if result:
            self.azimuth = float(dlg.lineEdit_azimuth.text())
            self.inline_offset = float(dlg.lineEdit_inline.text())
            self.crossline_offset = float(dlg.lineEdit_crossline.text())
            dlg.close()

        if self.actions[0].isChecked():
            canvas = self.iface.mapCanvas()
            self.spread = ActiveSpreadMapTool(
                canvas, self.azimuth, self.inline_offset, self.crossline_offset)
            canvas.setMapTool(self.spread)

        else:
            print('====> exit plugin')
            self.spread.deactivate()
            self.iface.mapCanvas().unsetMapTool(self.spread)
            self.first_start = True
