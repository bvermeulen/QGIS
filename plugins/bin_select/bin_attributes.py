import sys
from pathlib import Path
import numpy as np
import pandas as pd
from sqlalchemy import create_engine, text, bindparam
import matplotlib as mpl
import matplotlib.pyplot as plt
import matplotlib.colors as colors
import matplotlib.ticker as ticker
from .db_tools import DbTools
from matplotlib.projections import register_projection
from windrose import WindroseAxes

DEG2RAD = np.pi / 180.0
PLOT_BINS_WIDTH = 1 / 5
NSECTORS = 16
OFFSET_MARGIN = 1.2
BASE_FONTSIZE = 10
FIGSIZE = (8, 8)
MIN_TEXT = 4
LEGEND_BOTTOM_SPACE = 0.20
LEGEND_X = -0.1
LEGEND_Y = -0.60
LEGEND_VISIBLE_SCALE = 0.63

register_projection(WindroseAxes)


class BinAttributes:

    def __init__(
        self, db_file: Path, center_bin: tuple[int, int], offset, src_indexes, **kwargs
    ) -> pd.DataFrame:
        super().__init__(**kwargs)
        db_uri = "".join(["sqlite:///", str(db_file)])
        self.engine = create_engine(db_uri)
        self.center_bin = center_bin
        self.offset = offset
        self.src_indexes = src_indexes
        self.traces_table = "traces"
        self.bins_df = np.empty((3, 3), dtype=object)

    def get_bin(self, bin_src: int, bin_rcv: int) -> pd.DataFrame:
        query = text(
            f"SELECT * FROM {self.traces_table} WHERE "
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
                "max_offset": self.offset,
            },
        )
        return bin_df

    def get_surrounding_bins(self) -> np.array:
        for i in [-1, 0, 1]:
            for j in [-1, 0, 1]:
                selector = np.array([i, j], dtype=int)
                bin = (self.center_bin + selector).tolist()
                self.bins_df[i, j] = self.get_bin(bin[0], bin[1])

        return self.bins_df


class Plot:
    def __init__(self, bins_df: np.array):
        self.bins_df = bins_df
        self.legend = None
        self.fig = None
        self.axes = None

    def setup_plot_cartesian(self, figsize: tuple[int, int]) -> None:
        self.fig, self.axes = plt.subplots(
            3, 3, sharex=True, sharey=True, figsize=figsize
        )
        self.fig.canvas.mpl_connect("resize_event", self.on_resize)
        self.fig.tight_layout(pad=1.2)
        self.fig.subplots_adjust(wspace=0, hspace=0)
        labelsize = BASE_FONTSIZE
        for i, ax in enumerate(self.axes.flat):
            ax.tick_params(axis="both", labelsize=labelsize)
            if i == 6:
                ax.tick_params(left=True, bottom=True)
                ax.label_outer()
            else:
                ax.tick_params(left=False, bottom=False)
                ax.tick_params(labelleft=False, labelbottom=False)

        ax.xaxis.set_major_locator(ticker.MaxNLocator(5))
        ax.yaxis.set_major_locator(ticker.MaxNLocator(5))
        self.set_text_label_sizes()

    def setup_plot_polar(self, figsize: tuple[int, int]) -> None:
        self.fig, axes_cartesian = plt.subplots(
            3, 3, sharex=True, sharey=True, figsize=figsize
        )
        self.fig.canvas.mpl_connect("resize_event", self.on_resize)
        axes = []
        self.fig.subplots_adjust(wspace=0.0, hspace=0.0)
        self.fig.tight_layout(pad=0)
        legend_space = (
            LEGEND_BOTTOM_SPACE if self.get_scale() > LEGEND_VISIBLE_SCALE else 0
        )
        self.fig.subplots_adjust(bottom=legend_space)

        for axc in axes_cartesian.flat:
            axc.tick_params(
                left=False, bottom=False, labelleft=False, labelbottom=False
            )
            axc.set_aspect("equal")
            ax = self.fig.add_axes(
                axc.get_position(),
                projection="windrose",
                frameon=False,
            )
            ax.tick_params(left=False, bottom=False, labelleft=False, labelbottom=False)
            axes.append(ax)

        self.axes = np.array(axes).reshape(3, 3)

        self.set_text_label_sizes()
        self.set_legend()

    def get_scale(self) -> float:
        if self.fig is None:
            return 1.0

        width, height = self.fig.get_size_inches()
        return min(width / FIGSIZE[0], height / FIGSIZE[1])

    def set_text_label_sizes(self) -> None:
        scale = self.get_scale()
        size = max(MIN_TEXT, scale * BASE_FONTSIZE)
        for i, ax in enumerate(np.array(self.axes).flat):
            for t in ax.texts:
                t.set_fontsize(size)
            if i == 6:
                ax.tick_params(axis="both", labelsize=size)

        if self.legend:
            for text in self.legend.get_texts():
                text.set_fontsize(size)

    def set_legend(self) -> None:
        if not self.legend:
            return

        if (scale := self.get_scale()) > LEGEND_VISIBLE_SCALE:
            self.legend.set_visible(True)
            self.legend.set_bbox_to_anchor((LEGEND_X, LEGEND_Y / scale))

        else:
            self.legend.set_visible(False)

    def on_resize(self, event=None) -> None:
        self.set_text_label_sizes()
        self.set_legend()
        self.fig.canvas.draw_idle()

    def plot_diagram(self, plot_fn) -> mpl.figure.Figure:
        for i in [-1, 0, 1]:
            for j in [-1, 0, 1]:
                plot_fn(i, j)

        self.on_resize()
        return self.fig

    @staticmethod
    def plot():
        plt.show()

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


class PlotOffset(Plot):
    def __init__(self, bins_df: np.array, fig_size: tuple[int, int]):
        super().__init__(bins_df)
        self.setup_plot_cartesian(fig_size)

    def __del__(self):
        """destructor to remove all figures as otherwise they accumulate in memory"""
        plt.close("all")

    def plot_offset(self, i: int, j: int) -> None:
        bin_df = self.bins_df[i, j]
        if bin_df.empty:
            return
        src_midline, src_midpoint, *_ = self.calc_bin_values(i, j)
        bin_text = f"{src_midline}\n" f"{src_midpoint}"
        offsets = sorted(list(bin_df.offset))
        traces = np.arange(1, len(offsets) + 1, 1)
        self.axes[1 + i, 1 + j].bar(traces, offsets)
        self.axes[1 + i, 1 + j].text(
            0.02 * traces[-1],
            0.88 * offsets[-1],
            bin_text,
            size=BASE_FONTSIZE,
            color="red",
        )

    def diagram(self):
        return self.plot_diagram(self.plot_offset)


class PlotSpider(Plot):

    def __init__(self, bins_df: np.array, offset: float, figsize: tuple[int, int]):
        super().__init__(bins_df)
        self.offset = offset
        self.setup_plot_cartesian(figsize)

    def __del__(self):
        """destructor to remove all figures as otherwise they accumulate in memory"""
        plt.close("all")

    def plot_spider(self, i: int, j: int) -> None:
        bin_df = self.bins_df[i, j]
        if bin_df.empty:
            return
        max_offset = self.offset
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
            -max_offset * 0.95,
            -max_offset * 0.95,
            bin_text,
            size=BASE_FONTSIZE,
            color="red",
        )

    def diagram(self):
        return self.plot_diagram(self.plot_spider)


class PlotRose(Plot):
    def __init__(self, bins_df: np.array, offset: float, figsize: tuple[int, int]):
        super().__init__(bins_df)
        self.offset = offset
        self.setup_plot_polar(figsize)

    def __del__(self):
        """destructor to remove all figures as otherwise they accumulate in memory"""
        plt.close("all")

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
            0.02,
            0.02,
            bin_text,
            size=BASE_FONTSIZE,
            color="red",
            transform=self.axes[1 + i][1 + j].transAxes,
            ha="left",
            va="bottom",
        )
        self.axes[1 + i][1 + j].bar(
            azimuths,
            offsets,
            bins=np.arange(0, self.offset, int(self.offset * PLOT_BINS_WIDTH)),
            opening=1.0,
            nsector=NSECTORS,
            edgecolor="white",
        )
        if i == 1 and j == -1:
            self.legend = self.axes[1 +i][1 +j].legend(
                bbox_to_anchor=(LEGEND_X, LEGEND_Y),
            )

    def diagram(self) -> mpl.figure.Figure:
        return self.plot_diagram(self.plot_rose)


def main(argv: list):
    if len(argv) != 2:
        print("Provide the bins database file as argument!")
        sys.exit()

    db_file = Path(argv[1])
    center_bin = np.array([502, 675], dtype=int)
    config = DbTools(db_file).get_config_from_db()
    ba = BinAttributes(db_file, center_bin, config["offset"], config["src_indexes"])
    bins_df = ba.get_surrounding_bins()
    figsize = (6, 6)
    plot_offset = PlotOffset(bins_df, figsize)
    plot_offset.diagram()
    plot_offset.plot()
    plot_spider = PlotSpider(bins_df, config["offset"], figsize)
    plot_spider.diagram()
    plot_spider.plot()
    plot_rose = PlotRose(bins_df, config["offset"], figsize)
    plot_rose.diagram()
    plot_rose.plot()


if __name__ == "__main__":
    main(sys.argv)
