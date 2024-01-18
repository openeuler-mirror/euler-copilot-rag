# -*- coding: utf-8 -*-
from sqlmodel import Session, select

from rag_service.exceptions import KnowledgeBaseNotExistsException
from rag_service.models.database.models import KnowledgeBase


def validate_knowledge_base(
        session: Session,
        knowledge_base_serial_number: str
) -> KnowledgeBase:
    knowledge_base = session.exec(
        select(KnowledgeBase)
        .where(KnowledgeBase.sn == knowledge_base_serial_number)
    ).one_or_none()

    if not knowledge_base:
        raise KnowledgeBaseNotExistsException(
            f'Knowledge base <{knowledge_base_serial_number}> not exists.')

    return knowledge_base
