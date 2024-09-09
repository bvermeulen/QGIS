import io
import datetime
from dataclasses import dataclass
from functools import wraps
from PIL import Image
from decouple import config
import psycopg2


@dataclass
class PicturesTable:
    id: int
    date_picture: datetime.datetime
    md5_signature: str
    camera_make: str
    camera_model: str
    gps_latitude: dict
    gps_longitude: dict
    gps_altitude: dict
    gps_img_direction: dict
    thumbnail: str
    exif: dict
    rotate: int
    rotate_checked: bool


@dataclass
class FilesTable:
    id: int
    picture_id: int
    file_path: str
    file_name: str
    file_modified: datetime.datetime
    file_created: datetime.datetime
    file_size: int
    file_checked: bool


@dataclass
class InfoTable:
    country: str
    state: str
    city: str
    suburb: str
    road: str


class Exif:
    """utility methods to handle picture exif"""

    codec = "ISO-8859-1"  # or latin-1

    @staticmethod
    def convert_gps(gps_latitude, gps_longitude, gps_altitude):
        """input based on tuples of fractions"""

        def convert_to_degrees(lat_long_value):
            ref = lat_long_value.get("ref", "")
            fractions = lat_long_value.get("pos", [0, 1])
            degrees = fractions[0][0] / fractions[0][1]
            minutes = fractions[1][0] / fractions[1][1]
            seconds = fractions[2][0] / fractions[2][1]

            if fractions[1][0] == 0 and fractions[2][0] == 0:
                lat_long_str = f"{ref} {degrees:.4f}\u00B0"

            elif fractions[2][0] == 0:
                lat_long_str = f'{ref} {degrees:.0f}\u00B0 {minutes:.2f}"'

            else:
                lat_long_str = (
                    f"{ref} {degrees:.0f}\u00B0 {minutes:.0f}\" {seconds:.0f}'"
                )

            lat_long = degrees + minutes / 60 + seconds / 3600
            if ref in ["S", "W", "s", "w"]:
                lat_long *= -1

            return lat_long_str, lat_long

        try:
            latitude, lat_val = convert_to_degrees(gps_latitude)
            longitude, lon_val = convert_to_degrees(gps_longitude)

            try:
                alt_fraction = gps_altitude.get("alt")
                altitude = f"{alt_fraction[0]/ alt_fraction[1]:.2f}"
                alt_val = alt_fraction[0] / alt_fraction[1]

            except (TypeError, AttributeError, ZeroDivisionError):
                altitude = "-"
                alt_val = 0

            return (
                f"{latitude}, {longitude}, altitude: {altitude}",
                (lat_val, lon_val, alt_val),
            )

        except (TypeError, AttributeError, ZeroDivisionError) as _:
            return None, None


class DbUtils:
    """utility methods for database"""

    host = config("DB_HOST")
    db_user = config("DB_USERNAME")
    db_user_pw = config("DB_PASSWORD")
    database = config("DATABASE")

    @classmethod
    def connect(cls, func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            connect_string = (
                f"host='{cls.host}' dbname='{cls.database}'"
                f"user='{cls.db_user}' password='{cls.db_user_pw}'"
            )
            result = None
            try:
                # add ggsencmode='disable' to resolve unsupported frontend protocol
                # 1234.5679: server supports 2.0 to 3.0
                # should be fixed on postgresql 12.3
                connection = psycopg2.connect(connect_string)
                cursor = connection.cursor()
                result = func(*args, cursor, **kwargs)
                connection.commit()

            except psycopg2.Error as error:
                print(f"error while connect to PostgreSQL {cls.database}: " f"{error}")

            finally:
                if connection:
                    cursor.close()
                    connection.close()

            return result

        return wrapper


class PictureDb:
    table_pictures = "pictures"
    table_files = "files"
    table_locations = "locations"

    @classmethod
    @DbUtils.connect
    def load_picture_meta(cls, _id: int, cursor):
        """load picture meta data from the database
        :arguments:
            _id: picture id number in database: integer
        :returns:
            im: PIL image
            pic_meta: PicturesTable
            file_meta: FilesTable
            info_meta: InfoTable
            lat_lon_str: string
        """
        sql_string = f"SELECT * FROM {cls.table_pictures} WHERE id=%s;"
        cursor.execute(sql_string, (_id,))
        data_from_table_pictures = cursor.fetchone()

        if not data_from_table_pictures:
            return None, None, None, None, None

        sql_string = f"SELECT * FROM {cls.table_files} WHERE picture_id=%s;"
        cursor.execute(sql_string, (_id,))
        data_from_table_files = cursor.fetchone()
        if not data_from_table_files:
            return None, None, None, None, None

        sql_string = (
            f"SELECT geolocation_info FROM {cls.table_locations} WHERE picture_id=%s"
        )
        cursor.execute(sql_string, (_id,))
        geolocation_info = cursor.fetchone()[0]

        pic_meta = PicturesTable(
            id=data_from_table_pictures[0],
            date_picture=data_from_table_pictures[1],
            md5_signature=data_from_table_pictures[2],
            camera_make=data_from_table_pictures[3],
            camera_model=data_from_table_pictures[4],
            gps_latitude=data_from_table_pictures[5],
            gps_longitude=data_from_table_pictures[6],
            gps_altitude=data_from_table_pictures[7],
            gps_img_direction=data_from_table_pictures[8],
            thumbnail=data_from_table_pictures[9],
            exif=data_from_table_pictures[10],
            rotate=data_from_table_pictures[11],
            rotate_checked=data_from_table_pictures[12],
        )
        file_meta = FilesTable(
            id=data_from_table_files[0],
            picture_id=data_from_table_files[1],
            file_path=data_from_table_files[2],
            file_name=data_from_table_files[3],
            file_modified=data_from_table_files[4],
            file_created=data_from_table_files[5],
            file_size=data_from_table_files[6],
            file_checked=data_from_table_files[7],
        )
        info_meta = InfoTable(
            country=geolocation_info.get("country", ""),
            state=", ".join(
                v
                for v in [geolocation_info.get(k, "") for k in ["state", "province"]]
                if v
            ),
            city=", ".join(
                v
                for v in [
                    geolocation_info.get(k, "")
                    for k in ["city", "municipality", "town", "village"]
                ]
                if v
            ),
            suburb=geolocation_info.get("suburb", ""),
            road=geolocation_info.get("road", ""),
        )
        assert (
            pic_meta.id == file_meta.picture_id
        ), "load_picture_meta: database integrity error"

        if pic_meta.thumbnail:
            img_bytes = io.BytesIO(pic_meta.thumbnail.encode(Exif().codec))
            im = Image.open(img_bytes)

        lat_lon_str, _ = Exif().convert_gps(
            pic_meta.gps_latitude, pic_meta.gps_longitude, pic_meta.gps_altitude
        )
        return im, pic_meta, file_meta, info_meta, lat_lon_str
