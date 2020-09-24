import io
from PIL import Image
from PyQt5.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton,
    QShortcut
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QImage, QPixmap
from .picture_db import PictureDb

anticlockwise_symbol = '\u21b6'
clockwise_symbol = '\u21b7'
right_arrow_symbol = '\u25B6'
left_arrow_symbol = '\u25C0'

def pil2pixmap(pil_image):
    bytes_img = io.BytesIO()
    pil_image.save(bytes_img, format='JPEG')

    qimg = QImage()
    qimg.loadFromData(bytes_img.getvalue())

    return QPixmap.fromImage(qimg)

def meta_to_text(pic_meta, file_meta, lat_lon_str, index=None, total=None):
    try:
        _date_pic = pic_meta.date_picture.strftime("%d-%b-%Y %H:%M:%S")

    except AttributeError:
        _date_pic = None

    text = (
        f'id: {pic_meta.id:6}\n'
        f'file name: {file_meta.file_name}\n'
        f'file path: {file_meta.file_path}\n'
        f'file modified: {file_meta.file_modified.strftime("%d-%b-%Y %H:%M:%S")}\n'
        f'date picture: {_date_pic}\n'
        f'md5: {pic_meta.md5_signature}\n'
        f'camera make: {pic_meta.camera_make}\n'
        f'camera model: {pic_meta.camera_model}\n'
        f'location: {lat_lon_str}\n'
        f'file check: {file_meta.file_checked}\n'
        f'rotate: {pic_meta.rotate:3}\n'
        f'rotate_check: {pic_meta.rotate_checked}'
    )

    if index is not None:
        text += f'\nindex: {index+1} of {total}'

    return text


class PictureShow(QWidget):

    def __init__(self, mode='single_picture'):
        super().__init__()

        self.mode = mode
        self.picdb = PictureDb()

        self.rotate = None
        self.index = None
        self.id_list = []
        self.initUI()

    def initUI(self):
        vbox = QVBoxLayout()

        hbox_pic_text = QHBoxLayout()

        self.pic_lbl = QLabel()
        hbox_pic_text.addWidget(self.pic_lbl)
        self.text_lbl = QLabel()
        self.text_lbl.setAlignment(Qt.AlignTop)
        hbox_pic_text.addWidget(self.text_lbl)

        hbox_buttons = QHBoxLayout()
        #quit_button = QPushButton('Quit')
        #quit_button.clicked.connect(self.cntr_quit)
        if self.mode != 'single_picture':
            prev_button = QPushButton(left_arrow_symbol)
            prev_button.clicked.connect(self.cntr_prev)
            next_button = QPushButton(right_arrow_symbol)
            next_button.clicked.connect(self.cntr_next)
        #save_button = QPushButton('save')
        #save_button.clicked.connect(self.cntr_save)

        clockwise_button = QPushButton(clockwise_symbol)
        clockwise_button.clicked.connect(self.rotate_clockwise)
        anticlockwise_button = QPushButton(anticlockwise_symbol)
        anticlockwise_button.clicked.connect(self.rotate_anticlockwise)

        hbox_buttons.setAlignment(Qt.AlignLeft)
        hbox_buttons.addWidget(anticlockwise_button)
        hbox_buttons.addWidget(clockwise_button)
        if self.mode != 'single_picture':
            hbox_buttons.addWidget(prev_button)
            hbox_buttons.addWidget(next_button)
            #hbox_buttons.addWidget(save_button)
            #hbox_buttons.addWidget(quit_button)

        vbox.addLayout(hbox_pic_text)
        vbox.addLayout(hbox_buttons)

        self.setLayout(vbox)

        if self.mode != 'single_picture':
            QShortcut(Qt.Key_Left, self, self.cntr_prev)
            QShortcut(Qt.Key_Right, self, self.cntr_next)
        #QShortcut(Qt.Key_S, self, self.cntr_save)
        QShortcut(Qt.Key_Space, self, self.rotate_clockwise)

        self.move(400, 300)
        self.setWindowTitle('Picture ... ')
        self.show()

    def call_by_list(self, id_list):
        self.id_list = id_list
        self.index = 0
        self.cntr_select_pic(self.id_list[self.index])

    @property
    def picture_id(self):
        return self.id_list[self.index]

    def show_picture(self):
        pixmap = pil2pixmap(self.image)
        self.pic_lbl.setPixmap(pixmap)

        self.text = meta_to_text(
            self.pic_meta, self.file_meta, self.lat_lon_str,
            index=self.index, total=len(self.id_list)
        )
        self.text_lbl.setText(self.text)

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

    def cntr_select_pic(self, _id):
        self.image, self.pic_meta, self.file_meta, self.lat_lon_str = (
            self.picdb.load_picture_meta(_id))

        if self.pic_meta:
            self.rotate = self.pic_meta.rotate
            self.show_picture()

    def cntr_prev(self):
        self.index -= 1
        if self.index < 0:
            self.index = len(self.id_list) - 1

        self.image, self.pic_meta, self.file_meta, self.lat_lon_str = (
            self.picdb.load_picture_meta(self.id_list[self.index]))
        if self.pic_meta:
            self.rotate = self.pic_meta.rotate
            self.show_picture()

    def cntr_next(self):
        self.index += 1
        if self.index > len(self.id_list) - 1:
            self.index = 0

        self.image, self.pic_meta, self.file_meta, self.lat_lon_str = (
            self.picdb.load_picture_meta(self.id_list[self.index]))
        if self.pic_meta:
            self.rotate = self.pic_meta.rotate
            self.show_picture()

    def cntr_save(self):
        self.picdb.update_thumbnail_image(
            self.id_list[self.index], self.image, self.rotate)

    def cntr_quit(self):
        self.close()
