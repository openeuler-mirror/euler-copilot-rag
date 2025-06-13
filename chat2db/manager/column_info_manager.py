from sqlalchemy import and_
import sys
from chat2db.database.postgres import ColumnInfo, PostgresDB


class ColumnInfoManager():
    @staticmethod
    async def add_column_info_with_table_id(table_id, column_name, column_type, column_note):
        column_info_entry = ColumnInfo(table_id=table_id, column_name=column_name,
                                       column_type=column_type, column_note=column_note)
        with PostgresDB.get_session() as session:
            session.add(column_info_entry)
            session.commit()

    @staticmethod
    async def del_column_info_by_column_id(column_id):
        with PostgresDB.get_session() as session:
            column_info_to_delete = session.query(ColumnInfo).filter(ColumnInfo.id == column_id)
            session.delete(column_info_to_delete)
            session.commit()

    @staticmethod
    async def get_column_info_by_column_id(column_id):
        tmp_dict = {}
        with PostgresDB.get_session() as session:
            result = session.query(ColumnInfo).filter(ColumnInfo.id == column_id).first()
            session.commit()
            if not result:
                return None
            tmp_dict = {
                'column_id': result.id,
                'table_id': result.table_id,
                'column_name': result.column_name,
                'column_type': result.column_type,
                'column_note': result.column_note,
                'enable': result.enable
            }
        return tmp_dict

    @staticmethod
    async def update_column_info_enable(column_id, enable=True):
        with PostgresDB.get_session() as session:
            column_info = session.query(ColumnInfo).filter(ColumnInfo.id == column_id).first()
            if column_info is not None:
                column_info.enable = True
                session.commit()
            else:
                return False
        return True

    @staticmethod
    async def get_column_info_by_table_id(table_id, enable=None):
        column_info_list = []
        with PostgresDB.get_session() as session:
            if enable is None:
                results = session.query(ColumnInfo).filter(ColumnInfo.table_id == table_id).all()
            else:
                results = session.query(ColumnInfo).filter(
                    and_(ColumnInfo.table_id == table_id, ColumnInfo.enable == enable)).all()
            for result in results:
                tmp_dict = {
                    'column_id': result.id,
                    'column_name': result.column_name,
                    'column_type': result.column_type,
                    'column_note': result.column_note,
                    'enable': result.enable
                }
                column_info_list.append(tmp_dict)
        return column_info_list
