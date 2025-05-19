# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.
import uuid
from data_chain.logger.logger import logger as logging
from data_chain.entities.request_data import ListTeamRequest, CreateTeamRequest
from data_chain.entities.response_data import ListTeamMsg
from data_chain.entities.enum import TeamType, TeamStatus
from data_chain.entities.common import default_roles
from data_chain.stores.database.database import TeamEntity
from data_chain.apps.base.convertor import Convertor
from data_chain.manager.team_manager import TeamManager
from data_chain.manager.role_manager import RoleManager


class TeamService:
    """团队服务"""
    @staticmethod
    async def validate_user_action_in_team(
            user_sub: str, team_id: uuid.UUID, action: str) -> bool:
        """验证用户在团队中的操作权限"""
        try:
            action_entity = await RoleManager.get_action_by_team_id_user_sub_and_action(user_sub, team_id, action)
            if action_entity is None:
                return False
            return True
        except Exception as e:
            err = "验证用户在团队中的操作权限失败"
            logging.exception("[TeamService] %s", err)
            raise e

    @staticmethod
    async def list_teams(user_sub: str, req: ListTeamRequest) -> ListTeamMsg:
        """列出团队"""
        if req.team_type == TeamType.MYCREATED:
            total, team_entities = await TeamManager.list_team_mycreated_user_sub(user_sub, req)
        elif req.team_type == TeamType.MYJOINED:
            total, team_entities = await TeamManager.list_team_myjoined_by_user_sub(user_sub, req)
        elif req.team_type == TeamType.PUBLIC:
            total, team_entities = await TeamManager.list_pulic_team(req)
        else:
            total_mycreated, team_entities_mycreated = await TeamManager.list_team_mycreated_user_sub(user_sub, req)
            total_myjoined, team_entities_myjoined = await TeamManager.list_team_myjoined_by_user_sub(user_sub, req)
            total = total_mycreated + total_myjoined
            team_entities = team_entities_mycreated + team_entities_myjoined
            team_entities.sort(key=lambda x: x.created_time, reverse=True)
        teams = []
        for team_entity in team_entities:
            team = await Convertor.convert_team_entity_to_team(team_entity)
            teams.append(team)
        return ListTeamMsg(total=total, teams=teams)

    @staticmethod
    async def create_team(user_sub: str, req: CreateTeamRequest) -> uuid.UUID:
        """创建团队"""
        try:
            team_entity = await Convertor.convert_create_team_request_to_team_entity(user_sub, req)
            team_entity = await TeamManager.add_team(team_entity)
            team_user_entity = await Convertor.convert_user_sub_and_team_id_to_team_user_entity(user_sub, team_entity.id)
            await TeamManager.add_team_user(team_user_entity)
            become_creator_flag = False
            for role_dict in default_roles:
                role_entity = await Convertor.convert_default_role_dict_to_role_entity(team_entity.id, role_dict)
                role_entity = await RoleManager.add_role(role_entity)
                if not become_creator_flag:
                    user_role_entity = await Convertor.convert_user_sub_role_id_and_team_id_to_user_role_entity(
                        user_sub, role_entity.id, team_entity.id)
                    await RoleManager.add_user_role(user_role_entity)
                    become_creator_flag = True
                role_action_entities = await Convertor.convert_default_role_action_dicts_to_role_action_entities(role_entity.id, role_dict['actions'])
                await RoleManager.add_role_actions(role_action_entities)
            return team_entity.id
        except Exception as e:
            err = "创建团队失败"
            logging.exception("[TeamService] %s", err)
            raise e

    @staticmethod
    async def update_team_by_team_id(
            user_sub: str, team_id: uuid.UUID, req: CreateTeamRequest) -> bool:
        """更新团队"""
        try:
            team_dict = await Convertor.convert_update_team_request_to_dict(req)
            team_entity = await TeamManager.update_team_by_id(team_id, team_dict)
            if team_entity is None:
                err = "更新团队失败"
                logging.exception("[TeamService] %s", err)
                raise "更新团队失败, 团队不存在"
            return team_entity.id
        except Exception as e:
            err = "更新团队失败"
            logging.exception("[TeamService] %s", err)
            raise e

    @staticmethod
    async def soft_delete_team_by_team_id(
            team_id: uuid.UUID) -> bool:
        """软删除团队"""
        try:
            team_entity = await TeamManager.update_team_by_id(
                team_id, {"status": TeamStatus.DELETED.value})
            if team_entity is None:
                err = "软删除团队失败"
                logging.exception("[TeamService] %s", err)
                raise "软删除团队失败, 团队不存在"
            return team_entity.id
        except Exception as e:
            err = "软删除团队失败"
            logging.exception("[TeamService] %s", err)
            raise e
