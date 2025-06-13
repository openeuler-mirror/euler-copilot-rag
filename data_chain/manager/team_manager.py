# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.
from sqlalchemy import select, update, delete, and_, func
from typing import Dict
import uuid

from data_chain.logger.logger import logger as logging
from data_chain.entities.request_data import ListTeamRequest
from data_chain.entities.enum import TeamStatus
from data_chain.stores.database.database import DataBase, TeamEntity, TeamUserEntity


class TeamManager:

    @staticmethod
    async def add_team(team_entity: TeamEntity) -> TeamEntity:
        """添加团队"""
        try:
            async with await DataBase.get_session() as session:
                session.add(team_entity)
                await session.commit()
                await session.refresh(team_entity)
        except Exception as e:
            err = "添加团队失败"
            logging.exception("[TeamManger] %s", err)
            raise e
        return team_entity

    @staticmethod
    async def add_team_user(team_user_entity: TeamUserEntity) -> TeamUserEntity:
        """添加团队成员"""
        try:
            async with await DataBase.get_session() as session:
                session.add(team_user_entity)
                await session.commit()
                await session.refresh(team_user_entity)
        except Exception as e:
            err = "添加团队成员失败"
            logging.exception("[TeamManger] %s", err)
        return team_user_entity

    @staticmethod
    async def list_team_myjoined_by_user_sub(user_sub: str, req: ListTeamRequest) -> list[TeamEntity]:
        """列出我加入的团队,以及总数"""
        try:
            async with await DataBase.get_session() as session:
                stmt = select(TeamEntity).join(TeamUserEntity, TeamEntity.id == TeamUserEntity.team_id).where(
                    and_(TeamUserEntity.user_id == user_sub,
                         TeamEntity.author_id != user_sub,
                         TeamEntity.status != TeamStatus.DELETED.value))
                if req.team_id:
                    stmt = stmt.where(TeamEntity.id == req.team_id)
                if req.team_name:
                    stmt = stmt.where(TeamEntity.name.ilike(f"%{req.team_name}%"))
                count_stmt = select(func.count()).select_from(stmt.subquery())
                total = (await session.execute(count_stmt)).scalar()
                stmt = stmt.limit(req.page_size).offset((req.page - 1) * req.page_size)
                stmt = stmt.order_by(TeamEntity.created_time.desc())
                result = await session.execute(stmt)
                team_entities = result.scalars().all()
                return (total, team_entities)
        except Exception as e:
            err = "列出我加入的团队失败"
            logging.exception("[TeamManager] %s", err)
            raise e

    @staticmethod
    async def list_team_mycreated_user_sub(user_sub: str, req: ListTeamRequest) -> list[TeamEntity]:
        """列出我创建的团队"""
        try:
            async with await DataBase.get_session() as session:
                stmt = select(TeamEntity).where(and_(
                    TeamEntity.author_id == user_sub, TeamEntity.status != TeamStatus.DELETED.value))
                if req.team_id:
                    stmt = stmt.where(TeamEntity.id == req.team_id)
                if req.team_name:
                    stmt = stmt.where(TeamEntity.name.ilike(f"%{req.team_name}%"))
                count_stmt = select(func.count()).select_from(stmt.subquery())
                total = (await session.execute(count_stmt)).scalar()
                stmt = stmt.limit(req.page_size).offset((req.page - 1) * req.page_size)
                stmt = stmt.order_by(TeamEntity.created_time.desc())
                result = await session.execute(stmt)
                team_entities = result.scalars().all()
                return (total, team_entities)
        except Exception as e:
            err = "列出我创建的团队失败"
            logging.exception("[TeamManager] %s", err)
            raise e

    @staticmethod
    async def list_all_team_user_created_or_joined(user_sub: str) -> list[TeamEntity]:
        """列出我创建或加入的团队"""
        try:
            async with await DataBase.get_session() as session:
                stmt = select(TeamEntity).where(and_(
                    TeamEntity.author_id == user_sub, TeamEntity.status != TeamStatus.DELETED.value))
                result = await session.execute(stmt)
                team_entities = result.scalars().all()
                stmt = select(TeamEntity).join(TeamUserEntity, TeamEntity.id == TeamUserEntity.team_id).where(
                    and_(TeamUserEntity.user_id == user_sub, TeamEntity.author_id != user_sub, TeamEntity.status != TeamStatus.DELETED.value))
                result = await session.execute(stmt)
                team_entities += result.scalars().all()
                team_entities.sort(key=lambda x: x.created_time, reverse=True)
                return team_entities
        except Exception as e:
            err = "列出我创建或加入的团队失败"
            logging.exception("[TeamManager] %s", err)
            raise e

    @staticmethod
    async def list_pulic_team(req: ListTeamRequest) -> list[TeamEntity]:
        """列出公开的团队"""
        try:
            async with await DataBase.get_session() as session:
                stmt = select(TeamEntity).where(and_(
                    TeamEntity.status != TeamStatus.DELETED.value, TeamEntity.is_public == True))
                if req.team_id:
                    stmt = stmt.where(TeamEntity.id == req.team_id)
                if req.team_name:
                    stmt = stmt.where(TeamEntity.name.ilike(f"%{req.team_name}%"))
                count_stmt = select(func.count()).select_from(stmt.subquery())
                total = (await session.execute(count_stmt)).scalar()
                stmt = stmt.limit(req.page_size).offset((req.page - 1) * req.page_size)
                stmt = stmt.order_by(TeamEntity.created_time.desc())
                result = await session.execute(stmt)
                team_entities = result.scalars().all()
                return (total, team_entities)
        except Exception as e:
            err = "列出公开的团队失败"
            logging.exception("[TeamManager] %s", err)
            raise e

    @staticmethod
    async def delete_team_by_id(team_id: uuid.UUID) -> uuid.UUID:
        """删除团队"""
        try:
            async with await DataBase.get_session() as session:
                stmt = delete(TeamEntity).where(TeamEntity.id == team_id)
                await session.execute(stmt)
                await session.commit()
        except Exception as e:
            err = "删除团队失败"
            logging.exception("[TeamManager] %s", err)
            raise e
        return team_id

    @staticmethod
    async def delete_teams_deleted() -> None:
        """删除团队"""
        try:
            async with await DataBase.get_session() as session:
                stmt = delete(TeamEntity).where(TeamEntity.status == TeamStatus.DELETED.value)
                await session.execute(stmt)
                await session.commit()
        except Exception as e:
            err = "删除团队失败"
            logging.exception("[TeamManager] %s", err)
            raise e

    @staticmethod
    async def update_team_by_id(team_id: uuid.UUID, team_dict: Dict[str, str]) -> TeamEntity:
        """更新团队"""
        try:
            async with await DataBase.get_session() as session:
                stmt = update(TeamEntity).where(TeamEntity.id == team_id).values(**team_dict)
                await session.execute(stmt)
                await session.commit()
                stmt = select(TeamEntity).where(TeamEntity.id == team_id)
                result = await session.execute(stmt)
                team_entity = result.scalars().first()
                return team_entity
        except Exception as e:
            err = "更新团队失败"
            logging.exception("[TeamManager] %s", err)
            raise e
