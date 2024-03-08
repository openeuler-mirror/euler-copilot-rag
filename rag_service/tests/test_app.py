from fastapi.testclient import TestClient

from rag_service.rag_app.router.knowledge_base_api import router

test_client = TestClient(app=router)


def test_get_stream_answer():
    res = test_client.post(
        "/kb/get_stream_answer",
        json={'question': '介绍一下openEuler', 'kb_sn': 'openEuler_f79cc628', 'top_k': 5, 'fetch_source': False})
    assert res.status_code == 200
