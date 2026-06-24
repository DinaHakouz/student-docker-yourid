import os
import pymysql


def get_db_connection():
    config = {
        "host": os.environ.get("DB_HOST", "db"),
        "user": os.environ["DB_USER"],
        "password": os.environ["DB_PASSWORD"],
        "db": os.environ["DB_NAME"],
        "port": int(os.environ.get("DB_PORT", 3306)),
        "cursorclass": pymysql.cursors.DictCursor,
        "autocommit": True,
    }
    return pymysql.connect(**config)
