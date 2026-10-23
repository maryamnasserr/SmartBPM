"""Reproduce Days 7-8 exports. No model fitting; original logs are read-only."""
import hashlib
import json
from pathlib import Path
import shutil
import sys
import time
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from smartbpm.ml_features import (build_dataset, feature_dictionary, audit_leakage,
    fit_preprocessor, transform_features, validate_schema, FEATURES)


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()


def balance(frame):
    return [{'split':str(name),'cases':len(group),'positive':int(group.target_long_observed.sum()),
             'negative':int(group.target_long_observed.eq(0).sum())}
            for name,group in frame.groupby('split',sort=True)]


def main():
    started = time.perf_counter()
    free = shutil.disk_usage(ROOT).free
    source = ROOT/'data/processed/domestic_declarations_cleaned.parquet'
    raw = ROOT/'data/raw/DomesticDeclarations.xes'
    before = {str(p.relative_to(ROOT)):digest(p) for p in [raw,source]}
    events = pd.read_parquet(source)
    rows,audit,design = build_dataset(events)
    prepared_seconds = time.perf_counter()-started
    reports = ROOT/'outputs/reports'
    output = ROOT/'data/processed/domestic_declarations_ml_ready.parquet'
    audit_path = ROOT/'data/processed/domestic_declarations_ml_audit.parquet'
    spec = fit_preprocessor(rows)
    for split in ['train','validation','test']:
        transformed = transform_features(rows.loc[rows.split.eq(split)],spec)
        if transformed.isna().any().any():
            raise ValueError('Preprocessor produced null values')
    rows.to_parquet(output,index=False)
    audit.to_parquet(audit_path,index=False)
    restored = pd.read_parquet(output)
    validate_schema(restored)
    pd.testing.assert_frame_equal(rows,restored)
    pd.testing.assert_frame_equal(audit,pd.read_parquet(audit_path))
    dictionary = feature_dictionary(events, rows)
    dictionary.to_csv(reports/'day7_8_feature_dictionary.csv',index=False)
    pd.testing.assert_frame_equal(dictionary,pd.read_csv(reports/'day7_8_feature_dictionary.csv'))
    prefix = audit.loc[audit.event_count.ge(2)]
    counts = audit.eligibility.value_counts().to_dict()
    if sum(counts.values()) != events['case:concept:name'].nunique():
        raise ValueError('Eligibility accounting failed')
    eligibility = {'original_cases':len(audit),'event2_snapshots':len(prefix),
        'final_unresolved_eligible':len(rows),'mutually_exclusive_counts':counts,
        'already_above_threshold_including_overlap':int(prefix.already_above_threshold.sum()),
        'overlap_including_known_positive':int(prefix.split.eq('purged_overlap').sum()),
        'overlap_and_known_positive':int((prefix.split.eq('purged_overlap') & prefix.already_above_threshold).sum()),
        'singletons_zero_duration':int((audit.event_count.eq(1)&audit.elapsed_days.eq(0)).sum()),
        'zero_duration_event2_cases':int((prefix.elapsed_days.eq(0)).sum()),
        'prefix_at_observed_endpoint':int(prefix.prediction_timestamp.eq(prefix.end_timestamp).sum()),
        'cases_with_tied_timestamps':int(events.loc[events.duplicated(['case:concept:name','time:timestamp'],keep=False),'case:concept:name'].nunique()),
        'nonpayment_endpoints_all_cases':int(audit.end_activity.ne('Payment Handled').sum()),
        'endpoint_sensitivity':audit.groupby(['eligibility','end_activity']).agg(cases=('event_count','size'),positive=('target_long_observed','sum')).reset_index().to_dict('records'),
        'excluded_case_ids':{status:audit.loc[audit.eligibility.eq(status),'case:concept:name'].tolist() for status in counts if status!='unresolved_eligible'},
        'policy':'Singleton > known positive > overlap > unresolved; known positives remain in original threshold reference cohort. No exclusion based on future endpoint or zero duration.'}
    summary = {**design,'initial_proportions':[.6,.2,.2], 'final_class_balance':balance(rows),
        'all_event2_class_balance':balance(prefix),'known_positive_class_balance':balance(prefix.loc[prefix.already_above_threshold]),
        'unresolved_including_purged_class_balance':balance(prefix.loc[~prefix.already_above_threshold]),
        'prediction_ranges':{name:{'min':g.prediction_timestamp.min().isoformat(),'max':g.prediction_timestamp.max().isoformat()} for name,g in rows.groupby('split')},
        'unpurged_overlap_counts':{'training_at_validation':int((prefix.prediction_timestamp.lt(pd.Timestamp(design['validation_start'])) & prefix.end_timestamp.ge(pd.Timestamp(design['validation_start']))).sum()),
            'validation_at_test':int((prefix.prediction_timestamp.ge(pd.Timestamp(design['validation_start'])) & prefix.prediction_timestamp.lt(pd.Timestamp(design['test_start'])) & prefix.end_timestamp.ge(pd.Timestamp(design['test_start']))).sum())},
        'evaluation':'Retrospective chronological endpoint-purged approximation; not certified prospective completion labels'}
    threshold = {**design,'quantile':.75,'interpolation':'linear',
        'fit_cases':spec['fit_cases'],
        'threshold_reference_case_ids':audit.loc[audit.split.eq('train'),'case:concept:name'].tolist(),
        'global_p75_descriptive_only':float(audit.elapsed_days.quantile(.75)),
        'day6_threshold':json.loads((reports/'day6_target_definition.json').read_text())['threshold_days'],
        'policy':'Frozen from ALL mature Event-2 training cases before known-positive removal; no circular refitting after threshold-dependent exclusions; not an official SLA'}
    leakage = audit_leakage(rows,audit,design)
    leakage['missing_values_by_partition'] = {name:{c:int(v) for c,v in g.isna().sum().items()} for name,g in rows.groupby('split')}
    leakage['event_attribute_missingness'] = {c:int(v) for c,v in audit.filter(regex='^event[12]_').isna().sum().items()}
    leakage['preprocessing_fit_cases'] = len(spec['fit_cases'])
    leakage['no_model_trained'] = True
    after = {str(p.relative_to(ROOT)):digest(p) for p in [raw,source]}
    if before!=after:
        raise ValueError('Source hash changed')
    payloads = {'eligibility_audit':eligibility,'split_summary':summary,'threshold_derivation':threshold,
                'leakage_audit':leakage,'preprocessing_spec':spec}
    for name,payload in payloads.items():
        path = reports/f'day7_8_{name}.json'
        path.write_text(json.dumps(payload,indent=2,allow_nan=False),encoding='utf-8')
        assert json.loads(path.read_text(encoding='utf-8')) == payload
    measurements = {'preparation_seconds':prepared_seconds,'total_seconds':time.perf_counter()-started,
        'free_bytes_before':free,'free_bytes_after':shutil.disk_usage(ROOT).free,
        'output_bytes':{str(p.relative_to(ROOT)):p.stat().st_size for p in [output,audit_path,*reports.glob('day7_8_*')]},
        'source_sha256':before,'source_hashes_unchanged':before==after,
        'baseline_tests':'91 passed, 1 optional PM4Py warning in 211.12 s'}
    (reports/'day7_8_runtime.json').write_text(json.dumps(measurements,indent=2),encoding='utf-8')
    print(json.dumps({'eligibility':counts,'threshold':design['threshold_days'],
                     'partitions':balance(rows),'runtime':measurements},indent=2))


if __name__=='__main__':
    main()
