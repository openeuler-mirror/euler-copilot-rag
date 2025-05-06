# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.
from sqlalchemy import select, delete, and_
from typing import Dict
import uuid

from data_chain.logger.logger import logger as logging
from data_chain.entities.request_data import ListTeamRequest
from data_chain.entities.enum import TeamStatus
from data_chain.stores.database.database import DataBase, RoleEntity, ActionEntity, RoleActionEntity, UserRoleEntity


class RoleManager:
    @staticmethod
    async def add_role(role_entity: RoleEntity) -> RoleEntity:
        """添加角色"""
        try:
            async with await DataBase.get_session() as session:
                session.add(role_entity)
                await session.commit()
                await session.refresh(role_entity)
        except Exception as e:
            err = "添加角色失败"
            logging.exception("[RoleManager] %s", err)
            raise e
        return role_entity

    @staticmethod
    async def add_user_role(user_role_entity: UserRoleEntity) -> UserRoleEntity:
        """添加用户角色"""
        try:
            async with await DataBase.get_session() as session:
                session.add(user_role_entity)
                await session.commit()
                await session.refresh(user_role_entity)
        except Exception as e:
            err = "添加用户角色失败"
            logging.exception("[RoleManager] %s", err)
            raise e
        return user_role_entity

    @staticmethod
    async def add_action(action_entity: ActionEntity) -> ActionEntity:
        """添加操作"""
        try:
            async with await DataBase.get_session() as session:
                session.add(action_entity)
                await session.commit()
                await session.refresh(action_entity)
            return True
        except Exception as e:
            err = "添加操作失败"
            logging.warning("[RoleManager] %s", err)
            return False

    @staticmethod
    async def add_role_actions(role_action_entities: list[RoleActionEntity]) -> bool:
        """添加角色操作"""
        try:
            async with await DataBase.get_session() as session:
                for role_action_entity in role_action_entities:
                    session.add(role_action_entity)
                await session.commit()
                for role_action_entity in role_action_entities:
                    await session.refresh(role_action_entity)
        except Exception as e:
            err = "添加角色操作失败"
            logging.exception("[RoleManager] %s", err)
            raise e

    @staticmethod
    async def get_action_by_team_id_user_sub_and_action(
            user_sub: str, team_id: uuid.UUID, action: str) -> ActionEntity:
        """根据团队ID、用户ID和操作获取操作"""
        try:
            async with await DataBase.get_session() as session:
                stmt = select(ActionEntity).join(
                    RoleActionEntity, ActionEntity.action == RoleActionEntity.action).join(
                    UserRoleEntity, RoleActionEntity.role_id == UserRoleEntity.role_id).where(
                    and_(
                        UserRoleEntity.user_id == user_sub,
                        UserRoleEntity.team_id == team_id,
                        ActionEntity.action == action,
                    )
                )
                result = await session.execute(stmt)
                action_entity = result.scalars().first()
                return action_entity
        except Exception as e:
            err = "根据团队ID、用户ID和操作获取操作失败"
            logging.exception("[RoleManager] %s", err)
            raise e
