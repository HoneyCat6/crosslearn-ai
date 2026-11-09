import asyncio
from app.agent import orchestrate
from app.config import settings


def test_hanging_adapter_has_bounded_timeout(monkeypatch):
    class Hanging:
        async def choose(self, evidence):
            await asyncio.sleep(100)
    monkeypatch.setattr(settings, 'model_timeout_seconds', 0.01)
    result = asyncio.run(orchestrate({'sessions': []}, Hanging()))
    assert result['source'] == 'rules'
    assert result['error'] == 'model_timeout'
    assert result['output']['profile_status'] == 'INSUFFICIENT_EVIDENCE'


def test_model_cannot_claim_an_unsupported_concept_gap():
    class InventedGap:
        async def choose(self, evidence):
            return {'action': 'revisit_concept', 'concepts': ['moss']}
    result = asyncio.run(orchestrate({'sessions': []}, InventedGap()))
    assert result['source'] == 'rules'
    assert result['error'] == 'invalid_or_unavailable_model'
    assert result['output']['observed_strengths'] == []
