"""Versioned, server-only answer keys and deterministic evidence calculations."""
import json
from pathlib import Path


def seed_content():
    return json.loads((Path(__file__).parent / 'science-demo-v1.json').read_text(encoding='utf-8'))


def validate_content(data):
    assert len(data['concepts']) == 3
    ids = {c['id'] for c in data['concepts']}
    assert len(ids) == 3
    grid = {}
    for c in data['concepts']:
        assert c['direction'] in ['across', 'down']
        for i, letter in enumerate(c['word']):
            r, col = c['row'] + (i if c['direction'] == 'down' else 0), c['col'] + (i if c['direction'] == 'across' else 0)
            assert 0 <= r < 4 and 0 <= col < 5
            assert (r, col) not in grid or grid[r, col] == letter
            grid[r, col] = letter
    all_ids = []
    for phase in ['baseline', 'post']:
        assert len(data[phase]) == 6
        for cid in ids:
            assert len([q for q in data[phase] if q['concept'] == cid]) == 2
        for q in data[phase]:
            assert q['concept'] in ids and 0 <= q['answer'] < len(q['options'])
            all_ids.append(q['id'])
    assert len(set(all_ids)) == 12


def modes(data, rotation):
    return {c['id']: ['text', 'audio', 'visual'][(i + rotation) % 3] for i, c in enumerate(data['concepts'])}


def metrics(data, responses, rotation):
    answers = {r.item_id: r.chosen_option for r in responses}
    output = []
    for c in data['concepts']:
        row = {'concept': c['id'], 'word': c['word'], 'modality': modes(data, rotation)[c['id']]}
        for phase in ['baseline', 'post']:
            items = [q for q in data[phase] if q['concept'] == c['id']]
            row[phase + '_correct'] = sum(answers.get(q['id']) == q['answer'] for q in items)
            row[phase + '_total'] = len(items)
            row[phase + '_answered'] = sum(q['id'] in answers for q in items)
        row['gain_pp'] = 50 * (row['post_correct'] - row['baseline_correct'])
        output.append(row)
    return output
