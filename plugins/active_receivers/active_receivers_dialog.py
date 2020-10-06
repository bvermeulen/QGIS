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
    os.path.dirname(__file__), 'active_receivers_dialog_base.ui'))


class ActiveReceiversDialog(QtWidgets.QDialog, FORM_CLASS):
    def __init__(self, parent=None):
        """Constructor."""
        super(ActiveReceiversDialog, self).__init__(parent)
        self.setupUi(self)
        float_validator = QtGui.QDoubleValidator()
        self.lineEdit_azimuth.setValidator(float_validator)
        self.lineEdit_inline.setValidator(float_validator)
        self.lineEdit_crossline.setValidator(float_validator)
