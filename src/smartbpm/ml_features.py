"""Event-2 snapshots and retrospective, overlap-purged ML preparation.

No classifier is fitted. Outcome columns live in a separate case audit.
"""
import json
import numpy as np
import pandas as pd
from smartbpm.dashboard import C
from smartbpm.process_mining import ordered_events
from smartbpm.performance import temporal_design, duration_labels

CATEGORICAL = ['first_activity', 'second_activity']
NUMERIC = ['prefix_elapsed_hours', 'utc_month', 'utc_weekday', 'utc_hour']
FEATURES = CATEGORICAL + NUMERIC
METADATA = [C.case, 'first_timestamp', 'second_timestamp', 'prediction_timestamp',
            'target_long_observed', 'split']


def extract_prefix(events):
    """Keep exactly positions 1 and 2; source order breaks timestamp ties.

    Duplicate records/IDs remain observations. Unique source provenance is required.
    Empty and malformed inputs fail explicitly, rather than create empty artifacts.
    """
    frame = ordered_events(events)
    if frame.empty:
        raise ValueError('ML preparation requires nonempty events')
    prefix = frame.groupby(C.case, sort=True).head(2).copy()
    prefix['position'] = prefix.groupby(C.case).cumcount() + 1
    return prefix


def prefix_features(events):
    prefix = extract_prefix(events)
    first = prefix.loc[prefix.position.eq(1)].set_index(C.case)
    second = prefix.loc[prefix.position.eq(2)].set_index(C.case)
    result = pd.DataFrame(index=second.index)
    result['first_activity'] = first[C.activity].reindex(second.index)
    result['second_activity'] = second[C.activity]
    result['first_timestamp'] = first[C.timestamp].reindex(second.index)
    result['second_timestamp'] = second[C.timestamp]
    result['prediction_timestamp'] = result.second_timestamp
    result['prefix_elapsed_hours'] = (result.second_timestamp-result.first_timestamp).dt.total_seconds()/3600
    for name, values in [('utc_month', result.prediction_timestamp.dt.month),
                         ('utc_weekday', result.prediction_timestamp.dt.dayofweek),
                         ('utc_hour', result.prediction_timestamp.dt.hour)]:
        result[name] = values.astype('int16')
    return result.reset_index()


def construct_target(days, threshold_days):
    """Strict >; equality is negative. Threshold must be explicitly supplied."""
    return duration_labels(days, threshold_days)


def assess_eligibility(audit, threshold_days):
    """Mutually exclusive priority: singleton, known-positive, overlap, unresolved."""
    result = audit.copy()
    known = result.prefix_elapsed_hours.gt(threshold_days*24)
    result['already_above_threshold'] = known
    result['eligibility'] = 'unresolved_eligible'
    result.loc[result.split.eq('purged_overlap'), 'eligibility'] = 'purged_overlap'
    result.loc[known, 'eligibility'] = 'already_over_threshold'
    result.loc[result.event_count.lt(2), 'eligibility'] = 'fewer_than_two_events'
    return result


def validate_schema(rows):
    if rows.empty or set(rows) != set(FEATURES + METADATA):
        raise ValueError('Unexpected ML schema or empty dataset')
    if rows[C.case].isna().any() or not rows[C.case].is_unique or not rows[C.case].map(lambda x: isinstance(x,str) and bool(x.strip())).all():
        raise ValueError('Case identifiers must be unique nonblank strings')
    if rows.isna().any().any():
        raise ValueError('Snapshot schema has unexpected nulls')
    if not rows.split.isin(['train','validation','test']).all() or not rows.target_long_observed.isin([0,1]).all():
        raise ValueError('Invalid partition or target')
    for name in ['first_timestamp','second_timestamp','prediction_timestamp']:
        if not isinstance(rows[name].dtype, pd.DatetimeTZDtype) or str(rows[name].dt.tz) != 'UTC':
            raise ValueError('Snapshot timestamps must be UTC aware')
    if not rows.second_timestamp.equals(rows.prediction_timestamp) or (rows.first_timestamp > rows.second_timestamp).any():
        raise ValueError('Invalid snapshot timestamps')
    expected = (rows.second_timestamp-rows.first_timestamp).dt.total_seconds()/3600
    if not np.allclose(expected, rows.prefix_elapsed_hours) or not np.isfinite(rows[NUMERIC].to_numpy(dtype=float)).all():
        raise ValueError('Invalid prefix numeric features')
    for name, expected in [('utc_month',rows.prediction_timestamp.dt.month),('utc_weekday',rows.prediction_timestamp.dt.dayofweek),('utc_hour',rows.prediction_timestamp.dt.hour)]:
        if not rows[name].eq(expected).all():
            raise ValueError('Calendar feature mismatch')
    for name in CATEGORICAL:
        if not rows[name].map(lambda x:isinstance(x,str) and bool(x.strip())).all():
            raise ValueError('Invalid activity feature')
    for earlier,later in [('train','validation'),('validation','test')]:
        a,b = rows.loc[rows.split.eq(earlier),'prediction_timestamp'], rows.loc[rows.split.eq(later),'prediction_timestamp']
        if a.empty or b.empty or a.max() >= b.min():
            raise ValueError('Partitions empty or not strictly chronological')


def feature_matrix(rows):
    """Explicit allowlist: never infer predictors from all non-target columns."""
    return rows.loc[:, FEATURES].copy()


def fit_preprocessor(rows):
    """Fit a simple serializable specification on unresolved training rows only.

    Median imputation, mean/std scaling and one-hot vocabulary. No feature selection.
    Unknown categories map to all-zero indicators; literal missing-like strings stay
    distinct from nulls. Required activity fields never have nulls in validated data.
    """
    training = rows.loc[rows.split.eq('train')]
    if training.empty:
        raise ValueError('No training data')
    x = feature_matrix(training)
    stats = {}
    for name in NUMERIC:
        values = pd.to_numeric(x[name],errors='raise')
        if np.isinf(values.dropna()).any():
            raise ValueError('Infinite feature values')
        median = float(values.median()) if values.notna().any() else 0.
        filled = values.fillna(median)
        stats[name] = {'median':median,'mean':float(filled.mean()),'scale':float(filled.std(ddof=0)) or 1.}
    return {'fit_cases':training[C.case].tolist(), 'numeric':stats,
            'categories':{name:sorted(x[name].dropna().unique().tolist()) for name in CATEGORICAL},
            'features':FEATURES, 'unknown_category':'all zero indicators', 'feature_selection':'none'}


def transform_features(rows, spec):
    if spec['features'] != FEATURES:
        raise ValueError('Preprocessor feature schema mismatch')
    x = feature_matrix(rows)
    result = pd.DataFrame(index=rows.index)
    for name in NUMERIC:
        stat = spec['numeric'][name]
        result[name] = (pd.to_numeric(x[name],errors='raise').fillna(stat['median'])-stat['mean'])/stat['scale']
    for name in CATEGORICAL:
        for value in spec['categories'][name]:
            result[json.dumps([name,value])] = x[name].eq(value).fillna(False).astype('int8')
    return result


def build_dataset(events):
    frame = ordered_events(events)
    snapshots = prefix_features(frame)
    cases = frame.groupby(C.case,sort=True).agg(event_count=(C.activity,'size'),
                start_timestamp=(C.timestamp,'first'),end_timestamp=(C.timestamp,'last'),end_activity=(C.activity,'last')).reset_index()
    cases['elapsed_days'] = (cases.end_timestamp-cases.start_timestamp).dt.total_seconds()/86400
    labels, design = temporal_design(cases, snapshots)
    audit = cases.merge(snapshots,on=C.case,how='left',validate='one_to_one').merge(
        labels[[C.case,'split','target_long_observed']],on=C.case,how='left',validate='one_to_one')
    audit['target_long_observed'] = construct_target(audit.elapsed_days,design['threshold_days'])
    prefix = extract_prefix(frame)
    for position in [1,2]:
        part = prefix.loc[prefix.position.eq(position)].set_index(C.case)
        for attribute in [C.resource,'org:role']:
            audit[f'event{position}_{attribute}'] = audit[C.case].map(part[attribute]) if attribute in part else pd.NA
    audit = assess_eligibility(audit,design['threshold_days'])
    rows = audit.loc[audit.eligibility.eq('unresolved_eligible'), FEATURES+METADATA].reset_index(drop=True)
    validate_schema(rows)
    audit_leakage(rows,audit,design)
    return rows, audit, design


def audit_leakage(rows, audit, design):
    validate_schema(rows)
    if not audit[C.case].is_unique or not set(rows[C.case]).issubset(set(audit[C.case])):
        raise ValueError('Case audit mismatch')
    selected = audit.set_index(C.case).loc[rows[C.case]]
    if not selected.eligibility.eq('unresolved_eligible').all() or not rows[C.case].tolist()==audit.loc[audit.eligibility.eq('unresolved_eligible'),C.case].tolist():
        raise ValueError('Eligibility mismatch')
    if rows.prefix_elapsed_hours.gt(design['threshold_days']*24).any():
        raise ValueError('Known positive in unresolved dataset')
    for name in FEATURES+METADATA[1:]:
        if not rows[name].reset_index(drop=True).equals(selected[name].reset_index(drop=True)):
            raise ValueError(f'Snapshot differs from case audit: {name}')
    if not np.array_equal(rows.target_long_observed, construct_target(selected.elapsed_days,design['threshold_days'])):
        raise ValueError('Outcome label mismatch')
    for split,boundary in [('train','validation_start'),('validation','test_start')]:
        if audit.loc[audit.split.eq(split),'end_timestamp'].ge(pd.Timestamp(design[boundary])).any():
            raise ValueError('Label overlaps evaluation cutoff')
    fitted = float(audit.loc[audit.split.eq('train'),'elapsed_days'].quantile(.75))
    if fitted != design['threshold_days']:
        raise ValueError('Threshold does not match training-only quantile')
    return {'checks_passed':True,'predictor_allowlist':FEATURES,
            'forbidden_model_inputs':METADATA+['elapsed_days','end_timestamp','end_activity','event_count','eligibility','already_above_threshold','case attributes','future events'],
            'threshold_training_cases':int(audit.split.eq('train').sum()),
            'label_availability':'Observed endpoints precede next cutoff; actual completion/censoring unknown',
            'resource_role_policy':'Sensitivity only: ingestion-time availability unverified',
            'test_policy':'Descriptive preparation audit only; no test-driven feature/model selection'}


def feature_dictionary(events, rows):
    records = []
    sources = {'first_activity':C.activity,'second_activity':C.activity,
               'prefix_elapsed_hours':C.timestamp,'utc_month':C.timestamp,'utc_weekday':C.timestamp,'utc_hour':C.timestamp}
    for name in rows:
        included = name in FEATURES
        records.append({'feature_name':name,'source_column':sources.get(name,name), 'data_type':str(rows[name].dtype),
            'available_at_prediction':'yes (recorded prefix)' if included or name.endswith('timestamp') or name==C.case else 'no / evaluation metadata',
            'transformation':{'first_activity':'position 1','second_activity':'position 2','prefix_elapsed_hours':'(event2-event1) seconds / 3600','utc_month':'event2 UTC month','utc_weekday':'event2 UTC weekday Monday=0','utc_hour':'event2 UTC hour'}.get(name,'audit / join metadata'),
            'missing_handling':'required: reject invalid; numeric train-median fallback' if included else 'not a predictor',
            'leakage_risk':'prefix-only; ingestion ordering assumption' if included else 'identifier, absolute time, label or partition must not enter model',
            'decision':'primary predictor' if included else 'forbidden model input'})
    for name in events:
        if name == C.case:
            continue
        sensitivity = name in [C.resource,'org:role']
        records.append({'feature_name':name,'source_column':name,'data_type':str(events[name].dtype),
            'available_at_prediction':'unverified as-of availability' if sensitivity or name.startswith('case:') else 'only first two event rows',
            'transformation':'none; raw event column excluded from matrix',
            'missing_handling':'not imputed in primary matrix; preserve raw null versus literal categories',
            'leakage_risk':'final trace attributes / identifiers / future rows / unverified ingestion',
            'decision':'sensitivity only (first/second event)' if sensitivity else 'excluded raw column; use approved derivations only'})
    return pd.DataFrame(records)
