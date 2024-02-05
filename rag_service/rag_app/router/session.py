from fastapi import APIRouter
from rag_service.logger import get_logger, Module
from rag_service.session.session_manager import get_session_manager

router = APIRouter(prefix='/session', tags=['Session'])
logger = get_logger(module=Module.APP)
session_manager = get_session_manager()


@router.get('/generate_session')
def generate_session() -> str:
    return session_manager.generate_session()


@router.get('/clear_session')
def clear_session(session_id: str):
    session_id = session_manager.clear_session(session_id)
    if session_id == "":
        return f'Session id not exist<{session_id}>.'
    return f'Successfully clear session <{session_id}>.'


@router.get('/list_session')
def list_session():
    return session_manager.list_session()


@router.get('/list_history')
def list_history(session_id: str):
    return session_manager.list_history(session_id)
