# -*- coding: utf-8 -*-
"""
/***************************************************************************
 ActiveReceiversDialog
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

from qgis.PyQt import uic, QtWidgets, QtGui
# from qgis.PyQt import QtWidgets, QtGui

# This loads your .ui file so that PyQt can populate your plugin with the elements from Qt Designer
FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'picture_select_dlg.ui'))

years_range = range(2010, 2022)

class PictureSelectDialog(QtWidgets.QDialog, FORM_CLASS):
    def __init__(self, parent=None):
        super(PictureSelectDialog, self).__init__(parent)
        self.setupUi(self)
        self.pb_select_all.clicked.connect(self.select_all)
        self.pb_deselect_all.clicked.connect(self.deselect_all)

    def select_all(self):
        for year in years_range:
            getattr(self, f'cb_{year}').setChecked(True)

    def deselect_all(self):
        for year in years_range:
            getattr(self, f'cb_{year}').setChecked(False)