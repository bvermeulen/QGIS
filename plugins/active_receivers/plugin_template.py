# -*- coding: utf-8 -*-
from qgis.PyQt import QtWidgets


class PluginMain:
    def __init__(self, iface):
        self.iface = iface
        self.action = None

    def initGui(self):
        self.action = QtWidgets.QAction("plugin_template", self.iface.mainWindow())
        self.action.triggered.connect(self.run)
        self.iface.addPluginToMenu("plugin_template", self.action)

    def unload(self):
        self.iface.removePluginMenu("plugin_template", self.action)

    def run(self):
        QtWidgets.QMessageBox.information(
            self.iface.mainWindow(),
            "plugin_template",
            "Plugin plugin_template is running."
        )
