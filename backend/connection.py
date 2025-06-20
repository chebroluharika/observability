import os

import psycopg2
from dotenv import load_dotenv

load_dotenv()


def get_db_string():
    database_string = "postgresql://{user}:{pw}@{host}:{port}/{dbname}"
    return database_string.format(
        user=os.getenv("POSTGRES_USER", "postgres"),
        pw=os.getenv("POSTGRES_PASSWORD", "postgres"),
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=os.getenv("POSTGRES_PORT", "5432"),
        dbname=os.getenv("POSTGRES_DB", "postgres"),
    )


# Connect to PostgreSQL
def get_db_conn():
    db_string = get_db_string()
    print(f"{db_string = }")

    try:
        conn = psycopg2.connect(db_string)
    except psycopg2.OperationalError as err:
        err_msg = "DB Connection Error - Error: {}".format(err)
        print(err_msg)
        return None
    return conn
