import io
from functools import wraps
from PIL import Image
from recordtype import recordtype
from decouple import config
import psycopg2


class Exif:
    ''' utility methods to handle picture exif
    '''
    codec = 'ISO-8859-1'  # or latin-1

    @staticmethod
    def convert_gps(gps_latitude, gps_longitude, gps_altitude):
        ''' input based on tuples of fractions
        '''
        def convert_to_degrees(lat_long_value):
            ref = lat_long_value.get('ref', '')
            fractions = lat_long_value.get('pos', [0, 1])
            degrees = fractions[0][0] / fractions[0][1]
            minutes = fractions[1][0] / fractions[1][1]
            seconds = fractions[2][0] / fractions[2][1]

            if fractions[1][0] == 0 and fractions[2][0] == 0:
                lat_long_str = f'{ref} {degrees:.4f}\u00B0'

            elif fractions[2][0] == 0:
                lat_long_str = f'{ref} {degrees:.0f}\u00B0 {minutes:.2f}"'

            else:
                lat_long_str = f'{ref} {degrees:.0f}\u00B0 {minutes:.0f}" {seconds:.0f}\''

            lat_long = degrees + minutes / 60 + seconds / 3600
            if ref in ['S', 'W', 's', 'w']:
                lat_long *= -1

            return lat_long_str, lat_long

        try:
            latitude, lat_val = convert_to_degrees(gps_latitude)
            longitude, lon_val = convert_to_degrees(gps_longitude)

            try:
                alt_fraction = gps_altitude.get('alt')
                altitude = f'{alt_fraction[0]/ alt_fraction[1]:.2f}'
                alt_val = alt_fraction[0] / alt_fraction[1]

            except (TypeError, AttributeError, ZeroDivisionError):
                altitude = '-'
                alt_val = 0

            return (
                f'{latitude}, {longitude}, altitude: {altitude}',
                (lat_val, lon_val, alt_val))

        except (TypeError, AttributeError, ZeroDivisionError) as _:
            return None, None

class DbUtils:
    '''  utility methods for database
    '''
    host = config('DB_HOST')
    db_user = config('DB_USERNAME')
    db_user_pw = config('DB_PASSWORD')
    database = config('DATABASE')

    @classmethod
    def connect(cls, func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            connect_string = f'host=\'{cls.host}\' dbname=\'{cls.database}\''\
                             f'user=\'{cls.db_user}\' password=\'{cls.db_user_pw}\''
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
                print(f'error while connect to PostgreSQL {cls.database}: '
                      f'{error}')

            finally:
                if connection:
                    cursor.close()
                    connection.close()

            return result

        return wrapper

    @staticmethod
    def get_cursor(cursor):
        if cursor:
            return cursor[0]

        else:
            print('unable to connect to database')
            raise()


class PictureDb:
    table_pictures = 'pictures'
    table_files = 'files'

    PicturesTable = recordtype('PicturesTable',
                               'id, date_picture, md5_signature, camera_make, '
                               'camera_model, gps_latitude, gps_longitude, '
                               'gps_altitude, gps_img_direction, thumbnail, exif, '
                               'rotate, rotate_checked')

    FilesTable = recordtype('FilesTable',
                            'id, picture_id, file_path, file_name, file_modified, '
                            'file_created, file_size, file_checked')

    @classmethod
    @DbUtils.connect
    def load_picture_meta(cls, _id: int, *args):
        ''' load picture meta data from the database
            :arguments:
                _id: picture id number in database: integer
            :returns:
                im: PIL image
                pic_meta: recordtype PicturesTable
                file_meta: recordtype FilesTable
                lat_lon_str: string
        '''
        cursor = DbUtils().get_cursor(args)

        sql_string = f'SELECT * FROM {cls.table_pictures} WHERE id={_id};'
        cursor.execute(sql_string)
        data_from_table_pictures = cursor.fetchone()

        if not data_from_table_pictures:
            return None, None, None, None
        else:
            sql_string = f'SELECT * FROM {cls.table_files} WHERE picture_id={_id};'
            cursor.execute(sql_string)
            data_from_table_files = cursor.fetchone()
            if not data_from_table_files:
                return None, None, None, None

        pic_meta = cls.PicturesTable(
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

        file_meta = cls.FilesTable(
            id=data_from_table_files[0],
            picture_id=data_from_table_files[1],
            file_path=data_from_table_files[2],
            file_name=data_from_table_files[3],
            file_modified=data_from_table_files[4],
            file_created=data_from_table_files[5],
            file_size=data_from_table_files[6],
            file_checked=data_from_table_files[7],
        )

        assert pic_meta.id == file_meta.picture_id, \
            'load_picture_meta: database integrity error'

        if pic_meta.thumbnail:
            img_bytes = io.BytesIO(
                pic_meta.thumbnail.encode(Exif().codec))
            im = Image.open(img_bytes)

        lat_lon_str, _ = Exif().convert_gps(
            pic_meta.gps_latitude, pic_meta.gps_longitude, pic_meta.gps_altitude)

        return im, pic_meta, file_meta, lat_lon_str
