from pathlib import Path
import sqlite3
from functools import wraps


def db_connect(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        result = None
        database = args[0].database_file
        try:
            connection = sqlite3.connect(database)
            connection.enable_load_extension(True)
            connection.execute('SELECT load_extension("mod_spatialite")')
            cursor = connection.cursor()
            result = func(*args, cursor, **kwargs)
            connection.commit()

        except sqlite3.Error as error:
            print(f"Error while connect to sqlite {database}: {error}")

        finally:
            if connection:
                cursor.close()
                connection.close()

        return result

    return wrapper


class DbTools:
    def __init__(self, database_file: Path):
        self.database_file = database_file

    @db_connect
    def update_seis_config(self, key, value, cursor):
        sql_string = (
            f"INSERT OR REPLACE INTO seis_config (key, value) " f"VALUES (?, ?);"
        )
        cursor.execute(sql_string, (key, value))

    @db_connect
    def get_config_from_db(self, cursor):
        sql_string = "select value from seis_config WHERE key = ?"
        config = {}
        config["file_stem"] = cursor.execute(sql_string, ("file_stem",)).fetchone()[0]
        config["azimuth"] = float(
            cursor.execute(sql_string, ("azimuth",)).fetchone()[0]
        )
        config["easting_orig"] = float(
            cursor.execute(sql_string, ("easting_orig",)).fetchone()[0]
        )
        config["northing_orig"] = float(
            cursor.execute(sql_string, ("northing_orig",)).fetchone()[0]
        )
        config["bin_sp_int"] = float(
            cursor.execute(sql_string, ("bin_sp_int",)).fetchone()[0]
        )
        config["bin_rp_int"] = float(
            cursor.execute(sql_string, ("bin_rp_int",)).fetchone()[0]
        )
        config["nb_bin_sp"] = int(
            float(cursor.execute(sql_string, ("nb_bin_sp",)).fetchone()[0])
        )
        config["nb_bin_rp"] = int(
            float(cursor.execute(sql_string, ("nb_bin_rp",)).fetchone()[0])
        )
        config["epsg"] = int(float(cursor.execute(sql_string, ("epsg",)).fetchone()[0]))
        config["offset"] = float(cursor.execute(sql_string, ("offset",)).fetchone()[0])
        config["src_indexes"] = [
            int(v)
            for v in cursor.execute(sql_string, ("src_indexes",))
            .fetchone()[0]
            .split(",")
        ]
        return config

    @db_connect
    def clear_bins(self, cursor):
        sql_string = "UPDATE bins SET bin_count = null;"
        cursor.execute(sql_string)

    @db_connect
    def bin_traces(self, offset, indexes, cursor):
        sql_string = (
            "UPDATE bins SET bin_count = bc FROM "
            "(SELECT bin_sp, bin_rp, count(*) AS bc "
            "FROM traces tr NOT INDEXED "
            "WHERE "
            "tr.offset >= 0 AND tr.offset < ? AND "
            f"tr.src_index IN ({", ".join(["?" for _ in indexes])}) "
            "GROUP BY tr.bin_sp, tr.bin_rp"
            ") AS bins_grouped "
            "WHERE bins.bin_sp = bins_grouped.bin_sp and bins.bin_rp = bins_grouped.bin_rp;"
        )
        cursor.execute(sql_string, (offset, *indexes))
