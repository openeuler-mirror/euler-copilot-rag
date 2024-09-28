import json
import hashlib
import logging
from chat2db.database.postgres import DatabaseInfo, PostgresDB
from chat2db.common.security import Security

logging.basicConfig(filename='app.log', level=logging.INFO,
                    format='%(asctime)s - %(filename)s[line:%(lineno)d] - %(levelname)s: %(message)s')


class DatabaseInfoManager():
    @staticmethod
    async def add_database(database_url: str):
        id = None
        with PostgresDB.get_session() as session:
            encrypted_database_url, encrypted_config = Security.encrypt(database_url)
            hashmac = hashlib.sha256(database_url.encode('utf-8')).hexdigest()
            counter = session.query(DatabaseInfo).filter(DatabaseInfo.hashmac == hashmac).first()
            if counter:
                return id
            encrypted_config = json.dumps(encrypted_config)
            database_info_entry = DatabaseInfo(encrypted_database_url=encrypted_database_url,
                                               encrypted_config=encrypted_config, hashmac=hashmac)
            session.add(database_info_entry)
            session.commit()
            id = database_info_entry.id
        return id

    @staticmethod
    async def del_database_by_id(id):
        with PostgresDB.get_session() as session:
            database_info_to_delete = session.query(DatabaseInfo).filter(DatabaseInfo.id == id).first()
            if database_info_to_delete:
                session.delete(database_info_to_delete)
            else:
                return False
            session.commit()
        return True

    @staticmethod
    async def get_database_url_by_id(id):
        with PostgresDB.get_session() as session:
            result = session.query(
                DatabaseInfo.encrypted_database_url, DatabaseInfo.encrypted_config).filter(
                DatabaseInfo.id == id).first()
            if result is None:
                return None
            try:
                encrypted_database_url, encrypted_config = result
                encrypted_config = json.loads(encrypted_config)
            except Exception as e:
                logging.error(f'数据库url解密失败由于{e}')
                return None
            if encrypted_database_url:
                database_url = Security.decrypt(encrypted_database_url, encrypted_config)
            else:
                return None
        return database_url

    @staticmethod
    async def get_all_database_info():
        with PostgresDB.get_session() as session:
            results = session.query(DatabaseInfo).order_by(DatabaseInfo.created_at).all()
            database_info_list = []
            for i in range(len(results)):
                database_id = results[i].id
                encrypted_database_url = results[i].encrypted_database_url
                encrypted_config = json.loads(results[i].encrypted_config)
                created_at = results[i].created_at
                if encrypted_database_url:
                    database_url = Security.decrypt(encrypted_database_url, encrypted_config)
                tmp_dict = {'database_id': database_id, 'database_url': database_url, 'created_at': created_at}
                database_info_list.append(tmp_dict)
        return database_info_list
