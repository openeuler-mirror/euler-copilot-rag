from sqlalchemy import and_
import sys
from chat2db.database.postgres import TableInfo, PostgresDB


class TableInfoManager():
    @staticmethod
    async def add_table_info(database_id, table_name, table_note, table_note_vector):
        id = None
        with PostgresDB.get_session() as session:
            counter = session.query(TableInfo).filter(
                and_(TableInfo.database_id == database_id, TableInfo.table_name == table_name)).first()
            if counter:
                return id
            table_info_entry = TableInfo(database_id=database_id, table_name=table_name,
                                         table_note=table_note, table_note_vector=table_note_vector)
            session.add(table_info_entry)
            session.commit()
            id = table_info_entry.id
        return id

    @staticmethod
    async def del_table_by_id(id):
        with PostgresDB.get_session() as session:
            table_info_to_delete = session.query(TableInfo).filter(TableInfo.id == id).first()
            if table_info_to_delete:
                session.delete(table_info_to_delete)
            else:
                return False
            session.commit()
        return True

    @staticmethod
    async def get_table_info_by_table_id(table_id):
        with PostgresDB.get_session() as session:
            table_id, database_id, table_name, table_note = session.query(
                TableInfo.id, TableInfo.database_id, TableInfo.table_name, TableInfo.table_note).filter(
                TableInfo.id == table_id).first()
        if table_id is None:
            return None
        return {
            'table_id': table_id,
            'database_id': database_id,
            'table_name': table_name,
            'table_note': table_note
        }

    @staticmethod
    async def get_table_id_by_database_id_and_table_name(database_id, table_name):
        with PostgresDB.get_session() as session:
            table_info_entry = session.query(
                TableInfo).filter(
                TableInfo.database_id == database_id,
                TableInfo.table_name == table_name,
            ).first()
        if table_info_entry:
            return table_info_entry.id
        return None

    @staticmethod
    async def get_table_info_by_database_id(database_id, enable=None):
        with PostgresDB.get_session() as session:
            if enable is None:
                results = session.query(
                    TableInfo).filter(TableInfo.database_id == database_id).all()
            else:
                results = session.query(
                    TableInfo).filter(
                    and_(TableInfo.database_id == database_id,
                         TableInfo.enable == enable
                         )).all()
        table_info_list = []
        for result in results:
            table_info_list.append({'table_id': result.id, 'table_name': result.table_name,
                                   'table_note': result.table_note, 'created_at': result.created_at})
        return table_info_list

    @staticmethod
    async def get_topk_table_by_cos_dis(database_id, tmp_vector, topk=3):
        with PostgresDB.get_session() as session:
            results = session.query(
                TableInfo.id
            ).filter(TableInfo.database_id == database_id).order_by(
                TableInfo.table_note_vector.cosine_distance(tmp_vector)
            ).limit(topk).all()
        table_id_list = [result[0] for result in results]
        return table_id_list
