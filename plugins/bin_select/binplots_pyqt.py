"""PyQt shell for bin_attributes
author: Bruno Vermeulen
email: bvermeulen@hotmail.com
©2026 howdimain
admin@howdiweb.nl
"""

import time
import datetime
from functools import partial
import warnings
from pathlib import Path
from qgis.PyQt.QtCore import pyqtSignal
from qgis.PyQt import uic, QtWidgets
import matplotlib
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from .bin_attributes import read_config, BinAttributes

matplotlib.use("QtAgg")
warnings.filterwarnings("ignore", category=UserWarning)

DEFAULT_MAX_OFFSET = 4500
DEFAULT_INDEXES = [1, 2]


class MplCanvas(FigureCanvas):
    def __init__(self, fig):
        super().__init__(fig)


class BinAttributesView(QtWidgets.QMainWindow):
    """PyQt view and control"""

    selected_bin_changed = pyqtSignal(str)

    def __init__(self, db_filename, bin_id, *args, **kwargs):
        super().__init__(*args, **kwargs)
        uic.loadUi(Path(__file__).parent / "binning_plots.ui", self)
        db_filename = Path(db_filename)
        self.bins_file_stem = db_filename.parent / db_filename.stem
        self.save_folder_description = "Save to: "
        self.ActionQuit.triggered.connect(self.quit)
        self.ActionSaveFolder.triggered.connect(self.select_save_folder)
        self.ActionSave.triggered.connect(partial(self.save_plots))
        self.LineEdit_01.returnPressed.connect(self.select_bin)
        self.LineEdit_06.returnPressed.connect(self.select_bin)
        self.LineEdit_07.returnPressed.connect(self.select_bin)

        self.plot_dict = {}
        self.clear_vals()
        for _, value in self.plot_dict.items():
            value["rb"].clicked.connect(partial(self.show_plot, value["index"] - 1))
        self.save_folder = self.bins_file_stem.parent / "bin_plots"
        self.RB_Type_01.setChecked(True)
        self.DbLabel.setText(self.bins_file_stem.name)
        self.SaveFolderLabel.setText(
            "".join([self.save_folder_description, str(self.save_folder)])
        )
        self.LineEdit_01.setText(bin_id)
        self.select_bin()
        self.show()

    def clear_vals(self):
        if self.plot_dict:
            self.update_canvas_data({})

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
        self.LineEdit_01.setText("")
        self.LineEdit_02.setText("")
        self.LineEdit_03.setText("")
        self.LineEdit_04.setText("")
        self.LineEdit_05.setText("")
        self.LineEdit_06.setText(f"{", ".join(str(i) for i in DEFAULT_INDEXES)}")
        self.LineEdit_07.setText(f"{int(DEFAULT_MAX_OFFSET)}")
        self.figure_dict = {}
        self.center_bin_name = ""

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
            indexes = indexes.replace(delimeter, " ")
        try:
            indexes = [int(v) for v in indexes.split()]
            if not indexes or not all(v > 0 for v in indexes):
                raise ValueError("all indexes must be positive")

        except ValueError:
            return

        max_offset = self.LineEdit_07.text()
        try:
            max_offset = float(max_offset)
            if not (max_offset > 0):
                raise ValueError("max offset must be positive")

        except ValueError:
            return

        self.center_bin_name = f"{bin_src}_{bin_rcv}"
        ba = BinAttributes(
            str(self.bins_file_stem), (bin_src, bin_rcv), indexes, max_offset
        )
        bin_line, bin_point, easting, northing, traces = ba.calc_bin_values(0, 0)
        self.LineEdit_02.setText(f"{easting:.0f}")
        self.LineEdit_03.setText(f"{northing:.0f}")
        self.LineEdit_04.setText(f"{bin_line}/ {bin_point}")
        self.LineEdit_05.setText(f"{traces}")
        self.LineEdit_06.setText(f"{", ".join(str(i) for i in indexes)}")
        self.LineEdit_07.setText(f"{int(max_offset)}")
        self.figure_dict["Offset"] = ba.diagram(ba.setup_plot_cartesian, ba.plot_offset)
        self.figure_dict["Spider"] = ba.diagram(ba.setup_plot_cartesian, ba.plot_spider)
        self.figure_dict["Rose"] = ba.diagram(ba.setup_plot_polar, ba.plot_rose)
        self.update_canvas_data(self.figure_dict)
        bin_loc_str = ", ".join([str(easting), str(northing)])
        self.selected_bin_changed.emit(bin_loc_str)
        # make sure there is destructor (__del__) to apply plt.close('all') to remove all figures
        # and prevent deleting the instance too quickly for qgis to catch up
        time.sleep(1)
        del ba

    def update_canvas_data(self, figure_dict):
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
