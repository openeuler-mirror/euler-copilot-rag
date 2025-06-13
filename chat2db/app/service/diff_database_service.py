import re
from urllib.parse import urlparse
from chat2db.app.base.mysql import Mysql
from chat2db.app.base.postgres import Postgres


class DiffDatabaseService():
    database_types = ["mysql", "postgresql", "opengauss"]
    database_map = {"mysql": Mysql, "postgresql": Postgres, "opengauss": Postgres}

    @staticmethod
    def get_database_service(database_type):
        if database_type not in DiffDatabaseService.database_types:
            raise f"不支持当前数据库类型{database_type}"
        return DiffDatabaseService.database_map[database_type]

    @staticmethod
    def get_database_type_from_url(database_url):
        result = urlparse(database_url)
        try:
            database_type = result.scheme.split('+')[0]
        except Exception as e:
            raise e
        return database_type.lower()

    @staticmethod
    def is_database_type_allow(database_type):
        return database_type in DiffDatabaseService.database_types
