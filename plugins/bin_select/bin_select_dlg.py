# -*- coding: utf-8 -*-
"""
/***************************************************************************
        begin                : 2026-07-18
        copyright            : (C) 2026 by Bruno Vermeulen
        email                : bruno.vermeulen@hotmail.com
 ***************************************************************************/
"""

from pathlib import Path
from qgis.core import QgsProject, QgsMapLayerProxyModel, QgsMapLayerType
from qgis.PyQt import uic, QtWidgets

# This loads your .ui file so that PyQt can populate your plugin with the elements
# from Qt Designer
FORM_CLASS, _ = uic.loadUiType(Path(__file__).parent / "bin_select_dlg.ui")


class BinSelectDialog(QtWidgets.QDialog, FORM_CLASS):
    def __init__(self, parent=None):
        super(BinSelectDialog, self).__init__(parent)
        self.setupUi(self)

        self.combo_layer.setFilters(QgsMapLayerProxyModel.VectorLayer)
        self.combo_layer.setAllowEmptyLayer(False)

        target_attribute = "bin_rp"
        layers = QgsProject.instance().mapLayers().values()
        excepted_layers = []
        for layer in layers:
            if layer.type() != QgsMapLayerType.VectorLayer:
                excepted_layers.append(layer)
                continue

            field_names = [field.name() for field in layer.fields()]
            if target_attribute not in field_names:
                excepted_layers.append(layer)

        self.combo_layer.setExceptedLayerList(excepted_layers)

    def get_selected_layer(self):
        return self.combo_layer.currentLayer()
