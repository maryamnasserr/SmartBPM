"""Independent UAT calculations: XML/Pandas/Counter, without analytical helpers."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import time
import xml.etree.ElementTree as ET
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
CASE,ACT,TIME='case:concept:name','concept:name','time:timestamp'


def sha(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def audit():
    tick=time.perf_counter()
    raw=ROOT/'data/raw/DomesticDeclarations.xes'
    source=ROOT/'data/processed/domestic_declarations_cleaned.parquet'
    rows=pd.read_parquet(source).sort_values([CASE,TIME,'_source_order'],kind='stable')
    raw_records=[]
    for _,trace in ET.iterparse(raw,events=['end']):
        if trace.tag.rsplit('}',1)[-1]!='trace':continue
        attrs={c.get('key'):c.get('value') for c in trace if c.tag.rsplit('}',1)[-1]!='event'}
        for event in trace:
            if event.tag.rsplit('}',1)[-1]!='event':continue
            values={c.get('key'):c.get('value') for c in event}
            raw_records.append((attrs['concept:name'],values['concept:name'],pd.Timestamp(values['time:timestamp']).tz_convert('UTC')))
        trace.clear()
    raw_frame=pd.DataFrame(raw_records,columns=[CASE,ACT,TIME])
    loaded=rows.sort_values('_source_order')[[CASE,ACT,TIME]].reset_index(drop=True)
    pd.testing.assert_frame_equal(raw_frame,loaded,check_dtype=False)
    sequences=rows.groupby(CASE,sort=True)[ACT].agg(tuple)
    variants=Counter(sequences)
    transitions=Counter(pair for sequence in sequences for pair in zip(sequence,sequence[1:]))
    cases=rows.groupby(CASE,sort=True).agg(first=(TIME,'first'),last=(TIME,'last'),events=(ACT,'size'))
    cases['days']=(cases['last']-cases['first']).dt.total_seconds()/86400
    second=rows.loc[rows.groupby(CASE).cumcount().eq(1)].set_index(CASE)
    first=rows.groupby(CASE).head(1).set_index(CASE)
    cohort=cases.join(second[TIME].rename('prediction_timestamp'),how='inner')
    times=cohort.prediction_timestamp.sort_values()
    validation,test=times.iloc[int(len(times)*.6)],times.iloc[int(len(times)*.8)]
    cohort['split']='test'
    cohort.loc[cohort.prediction_timestamp.lt(test),'split']='validation'
    cohort.loc[cohort.prediction_timestamp.lt(validation),'split']='train'
    overlap=(cohort.split.eq('train')&cohort['last'].ge(validation))|(cohort.split.eq('validation')&cohort['last'].ge(test))
    cohort.loc[overlap,'split']='purged_overlap'
    threshold=float(cohort.loc[cohort.split.eq('train'),'days'].quantile(.75))
    cohort['target']=(cohort.days>threshold).astype('int8')
    cohort['elapsed_hours']=(cohort.prediction_timestamp-cohort['first']).dt.total_seconds()/3600
    known=cohort.elapsed_hours.gt(threshold*24)
    final=cohort.loc[~known&~overlap]
    exported=pd.read_parquet(ROOT/'data/processed/domestic_declarations_ml_ready.parquet').set_index(CASE)
    assert set(exported.index)==set(final.index) and exported.index.is_unique
    expected={'first_activity':first[ACT].reindex(final.index),'second_activity':second[ACT].reindex(final.index),
              'prefix_elapsed_hours':final.elapsed_hours,'utc_month':final.prediction_timestamp.dt.month,
              'utc_weekday':final.prediction_timestamp.dt.dayofweek,'utc_hour':final.prediction_timestamp.dt.hour,
              'first_timestamp':final['first'],'second_timestamp':final.prediction_timestamp,
              'prediction_timestamp':final.prediction_timestamp,'target_long_observed':final.target,'split':final.split}
    assert set(exported)==set(expected)
    for name,value in expected.items():
        pd.testing.assert_series_equal(exported[name].sort_index(),value.sort_index(),check_names=False,check_dtype=False)
    spec=json.loads((ROOT/'outputs/reports/day7_8_preprocessing_spec.json').read_text())
    train=exported.loc[exported.split.eq('train')]
    assert set(spec['fit_cases'])==set(train.index)
    for name,stat in spec['numeric'].items():
        assert stat['median']==float(train[name].median())
        assert stat['mean']==float(train[name].mean())
        assert stat['scale']==(float(train[name].std(ddof=0)) or 1.)
    for name,vocabulary in spec['categories'].items():assert vocabulary==sorted(train[name].unique())
    saved=json.loads((ROOT/'outputs/reports/day7_8_split_summary.json').read_text())
    assert saved['threshold_days']==threshold
    assert saved['validation_start']==validation.isoformat() and saved['test_start']==test.isoformat()
    reported= pd.read_csv(ROOT/'outputs/reports/day5_transitions.csv')
    assert transitions==Counter({(r.source,r.target):int(r.frequency) for r in reported.itertuples()})
    fingerprints=json.loads((ROOT/'outputs/reports/preprocessing_report.json').read_text())
    assert sha(raw)==fingerprints['source_sha256'] and sha(source)==fingerprints['output_sha256']
    activity=rows[ACT].value_counts().to_dict()
    resource=rows['org:resource'].value_counts(dropna=False).to_dict()
    walkthrough_id=rows.loc[rows[ACT].eq('Declaration FOR_APPROVAL by ADMINISTRATION'),CASE].iloc[0]
    history=rows.loc[rows[CASE].eq(walkthrough_id)]
    history_json=[{'activity':r[ACT],'timestamp':r[TIME].isoformat(),'resource':r['org:resource']} for _,r in history.iterrows()]
    report={'checks_passed':True,'independent_method':'Raw XES XML matched source-order cleaned case/activity/time rows; Pandas groupby and Counter; no SmartBPM analytics imported',
        'cases':len(cases),'events':len(rows),'activities':len(activity),'variants':len(variants),
        'relationships':len(transitions),'transition_occurrences':sum(transitions.values()),
        'repeating_cases':sum(len(s)!=len(set(s)) for s in sequences),
        'duration_days':{name:float(value) for name,value in cases.days.describe(percentiles=[.5,.75,.9,.95]).items()},
        'threshold_days':threshold,'validation_start':validation.isoformat(),'test_start':test.isoformat(),
        'event2_cases':len(cohort),'singletons':int(cases.events.eq(1).sum()),'known_positive':int(known.sum()),
        'purged_overlap':int(overlap.sum()),'known_positive_and_overlap':int((known&overlap).sum()),
        'final_ml_cases':len(final),'partitions':final.groupby('split').agg(cases=('target','size'),positive=('target','sum')).reset_index().to_dict('records'),
        'activity_frequency':activity,'resource_frequency':resource,
        'top_variant_cases':[count for _,count in variants.most_common(5)],
        'walkthrough':{'case_id':walkthrough_id,'events':len(history),'elapsed_days':float(cases.loc[walkthrough_id,'days']),
                       'history':history_json,'ml_row':json.loads(exported.loc[[walkthrough_id]].reset_index().to_json(orient='records',date_format='iso')) if walkthrough_id in exported.index else []},
        'source_sha256':{str(p.relative_to(ROOT)):sha(p) for p in [raw,source]},'elapsed_seconds':time.perf_counter()-tick}
    out=ROOT/'outputs/reports/uat_data_audit.json'
    out.write_text(json.dumps(report,indent=2,allow_nan=False),encoding='utf-8')
    print(json.dumps(report,indent=2))
    return report


if __name__=='__main__':audit()
