import os
import sqlite3
from utils.env import DB_PATH


class MusicSQL:
    """
    CRUD commands for MusicDB
    """
    CREATE_TABLE = """
        CREATE TABLE IF NOT EXISTS {table_name} (
           name TEXT NOT NULL,
           url TEXT NOT NULL,
           id INTEGER PRIMARY KEY AUTOINCREMENT,
           UNIQUE (name, url)
       );
    """
    INSERT_ITEM = "INSERT INTO {table_name} (name, url) VALUES ('{name}', '{url}');"
    SELECT_ALL_ITEM = "SELECT * FROM {table_name};"
    SELECT_ITEM = "SELECT * FROM {table_name} WHERE id={id};"
    SELECT_ITEM_NAME = "SELECT * FROM {table_name} WHERE name LIKE '%{name}%';"
    SELECT_TABLES = "SELECT * FROM sqlite_master WHERE type='table' AND name != 'sqlite_sequence';"
    DELETE_FROM = "DELETE FROM {table_name} WHERE id={id};"
    DROP_TABLE = "DROP TABLE {table_name};"


class MusicItem:
    def __init__(self, name: str, url: str, id: str = None):
        self.name = name
        self.url = url
        self.id = id

    @classmethod
    def from_list(cls, data: list):
        name = data[0]
        url = data[1]
        try:
            id = data[2]
        except ValueError:
            id = None
        return cls(name, url, id)

    @classmethod
    def from_dict(cls, data: dict):
        name = data['title']
        url = data.get("id") or data.get("url")
        return cls(name, url, None)

    def __str__(self) -> str:
        return f"`{self.id}.` [{self.name}]({self.url})" if self.id is not None else f"[{self.name}]({self.url})"

    def __repr__(self) -> str:
        return self.__str__()


class MusicDB:
    """
    Class for Music CRUD operations
    """

    def __init__(self, guild_id):
        self.guild_id = str(guild_id)
        self.db = os.path.join(DB_PATH, "music", "guild_" + str(guild_id) + ".db")
        self.conn: sqlite3.Connection = None

    def exists(self) -> bool:
        return os.path.exists(self.db)

    def contains(self, playlist: str) -> bool:
        l = sqlite3.connect(self.db).cursor().execute(MusicSQL.SELECT_TABLES).fetchall()
        if not l:
            return False
        l = [t[1] for t in l]
        if playlist in l:
            return True
        return False

    def close(self):
        self.conn.close()
        self.conn = None
        return

    def create_connection(self):
        if self.conn is None:
            self.conn = sqlite3.connect(self.db)
        return

    def create_playlist(self, name: str):
        curr = self.conn.cursor()
        curr.execute(MusicSQL.CREATE_TABLE.format(table_name=name))
        self.conn.commit()
        return

    def get_playlist_items(self, name: str) -> list[MusicItem] | int:
        if not self.contains(name):
            return 0  # playlist does not exist
        curr = self.conn.cursor()
        data = curr.execute(MusicSQL.SELECT_ALL_ITEM.format(table_name=name)).fetchall()
        if not data:
            return -1  # empty playlist
        return [MusicItem.from_list(i) for i in data]

    def get_playlists(self) -> list | None:
        curr = self.conn.cursor()
        tables = curr.execute(MusicSQL.SELECT_TABLES).fetchall()
        if not tables:
            return None  # no playlists
        tables = [t[1] for t in tables]
        return tables

    def insert_item(self, name: str, item: MusicItem):
        self.create_playlist(name)  # in case db does not exist
        curr = self.conn.cursor()
        # will raise IntegrityError on inserting existing item
        curr.execute(MusicSQL.INSERT_ITEM.format(table_name=name, name=item.name, url=item.url))
        self.conn.commit()
        return

    def get_items_from_name(self, playlist: str, name) -> list[MusicItem] | int:
        if not self.contains(playlist):
            return 0
        curr = self.conn.cursor()
        items = curr.execute(MusicSQL.SELECT_ITEM_NAME.format(table_name=playlist, name=name)).fetchall()
        if not items:
            return -1
        results = [MusicItem.from_list(i) for i in items]
        return results

    def delete_from_id(self, name: str, id: int) -> MusicItem | int:
        if not self.contains(name):
            return 0
        curr = self.conn.cursor()
        try:
            item = curr.execute(MusicSQL.SELECT_ITEM.format(table_name=name, id=id)).fetchall()[0]
        except IndexError:
            return 1  # item does not exist
        curr.execute(MusicSQL.DELETE_FROM.format(table_name=name, id=id))
        self.conn.commit()
        return MusicItem.from_list(item)

    def drop_playlist(self, playlist: str) -> int | str:
        if not self.contains(playlist):
            return 0
        curr = self.conn.cursor()
        curr.execute(MusicSQL.DROP_TABLE.format(table_name=playlist))
        return playlist
