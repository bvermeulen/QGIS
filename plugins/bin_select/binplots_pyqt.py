"""PyQt shell for bin_attributes
author: Bruno Vermeulen
email: bvermeulen@hotmail.com
©2026 howdimain
admin@howdiweb.nl
"""

MOUSE_RELEASE_TRIGGER = 1000
FIGSIZE_PYQT_PLOT = (6.3125, 5.833)

import time
import datetime
import numpy as np
from functools import partial
import warnings
from pathlib import Path
from qgis.PyQt.QtCore import QThread, pyqtSignal, QTimer
from qgis.PyQt import uic, QtWidgets
import matplotlib
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from .db_tools import DbTools
from .bin_attributes import BinAttributes, PlotOffset, PlotSpider, PlotRose

matplotlib.use("QtAgg")
warnings.filterwarnings("ignore", category=UserWarning)

button_syle = """
    QPushButton {
        background-color: #2196F3;
        color: white;
        border-radius: 5px;
        font-size: 14px;
    }
    QPushButton:hover {
        background-color: #1E88E5;
    }
    QPushButton:pressed {
        background-color:  #1f618d;
    }
"""
button_style_active = """
    QPushButton {
        background-color: red;
        color: white;
        border-radius: 5px;
        font-size: 14px;
    }
"""


class BinningThread(QThread):
    binning_finished = pyqtSignal()

    def __init__(self, db_tools: DbTools, offset: float, src_indexes: list[int, int]):
        super().__init__()
        self.db_tools = db_tools
        self.offset = offset
        self.src_indexes = src_indexes

    def run(self):
        self.db_tools.clear_bins()
        self.db_tools.bin_traces(self.offset, self.src_indexes)
        self.binning_finished.emit()


class MplCanvas(FigureCanvas):
    def __init__(self, fig: matplotlib.figure.Figure):
        super().__init__(fig)


class BinAttributesView(QtWidgets.QMainWindow):
    """PyQt view and control"""

    selected_bin_changed = pyqtSignal(str)

    def __init__(self, db_filename: str, bin_id: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        uic.loadUi(Path(__file__).parent / "binning_plots.ui", self)
        self.plot_dict = {
            "Offset": {
                "index": 1,
                "canvas": None,
                "rb": self.RB_Type_01,
                "layout": self.FormLayout_01,
                "file_name": "bin_offset",
                "fig": None,
            },
            "Spider": {
                "index": 2,
                "canvas": None,
                "rb": self.RB_Type_02,
                "layout": self.FormLayout_02,
                "file_name": "bin_spider",
                "fig": None,
            },
            "Rose": {
                "index": 3,
                "canvas": None,
                "rb": self.RB_Type_03,
                "layout": self.FormLayout_03,
                "file_name": "bin_rose",
                "fig": None,
            },
        }
        self.db_filename = Path(db_filename)
        self.bins_file_stem = self.db_filename.parent / self.db_filename.stem
        self.db_tools = DbTools(db_filename)
        self.config = self.db_tools.get_config_from_db()
        self.save_folder_description = "Save to: "
        self.ActionQuit.triggered.connect(self.quit)
        self.ActionSaveFolder.triggered.connect(self.select_save_folder)
        self.ActionSave.triggered.connect(partial(self.save_plots))
        self.LineEdit_01.returnPressed.connect(self.select_bin)
        self.LineEdit_06.returnPressed.connect(self.select_bin)
        self.LineEdit_07.returnPressed.connect(self.select_bin)
        self.BinButton.pressed.connect(self.bin_traces)
        self.BinButton.setStyleSheet(button_syle)
        self.resize_timer = QTimer()
        self.resize_timer.setSingleShot(True)
        self.resize_timer.timeout.connect(self.handle_resize_release)

        for _, value in self.plot_dict.items():
            value["rb"].clicked.connect(partial(self.show_plot, value["index"] - 1))
        self.RB_Type_01.setChecked(True)
        self.DbLabel.setText(self.bins_file_stem.name)
        self.save_folder = self.bins_file_stem.parent / "bin_plots"
        self.SaveFolderLabel.setText(
            "".join([self.save_folder_description, str(self.save_folder)])
        )
        self.LineEdit_01.setText(bin_id)
        self.LineEdit_02.setText("")
        self.LineEdit_03.setText("")
        self.LineEdit_04.setText("")
        self.LineEdit_05.setText("")
        self.LineEdit_06.setText(
            f"{", ".join(str(i) for i in self.config["src_indexes"])}"
        )
        self.LineEdit_07.setText(f"{int(self.config["offset"])}")
        self.bins_df = np.array([])
        self.select_bin()
        self.show()

    def select_bin(self):
        bin = self.LineEdit_01.text()
        for delimeter in ["/", ",", ";"]:
            bin = bin.replace(delimeter, " ")
        try:
            bin_src, bin_rcv = [int(v) for v in bin.split()]
            if bin_src < 1 or bin_rcv < 1:
                raise ValueError("bin must be positive")

        except ValueError:
            return

        indexes = self.LineEdit_06.text()
        for delimeter in ["/", ",", ";"]:
            self.src_indexes = indexes.replace(delimeter, " ")
        try:
            self.src_indexes = [int(v) for v in indexes.split()]
            if not self.src_indexes or not all(v > 0 for v in self.src_indexes):
                raise ValueError("all indexes must be positive")

        except ValueError:
            return

        offset = self.LineEdit_07.text()
        try:
            self.offset = float(offset)
            if not (self.offset > 0):
                raise ValueError("max offset must be zero or positive")

        except ValueError:
            return

        self.db_tools.update_seis_config("offset", str(self.offset))
        self.db_tools.update_seis_config(
            "src_indexes", f"{", ".join(str(i) for i in self.src_indexes)}"
        )
        self.center_bin_name = f"{bin_src}, {bin_rcv}"
        ba = BinAttributes(
            self.db_filename, (bin_src, bin_rcv), self.offset, self.src_indexes
        )
        self.bins_df = ba.get_surrounding_bins()
        self.create_attribute_figs()
        del ba

    def create_attribute_figs(self):
        if self.bins_df.size == 0:
            return

        width = self.PlotFrame.width() / self.PlotFrame.logicalDpiX()
        height = self.PlotFrame.height() / self.PlotFrame.logicalDpiY()
        figsize = (width, height) if height > 1 else FIGSIZE_PYQT_PLOT
        self.plt_offset = PlotOffset(self.bins_df, figsize)
        self.plt_spider = PlotSpider(self.bins_df, self.offset, figsize)
        self.plt_rose = PlotRose(self.bins_df, self.offset, figsize)
        bin_line, bin_point, easting, northing, traces = (
            self.plt_offset.calc_bin_values(0, 0)
        )
        self.LineEdit_01.setText(self.center_bin_name)
        self.LineEdit_02.setText(f"{easting:.0f}")
        self.LineEdit_03.setText(f"{northing:.0f}")
        self.LineEdit_04.setText(f"{bin_line}/ {bin_point}")
        self.LineEdit_05.setText(f"{traces}")
        self.LineEdit_06.setText(f"{", ".join(str(i) for i in self.src_indexes)}")
        self.LineEdit_07.setText(f"{int(self.offset)}")
        figure_dict = {}
        figure_dict["Offset"] = self.plt_offset.diagram()
        figure_dict["Spider"] = self.plt_spider.diagram()
        figure_dict["Rose"] = self.plt_rose.diagram()
        bin_loc_str = ", ".join([str(easting), str(northing)])
        self.selected_bin_changed.emit(bin_loc_str)
        self.update_canvas_data(figure_dict)
        del self.plt_offset
        del self.plt_spider
        del self.plt_rose

    def update_canvas_data(self, figure_dict: dict):
        for key, value in self.plot_dict.items():
            value["fig"] = figure_dict.get(key)
            if value["canvas"]:
                value["canvas"].hide()
                value["layout"].removeWidget(value["canvas"])
                value["canvas"] = None

            if value["fig"]:
                value["canvas"] = MplCanvas(value["fig"])
                value["layout"].addWidget(value["canvas"])

    def show_plot(self, plot_index: int):
        self.StackedPlots.setCurrentIndex(plot_index)

    def resizeEvent(self, event):
        self.resize_timer.start(MOUSE_RELEASE_TRIGGER)
        super().resizeEvent(event)

    def handle_resize_release(self):
        self.create_attribute_figs()

    def bin_traces(self):
        self.BinButton.setText("Binning ...")
        self.BinButton.setStyleSheet(button_style_active)
        self.BinButton.setEnabled(False)
        time.sleep(0.5)
        self.config = self.db_tools.get_config_from_db()
        self.worker = BinningThread(
            self.db_tools, self.config["offset"], self.config["src_indexes"]
        )
        self.worker.binning_finished.connect(self.on_bin_traces_completion)
        self.worker.start()

    def on_bin_traces_completion(self):
        self.BinButton.setText("Bin traces")
        self.BinButton.setStyleSheet(button_syle)
        self.BinButton.setEnabled(True)
        self.worker.deleteLater()
        self.selected_bin_changed.emit("new_foldplot")

    def select_save_folder(self):
        save_folder = QtWidgets.QFileDialog.getExistingDirectory(
            self,
            "Select a save folder",
            directory=Path(self.bins_file_stem).parent.as_posix(),
        )
        if save_folder:
            self.save_folder = Path(save_folder)

        self.SaveFolderLabel.setText(
            "".join([self.save_folder_description, str(self.save_folder)])
        )

    def save_plots(self):
        base_file_name = "".join([datetime.datetime.now().strftime("%y%m%d"), "_"])
        for _, value in self.plot_dict.items():
            if not (fig := value["fig"]):
                continue

            file_name = self.save_folder / "".join(
                [
                    base_file_name,
                    value.get("file_name"),
                    "_",
                    self.center_bin_name,
                    ".png",
                ]
            )
            fig.savefig(file_name)

    def closeEvent(self, event):
        self.selected_bin_changed.emit("quit")

    def quit(self):
        self.selected_bin_changed.emit("quit")
        self.close()
