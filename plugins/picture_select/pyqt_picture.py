import io
from enum import Enum
from PIL import Image
from qgis.PyQt.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QLabel,
    QPushButton,
    QFrame,
    QShortcut,
)
from qgis.PyQt.QtCore import Qt, pyqtSignal
from qgis.PyQt.QtGui import QImage, QPixmap, QPalette, QColor

from .picture_db import PictureDb

anticlockwise_symbol = "\u21b6"
clockwise_symbol = "\u21b7"
right_arrow_symbol = "\u25B6"
left_arrow_symbol = "\u25C0"
border_style = "margin:2px; " "padding:2px 5px; " "border:1px solid black; "


class Mode(Enum):
    Single = 1
    Multi = 2


class QHLine(QFrame):
    def __init__(self, color=QColor("black"), width=0):
        super().__init__()
        self.setFrameShape(QFrame.HLine)
        self.setFrameShadow(QFrame.Plain)
        self.setLineWidth(width)
        self.setColor(color)

    def setColor(self, color):
        pal = self.palette()
        pal.setColor(QPalette.WindowText, color)
        self.setPalette(pal)


def pil2pixmap(pil_image):
    bytes_img = io.BytesIO()
    pil_image.save(bytes_img, format="JPEG")
    qimg = QImage()
    qimg.loadFromData(bytes_img.getvalue())
    return QPixmap.fromImage(qimg)


def meta_to_text(pic_meta, file_meta, lat_lon_str, index=None, total=None):
    try:
        _date_pic = pic_meta.date_picture.strftime("%d-%b-%Y %H:%M:%S")

    except AttributeError:
        _date_pic = None

    text = (
        f"id: {pic_meta.id:6}\n"
        f"file name: {file_meta.file_name}\n"
        f"file path: {file_meta.file_path}\n"
        f'file modified: {file_meta.file_modified.strftime("%d-%b-%Y %H:%M:%S")}\n'
        f"date picture: {_date_pic}\n"
        f"md5: {pic_meta.md5_signature}\n"
        f"camera make: {pic_meta.camera_make}\n"
        f"camera model: {pic_meta.camera_model}\n"
        f"location: {lat_lon_str}\n"
        f"file check: {file_meta.file_checked}\n"
        f"rotate: {pic_meta.rotate:3}\n"
        f"rotate_check: {pic_meta.rotate_checked}"
    )

    if index is not None:
        text += f"\nindex: {index+1} of {total}"

    return text


def info_to_text(info_meta):
    text = (
        f"country: {info_meta.country}\n"
        f"state: {info_meta.state}\n"
        f"city: {info_meta.city}\n"
        f"suburb: {info_meta.suburb}\n"
        f"road: {info_meta.road}"
    )
    return text


class PictureShow(QWidget):
    selected_id_changed = pyqtSignal(int)

    def __init__(self, mode=Mode.Single):
        super().__init__()
        self.mode = mode
        self.picdb = PictureDb()

        self.rotate = None
        self.index = None
        self.file_meta = None
        self.pic_meta = None
        self.info_meta = None
        self.id_list = []
        self.initUI()

    def initUI(self):
        mainbox = QVBoxLayout()

        hbox_main = QHBoxLayout()
        vbox_picture = QVBoxLayout()
        self.pic_lbl = QLabel()
        # self.pic_lbl.setStyleSheet(border_style)
        vbox_picture.addWidget(self.pic_lbl)
        vbox_picture.addStretch()
        vbox_text_info = QVBoxLayout()
        self.info_lbl = QLabel()
        # self.info_lbl.setStyleSheet(border_style)
        vbox_text_info.addWidget(self.info_lbl)
        vbox_text_info.addWidget(QHLine())
        self.text_lbl = QLabel()
        # self.text_lbl.setStyleSheet(border_style)
        vbox_text_info.addWidget(self.text_lbl)
        vbox_text_info.addStretch()
        hbox_main.addLayout(vbox_picture)
        hbox_main.addLayout(vbox_text_info)

        hbox_buttons = QHBoxLayout()
        if self.mode == Mode.Multi:
            prev_button = QPushButton(left_arrow_symbol)
            prev_button.clicked.connect(self.cntr_prev)
            next_button = QPushButton(right_arrow_symbol)
            next_button.clicked.connect(self.cntr_next)

        clockwise_button = QPushButton(clockwise_symbol)
        clockwise_button.clicked.connect(self.rotate_clockwise)
        anticlockwise_button = QPushButton(anticlockwise_symbol)
        anticlockwise_button.clicked.connect(self.rotate_anticlockwise)
        quit_button = QPushButton("Quit")
        quit_button.clicked.connect(self.cntr_quit)

        hbox_buttons.setAlignment(Qt.AlignLeft)
        hbox_buttons.addWidget(anticlockwise_button)
        hbox_buttons.addWidget(clockwise_button)
        if self.mode == Mode.Multi:
            hbox_buttons.addWidget(prev_button)
            hbox_buttons.addWidget(next_button)
        hbox_buttons.addWidget(quit_button)

        mainbox.addLayout(hbox_main)
        mainbox.addLayout(hbox_buttons)
        self.setLayout(mainbox)

        if self.mode == Mode.Multi:
            QShortcut(Qt.Key_Left, self, self.cntr_prev)
            QShortcut(Qt.Key_Right, self, self.cntr_next)
        QShortcut(Qt.Key_Space, self, self.rotate_clockwise)

        self.move(400, 300)
        self.setWindowTitle("Picture ... ")
        self.show()

    def show_picture(self):
        pixmap = pil2pixmap(self.image)
        self.pic_lbl.setPixmap(pixmap)

        meta_text = meta_to_text(
            self.pic_meta,
            self.file_meta,
            self.lat_lon_str,
            index=self.index,
            total=len(self.id_list),
        )
        info_text = info_to_text(self.info_meta)
        self.text_lbl.setText(meta_text)
        self.info_lbl.setText(info_text)
        self.resize(self.sizeHint())

    def rotate_clockwise(self):
        # note degrees are defined in counter clockwise direction !
        if self.image:
            self.image = self.image.rotate(-90, expand=True, resample=Image.BICUBIC)
            self.rotate += 90
            self.rotate = self.rotate % 360
            self.pic_meta.rotate = self.rotate
            self.show_picture()

    def rotate_anticlockwise(self):
        # note degrees are defined in counter clockwise direction !
        if self.image:
            self.image = self.image.rotate(+90, expand=True, resample=Image.BICUBIC)
            self.rotate -= 90
            self.rotate = self.rotate % 360
            self.pic_meta.rotate = self.rotate
            self.show_picture()

    def select_pic(self, picture_id):
        (
            self.image,
            self.pic_meta,
            self.file_meta,
            self.info_meta,
            self.lat_lon_str,
        ) = self.picdb.load_picture_meta(picture_id)
        if self.pic_meta:
            self.selected_id_changed.emit(picture_id)
            self.rotate = self.pic_meta.rotate
            self.show_picture()

    def cntr_prev(self):
        self.index -= 1
        if self.index < 0:
            self.index = len(self.id_list) - 1
        self.select_pic(self.id_list[self.index])

    def cntr_next(self):
        self.index += 1
        if self.index > len(self.id_list) - 1:
            self.index = 0
        self.select_pic(self.id_list[self.index])

    def call_by_list(self, id_list):
        self.id_list = id_list
        self.index = 0
        self.select_pic(self.id_list[self.index])

    def cntr_quit(self):
        self.close()
