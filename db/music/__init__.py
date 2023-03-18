import os
import sqlite3 as sql


BASE_PATH = os.path.join(os.getcwd(), "db", 'music')

CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS {} (
    name TEXT NOT NULL,
    url TEXT NOT NULL,
    id INTEGER PRIMARY KEY AUTOINCREMENT
);
"""

INSERT_DATA = """
INSERT INTO {} (name, url)
VALUES ('{}', '{}');
"""

SELECT_DATA = """
SELECT * FROM {};
"""

SELECT_DATA_WHERE = """
SELECT * FROM {}
WHERE id={};
"""

SELECT_TABLES = """
SELECT * FROM sqlite_master
WHERE type='table' AND name != 'sqlite_sequence';
"""

REMOVE_ROW = """
DELETE FROM {}
WHERE id={};
"""


def create_guild_playlist(guild_id: int):
    with open(f"{os.path.join(BASE_PATH, 'guild_' + str(guild_id) + '.db')}") as f:
        pass


def create_playlist(guild_id: int, playlist_name: str):
    conn = sql.connect(f"{os.path.join(BASE_PATH, 'guild_' + str(guild_id) + '.db')}")
    c = conn.cursor()
    c.execute(CREATE_TABLE.format(playlist_name))
    conn.commit()
    conn.close()


def insert_playlist_data(guild_id: int, playlist_name: str, data: list):
    conn = sql.connect(f"{os.path.join(BASE_PATH, 'guild_' + str(guild_id) + '.db')}")
    c = conn.cursor()
    # name, link
    c.execute(INSERT_DATA.format(playlist_name, data[0], data[1]))
    conn.commit()
    conn.close()


def get_playlist_data(guild_id: int, playlist_name: str):
    conn = sql.connect(f"{os.path.join(BASE_PATH, 'guild_' + str(guild_id) + '.db')}")
    c = conn.cursor()
    data = c.execute(SELECT_DATA.format(playlist_name)).fetchall()
    if not data:
        conn.close()
        return None
    conn.close()
    return data


def get_playlists(guild_id: int):
    conn = sql.connect(f"{os.path.join(BASE_PATH, 'guild_' + str(guild_id) + '.db')}")
    c = conn.cursor()
    unorg_tables = c.execute(SELECT_TABLES).fetchall()
    if not unorg_tables:
        conn.close()
        return None
    tables = [tb[1] for tb in unorg_tables]
    conn.close()
    return tables


def get_playlist_items(guild_id: int, playlist_name: str):
    data = get_playlist_data(guild_id, playlist_name)
    if data is not None:
        return data
    return None


def remove_playlist_item(guild_id: int, playlist_name: str, id: int):
    conn = sql.connect(f"{os.path.join(BASE_PATH, 'guild_' + str(guild_id) + '.db')}")
    c = conn.cursor()
    d = c.execute(SELECT_DATA_WHERE.format(playlist_name, id)).fetchall()[0]
    c.execute(REMOVE_ROW.format(playlist_name, id))
    conn.commit()
    conn.close()
    return d
