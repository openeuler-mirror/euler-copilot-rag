from chat2db.app.base.mysql import Mysql
from chat2db.app.base.postgres import Postgres


class DiffDatabaseService():
    database_map = {"mysql": Mysql, "postgres": Postgres}

    @staticmethod
    def get_database_service(database_type):
        return DiffDatabaseService.database_map[database_type]
