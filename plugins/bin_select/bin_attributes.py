import sys
import json
from pathlib import Path
import numpy as np
import pandas as pd
from sqlalchemy import create_engine, text, bindparam
import matplotlib as mpl
import matplotlib.pyplot as plt
import matplotlib.colors as colors
import matplotlib.ticker as ticker
from .db_tools import DbTools
from windrose import WindroseAxes

DEG2RAD = np.pi / 180.0
PLOT_BINS_WIDTH = 1 / 5
NSECTORS = 16
OFFSET_MARGIN = 1.2
FIGSIZE = (7, 7)


class BinAttributes:

    def __init__(
        self,
        db_file: Path,
        center_bin: tuple[int, int],
        src_indexes: list[int],
        max_offset: float,
    ) -> pd.DataFrame:
        self.engine = create_engine(f"sqlite:///{str(db_file)}")
        self.table = "traces"
        self.center_bin = center_bin
        self.src_indexes = src_indexes
        self.max_offset = max_offset
        self.bins_df = np.empty((3, 3), dtype=object)
        self.get_surrounding_bins()

    def __del__(self):
        """destructor to remove all figures as otherwise they accumulate in memory"""
        plt.close("all")

    def get_bin(self, bin_src: int, bin_rcv: int):
        query = text(
            f"SELECT * FROM {self.table} WHERE "
            f"bin_sp = :bin_sp AND bin_rp = :bin_rp AND "
            f"src_index in :src_indexes AND offset < :max_offset;"
        )
        query = query.bindparams(bindparam("src_indexes", expanding=True))
        bin_df = pd.read_sql(
            query,
            con=self.engine,
            params={
                "bin_sp": bin_src,
                "bin_rp": bin_rcv,
                "src_indexes": self.src_indexes,
                "max_offset": self.max_offset,
            },
        )
        return bin_df

    def calc_bin_values(self, i: int, j: int) -> tuple[int, int, int, float, float]:
        bin_df = self.bins_df[i, j]
        bin_traces = len(bin_df)
        try:
            src_midline = int(np.mean((bin_df.src_line + bin_df.rcv_point)) * 0.5)
            src_midpoint = int(np.mean((bin_df.src_point + bin_df.rcv_line)) * 0.5)
            easting = bin_df.mid_point_x.mean()
            northing = bin_df.mid_point_y.mean()
        except ValueError:
            src_midline = 0
            src_midpoint = 0
            easting = 0.0
            northing = 0.0

        return src_midline, src_midpoint, easting, northing, bin_traces

    def get_surrounding_bins(self):
        for i in [-1, 0, 1]:
            for j in [-1, 0, 1]:
                selector = np.array([i, j], dtype=int)
                bin = (self.center_bin + selector).tolist()
                self.bins_df[i, j] = self.get_bin(bin[0], bin[1])

    def setup_plot_polar(self):
        self.fig, axes_cartesian = plt.subplots(
            3, 3, sharex=True, sharey=True, figsize=FIGSIZE
        )
        axes = []
        self.fig.subplots_adjust(wspace=0.0, hspace=0.0)
        self.fig.tight_layout(pad=0)
        self.fig.subplots_adjust(bottom=0.2)
        for axc in axes_cartesian.flat:
            axc.tick_params(
                left=False, bottom=False, labelleft=False, labelbottom=False
            )
            ax = self.fig.add_axes(
                axc.get_position(),
                projection="windrose",
                frameon=False,
            )
            ax.tick_params(left=False, bottom=False, labelleft=False, labelbottom=False)
            axes.append(ax)

        self.axes = np.array(axes).reshape(3, 3)

    def setup_plot_cartesian(self):
        self.fig, self.axes = plt.subplots(
            3, 3, sharex=True, sharey=True, figsize=FIGSIZE
        )
        self.fig.tight_layout(pad=1.2)
        self.fig.subplots_adjust(wspace=0, hspace=0)
        for i, ax in enumerate(self.axes.flat):
            ax.tick_params(axis="both", labelsize=8)
            if i == 6:
                ax.tick_params(left=True, bottom=True)
                ax.label_outer()
            else:
                ax.tick_params(left=False, bottom=False)
                ax.tick_params(labelleft=False, labelbottom=False)

        ax.xaxis.set_major_locator(ticker.MaxNLocator(5))
        ax.yaxis.set_major_locator(ticker.MaxNLocator(5))

    def plot_rose(self, i: int, j: int) -> None:
        bin_df = self.bins_df[i, j]
        if bin_df.empty:
            return
        src_midline, src_midpoint, *_ = self.calc_bin_values(i, j)
        bin_text = f"{src_midline}\n" f"{src_midpoint}"
        azimuths = np.array(
            [(azimuth + 360 if azimuth < 0 else azimuth) for azimuth in bin_df.azimuth]
        )
        offsets = bin_df.offset

        self.axes[1 + i, 1 + j].text(
            0,
            0,
            bin_text,
            size=10,
            color="red",
            transform=self.axes[1 + i][1 + j].transAxes,
            ha="left",
            va="bottom",
        )
        self.axes[i + 1][j + 1].bar(
            azimuths,
            offsets,
            bins=np.arange(0, self.max_offset, int(self.max_offset * PLOT_BINS_WIDTH)),
            opening=1.0,
            nsector=NSECTORS,
            edgecolor="white",
        )
        if i == 1 and j == -1:
            self.axes[i + 1][j + 1].legend(bbox_to_anchor=(-0.1, -0.7))

    def plot_offset(self, i: int, j) -> None:
        bin_df = self.bins_df[i, j]
        if bin_df.empty:
            return
        src_midline, src_midpoint, *_ = self.calc_bin_values(i, j)
        bin_text = f"{src_midline}\n" f"{src_midpoint}"
        offsets = sorted(list(bin_df.offset))
        traces = np.arange(1, len(offsets) + 1, 1)
        self.axes[1 + i, 1 + j].bar(traces, offsets)
        self.axes[1 + i, 1 + j].text(
            0.1 * traces[-1], 0.85 * offsets[-1], bin_text, size=10, color="red"
        )

    def plot_spider(self, i: int, j) -> None:
        bin_df = self.bins_df[i, j]
        if bin_df.empty:
            return
        max_offset = self.max_offset
        src_midline, src_midpoint, *_ = self.calc_bin_values(i, j)
        bin_text = f"{src_midline}\n" f"{src_midpoint}"
        azimuths = bin_df.azimuth * DEG2RAD
        offsets = bin_df.offset
        eastings = 0 + offsets * np.cos(azimuths)
        northings = 0 + offsets * np.sin(azimuths)
        cmap = mpl.colormaps.get_cmap("cool")
        norm = colors.Normalize(vmin=0, vmax=max_offset)

        for easting, northing in zip(eastings, northings):
            line_color = cmap(norm(np.sqrt(easting * easting + northing * northing)))
            self.axes[1 + i, 1 + j].plot(
                [0, northing], [0, easting], color=line_color, linewidth=1
            )

        max_offset *= OFFSET_MARGIN
        self.axes[1 + i, 1 + j].set_xlim(-max_offset, max_offset)
        self.axes[1 + i, 1 + j].set_ylim(-max_offset, max_offset)
        self.axes[1 + i, 1 + j].set_aspect("equal")
        self.axes[1 + i, 1 + j].text(
            -max_offset * 0.95, -max_offset * 0.95, bin_text, size=10, color="red"
        )

    @staticmethod
    def plot():
        plt.show()

    def diagram(self, setup_plot_fn, plot_fn):
        setup_plot_fn()
        for i in [-1, 0, 1]:
            for j in [-1, 0, 1]:
                plot_fn(i, j)

        return self.fig


def main(argv: list):
    if len(argv) != 2:
        print("Provide the bins database file as argument!")
        sys.exit()

    db_file = Path(argv[1])
    config = DbTools(db_file).get_config_from_db()
    center_bin = np.array([502, 675], dtype=int)
    ba = BinAttributes(db_file, center_bin, config["offset"], config["src_indexes"])
    ba.diagram(ba.setup_plot_polar, ba.plot_rose)
    ba.diagram(ba.setup_plot_cartesian, ba.plot_offset)
    ba.diagram(ba.setup_plot_cartesian, ba.plot_spider)
    ba.plot()


if __name__ == "__main__":
    main(sys.argv)
