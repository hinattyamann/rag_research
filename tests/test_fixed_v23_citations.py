"""Citation transport prevents invented quotes and preserves existing anonymous labels."""

import sys
from pathlib import Path

import jsonschema
import pytest
from test_fixed_v23_automation import config as base_config  # noqa: F401
from test_fixed_v23_automation import fake_annotations, packets

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts/fixed_v23_automation'))
import citations  # noqa: E402
import common  # noqa: E402
import pipeline  # noqa: E402
import review  # noqa: E402


@pytest.fixture
def config(base_config):  # noqa: F811
    return base_config


def payload(config, kind='units', language='en'):
    run = Path(config['cal_run'])
    folder = run / language / 'quality'
    if kind == 'units':
        folder /= 'units'
    packet = common.read(folder / 'packet.json')
    annotations = common.read(folder / 'annotations.blank.json')['annotations']
    return {'cohort': 'cal', 'language': language, 'kind': kind, 'cases': packet['cases'],
            'annotations': [{k: v for k, v in a.items() if k not in review.META} for a in annotations]}


def selected_output(value, binding):
    rows = fake_annotations(value)['annotations']
    output = {}
    for (slot, template), row in zip(binding['slots'].items(), rows, strict=True):
        codes = [k for k, v in binding['catalog'].items() if v['annotation_id'] == template['annotation_id'] and v['source'] == 'actual']
        decision = {k: v for k, v in row.items() if k in {'label', 'reason', 'criteria', 'essential_points'}}
        decision['evidence'] = [codes[0]]
        output[slot] = decision
    return {'annotations': output}


@pytest.mark.parametrize('kind,language', [('quality', 'en'), ('units', 'en'), ('units', 'ja')])
def test_schema_and_decoder_bind_every_slot_to_exact_original_documents(config, kind, language):
    packets(Path(config['cal_run']))
    value = payload(config, kind, language)
    binding, schema = citations.prepare(value, kind)
    output = selected_output(value, binding)
    jsonschema.Draft202012Validator.check_schema(schema)
    jsonschema.validate(output, schema)
    decoded = citations.decode(output, binding, kind)
    assert len(decoded['annotations']) == len(value['annotations'])
    for row, template in zip(decoded['annotations'], value['annotations'], strict=True):
        assert row['annotation_id'] == template['annotation_id']
        if kind == 'units':
            assert row['claim_id'] == template['claim_id'] and row['claim_text_sha256'] == template['claim_text_sha256']
        documents = next(c['documents'] for c in value['cases'] if c['annotation_id'] == row['annotation_id'])
        assert all(any(e['passage_id'] == d['passage_id'] and e['quote'] == d['text'] for d in documents) for e in row['evidence'])


@pytest.mark.parametrize('bad', ['no_evidence', 'unknown_citation', 'other_candidate', 'missing_slot', 'changed_identity'])
def test_schema_or_decoder_rejects_missing_support_and_wrong_identity_or_source(config, bad):
    packets(Path(config['cal_run']))
    value = payload(config)
    binding, schema = citations.prepare(value, 'units')
    output = selected_output(value, binding)
    first = next(iter(output['annotations']))
    if bad == 'no_evidence':
        output['annotations'][first]['evidence'] = []
    elif bad == 'unknown_citation':
        output['annotations'][first]['evidence'] = ['invented quotation']
    elif bad == 'other_candidate':
        output['annotations'][first]['evidence'] = [next(k for k, v in binding['catalog'].items() if v['annotation_id'] != binding['slots'][first]['annotation_id'])]
    elif bad == 'missing_slot':
        del output['annotations'][first]
    else:
        output['annotations'][first]['claim_id'] = 'changed'
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(output, schema)
    with pytest.raises(citations.AnnotationFormatError):
        citations.decode(output, binding, 'units')


def test_quality_schema_rejects_label_criteria_mismatch_and_reference_only_reliable(config):
    packets(Path(config['cal_run']))
    value = payload(config, 'quality')
    binding, schema = citations.prepare(value, 'quality')
    output = selected_output(value, binding)
    first = next(iter(output['annotations']))
    output['annotations'][first]['criteria']['context_support'] = 'fail'
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(output, schema)
    output = selected_output(value, binding)
    reference = next(k for k, v in binding['catalog'].items() if v['annotation_id'] == binding['slots'][first]['annotation_id'] and v['source'] == 'reference')
    output['annotations'][first]['evidence'] = [reference]
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(output, schema)
    with pytest.raises(citations.AnnotationFormatError, match='actual context'):
        citations.decode(output, binding, 'quality')


def test_anonymous_citation_transport_repairs_once_and_seals_both_languages(config, monkeypatch):
    run = Path(config['cal_run'])
    packets(run)
    config['annotation_transport'] = 'inline_citations_v3'
    config['maximum_cli_invocations'] = 12
    monkeypatch.setattr(review, 'cli_auth', lambda config: None)
    calls = []

    def invoke(argv, *, receipt, stdin_path, **kwargs):
        inline = common.read(stdin_path)
        value, binding = inline['annotation_input'], inline['citation_binding']
        assert 'GOLD-SECRET' not in str(inline) if value['kind'] == 'units' else True
        result = selected_output(value, binding)
        calls.append((value['language'], value['kind']))
        if calls == [('en', 'quality')]:
            result['annotations'][next(iter(result['annotations']))]['evidence'] = ['unknown']
        common.write(receipt, {'exit_code': 0, 'elapsed_seconds': 1., 'finished_at_utc': '2026-11-04T00:00:00+00:00'})
        receipt.with_suffix('.log').write_text('')
        common.write(Path(argv[argv.index('--output-last-message') + 1]), result)
        return common.read(receipt)

    monkeypatch.setattr(review, 'run_owned', invoke)
    review.complete_annotations(config, run, 'cal')
    pipeline.verify_seal(run)
    assert len(calls) == 5
    assert len(common.read(Path(config['state_dir']) / 'cli_ledger.json')['invocations']) == 5
    assert list((Path(config['state_dir']) / 'jobs').glob('*/attempt-0/validation_error.json'))
    saved = common.sha(run / 'all_annotations.seal.json')
    review.complete_annotations(config, run, 'cal')
    assert len(calls) == 5 and common.sha(run / 'all_annotations.seal.json') == saved


def test_migration_reuses_legacy_validated_jobs_without_modifying_or_resending_them(config, monkeypatch):
    run = Path(config['cal_run'])
    packets(run)
    config.update(annotation_cases_per_job=1, maximum_cli_invocations=20)
    monkeypatch.setattr(review, 'cli_auth', lambda config: None)
    calls = []

    def invoke(argv, *, receipt, stdin_path, **kwargs):
        if receipt.exists():
            return common.read(receipt)
        if 'cal-en-units-001-inline-v2' in str(receipt):
            raise ValueError('synthetic rejected legacy job')
        inline = common.read(stdin_path)
        value = inline['annotation_input']
        result = selected_output(value, inline['citation_binding']) if 'citation_binding' in inline else fake_annotations(value)
        calls.append(str(receipt))
        common.write(receipt, {'exit_code': 0, 'elapsed_seconds': 1., 'finished_at_utc': '2026-11-04T00:00:00+00:00'})
        receipt.with_suffix('.log').write_text('')
        common.write(Path(argv[argv.index('--output-last-message') + 1]), result)
        return common.read(receipt)

    monkeypatch.setattr(review, 'run_owned', invoke)
    with pytest.raises(ValueError, match='rejected legacy'):
        review.complete_annotations(config, run, 'cal')
    legacy = Path(config['state_dir']) / 'jobs/cal-en-units-000-inline-v2'
    hashes = {str(p): common.sha(p) for p in legacy.rglob('*') if p.is_file()}
    count = len(calls)
    config['annotation_transport'] = 'inline_citations_v3'
    review.complete_annotations(config, run, 'cal')
    assert all(common.sha(p) == s for p, s in hashes.items())
    assert not any('cal-en-units-000-' in p for p in calls[count:])
    assert any('cal-en-units-001-citations-v3' in p for p in calls[count:])
    pipeline.verify_seal(run)
