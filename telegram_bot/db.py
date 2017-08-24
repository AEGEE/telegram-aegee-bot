import sqlite3
import logging

# create logger
module_logger = logging.getLogger(__name__)


class DBConnection:
    def __init__(self, filename="bot.db"):

        self.filename = filename
        self.connection = sqlite3.connect(filename, timeout=20)
        # don't wait for the disk to finish writing
        self.connection.execute("PRAGMA synchronous = OFF")
        # journal disabled since we never do rollbacks
        self.connection.execute("PRAGMA journal_mode = %s" % 'WAL')
        # 64mb of cache memory,probably need to make it user configurable
        self.connection.execute("PRAGMA cache_size=-%s" % (32 * 1024))
        self.connection.row_factory = sqlite3.Row

    def action(self, query, args=None):

        if query is None:
            return

        sql_result = None

        try:
            with self.connection as c:
                if args is None:
                    sql_result = c.execute(query)
                else:
                    sql_result = c.execute(query, args)

        except sqlite3.OperationalError as e:
            if "unable to open database file" in str(e) or "database is locked" in str(e):
                module_logger.debug('Database Error: %s', e)
            else:
                module_logger.debug('Database error: %s', e)
                raise

        except sqlite3.DatabaseError as e:
            module_logger.debug('Fatal Error executing %s :: %s', query, e)
            raise

        return sql_result

    def select(self, query, args=None):

        sql_results = self.action(query, args).fetchall()

        if sql_results is None or sql_results == [None]:
            return []

        return sql_results

    def insert_gossip(self, name, message):
        insert_query = (
            "INSERT INTO gossip (name, message)" +
            " VALUES ('" + name + "', '" + message + "')"
        )
        try:
            self.action(insert_query)
        except sqlite3.IntegrityError:
            module_logger.debug('Queries failed: %s', insert_query)

    def upsert(self, tableName, valueDict, keyDict):

        def genParams(myDict):
            return [x + " = ?" for x in myDict.keys()]

        changesBefore = self.connection.total_changes

        update_query = "UPDATE " + tableName + " SET " + ", ".join(
            genParams(valueDict)) + " WHERE " + " AND ".join(genParams(keyDict))

        self.action(update_query, valueDict.values() + keyDict.values())

        if self.connection.total_changes == changesBefore:
            insert_query = (
                "INSERT INTO " + tableName + " (" + ", ".join(
                    valueDict.keys() + keyDict.keys()) + ")" +
                " VALUES (" + ", ".join(["?"] * len(valueDict.keys() + keyDict.keys())) + ")"
            )
            try:
                self.action(insert_query, valueDict.values() + keyDict.values())
            except sqlite3.IntegrityError:
                module_logger.debug('Queries failed: %s and %s', update_query, insert_query)