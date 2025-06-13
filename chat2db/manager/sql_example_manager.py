import json
from sqlalchemy import and_
import sys
from chat2db.database.postgres import SqlExample, PostgresDB
from chat2db.security.security import Security


class SqlExampleManager():
    @staticmethod
    async def add_sql_example(question, sql, table_id, question_vector):
        id = None
        sql_example_entry = SqlExample(question=question, sql=sql,
                                       table_id=table_id, question_vector=question_vector)
        with PostgresDB.get_session() as session:
            session.add(sql_example_entry)
            session.commit()
            id = sql_example_entry.id
        return id

    @staticmethod
    async def del_sql_example_by_id(id):
        with PostgresDB.get_session() as session:
            sql_example_to_delete = session.query(SqlExample).filter(SqlExample.id == id).first()
            if sql_example_to_delete:
                session.delete(sql_example_to_delete)
            else:
                return False
            session.commit()
        return True

    @staticmethod
    async def update_sql_example_by_id(id, question, sql, question_vector):
        with PostgresDB.get_session() as session:
            sql_example_to_update = session.query(SqlExample).filter(SqlExample.id == id).first()
            if sql_example_to_update:
                sql_example_to_update.sql = sql
                sql_example_to_update.question = question
                sql_example_to_update.question_vector = question_vector
                session.commit()
            else:
                return False
        return True

    @staticmethod
    async def query_sql_example_by_table_id(table_id):
        with PostgresDB.get_session() as session:
            results = session.query(SqlExample).filter(SqlExample.table_id == table_id).all()
        sql_example_list = []
        for result in results:
            tmp_dict = {
                'sql_example_id': result.id,
                'question': result.question,
                'sql': result.sql
            }
            sql_example_list.append(tmp_dict)
        return sql_example_list

    @staticmethod
    async def get_topk_sql_example_by_cos_dis(question_vector, table_id_list=None, topk=3):
        with PostgresDB.get_session() as session:
            if table_id_list is not None:
                sql_example_list = session.query(
                    SqlExample
                ).filter(SqlExample.table_id.in_(table_id_list)).order_by(
                    SqlExample.question_vector.cosine_distance(question_vector)
                ).limit(topk).all()
            else:
                sql_example_list = session.query(
                    SqlExample
                ).order_by(
                    SqlExample.question_vector.cosine_distance(question_vector)
                ).limit(topk).all()
        sql_example_list = [
            {'table_id': sql_example.table_id, 'question': sql_example.question, 'sql': sql_example.sql}
            for sql_example in sql_example_list]
        return sql_example_list
