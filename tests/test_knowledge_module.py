from app.modules.knowledge.service import KnowledgeService


def test_service_exists():
    assert KnowledgeService(repository=object()) is not None
