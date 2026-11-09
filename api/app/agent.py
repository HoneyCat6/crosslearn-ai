"""Bounded orchestration: verified metrics in, allowlisted instructional action out."""
import hashlib
import json
from typing import Literal, Protocol
import httpx
from pydantic import BaseModel, ConfigDict, Field
from .config import settings


class ActionChoice(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    action: Literal['collect_more_evidence', 'revisit_concept']
    concepts: list[Literal['root', 'moss', 'stem']] = Field(max_length=3)


class ModelAdapter(Protocol):
    async def choose(self, evidence: dict) -> dict: ...


class OllamaAdapter:
    async def choose(self, evidence):
        headers = {'Authorization': f'Bearer {settings.model_api_key}'} if settings.model_api_key else {}
        body = {
            'model': settings.model_name, 'stream': False,
            'format': ActionChoice.model_json_schema(),
            'options': {'temperature': 0, 'num_predict': 160},
            'messages': [
                {'role': 'system', 'content': 'Select a provisional teacher action from the schema. Only use provided evidence. Revisit only concepts with incorrect post-test answers. Do not diagnose or label learners. No external tools or URLs are available.'},
                {'role': 'user', 'content': json.dumps(evidence, sort_keys=True)},
            ],
        }
        async with httpx.AsyncClient(timeout=settings.model_timeout_seconds, follow_redirects=False) as client:
            async with client.stream('POST', settings.model_endpoint, json=body, headers=headers) as response:
                response.raise_for_status()
                data = bytearray()
                async for chunk in response.aiter_bytes():
                    data.extend(chunk)
                    if len(data) > 32768:
                        raise ValueError('oversized_output')
        return json.loads(json.loads(data)['message']['content'])


def configured_adapter():
    return OllamaAdapter() if settings.model_provider == 'ollama' and settings.model_name else None


class EvidenceTools:
    """Tools operate only on the already-authorized snapshot, with no DB/network access."""
    def __init__(self, evidence):
        self.evidence = json.loads(json.dumps(evidence))
        self.trace = []

    def get_learner_evidence(self):
        self.trace.append('get_learner_evidence')
        return self.evidence

    def compare_trials(self):
        self.trace.append('compare_trials')
        return {'status': 'INSUFFICIENT_EVIDENCE', 'missed': sorted({r['concept'] for s in self.evidence['sessions'] for r in s['metrics'] if r['post_correct'] < r['post_total']})}

    def get_approved_explanations(self):
        self.trace.append('get_approved_explanations')
        return self.evidence.get('approved_explanations', [])

    def draft_teacher_recommendation(self, choice):
        self.trace.append('draft_teacher_recommendation')
        words = ', '.join(c.upper() for c in choice.concepts)
        if choice.action == 'revisit_concept':
            return f'Revisit {words} using an approved explanation. Ask the pupil to explain the idea in their own words.'
        return 'Collect evidence using new equivalent questions and later retention checks before choosing an explanation pattern.'

    def request_followup_assessment(self):
        self.trace.append('request_followup_assessment')
        return 'Teacher to select a new calibrated application item; repeated demo questions are practice, not independent evidence.'


async def orchestrate(evidence, adapter=None):
    # No identity, teacher notes, raw pupil text or original answer payloads reach a model.
    tools = EvidenceTools(evidence)
    evidence = tools.get_learner_evidence()
    missed = tools.compare_trials()['missed']
    evidence['approved_explanations'] = tools.get_approved_explanations()
    choice = ActionChoice(action='revisit_concept' if missed else 'collect_more_evidence', concepts=missed)
    source, error = 'rules', None
    if adapter:
        try:
            import asyncio
            raw = await asyncio.wait_for(adapter.choose(evidence), timeout=settings.model_timeout_seconds)
            candidate = ActionChoice.model_validate(raw)
            if candidate.action == 'revisit_concept' and (not candidate.concepts or not set(candidate.concepts) <= set(missed)):
                raise ValueError('unsupported_evidence')
            choice = candidate
            source = 'model'
        except Exception as exc:
            error = 'model_timeout' if isinstance(exc, TimeoutError) else 'invalid_or_unavailable_model'
    action = tools.draft_teacher_recommendation(choice)
    followup = tools.request_followup_assessment()
    output = {
        'profile_status': 'INSUFFICIENT_EVIDENCE',
        'observed_strengths': [],
        'misconceptions': [f'Check understanding of {c.upper()}; an incorrect answer alone does not diagnose a misconception.' for c in missed],
        'suggested_explanation_sequence': ['teacher-selected approved explanation', 'new application question'],
        'teacher_action': action,
        'next_assessment': followup,
        'evidence_summary': f"{len(evidence['sessions'])} completed synthetic session(s). The same uncalibrated item bank does not establish a reliable modality pattern.",
        'limitations': ['two questions per concept', 'uncalibrated content', 'repeated items', 'no delayed retention', 'baseline follows crossword discovery'],
        'requires_teacher_review': True,
    }
    tools.trace.append('validate_recommendation')
    return {'output': output, 'source': source, 'error': error, 'trace': tools.trace,
            'input_hash': hashlib.sha256(json.dumps(evidence, sort_keys=True).encode()).hexdigest()}
