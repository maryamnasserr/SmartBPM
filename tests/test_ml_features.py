"""Known-answer snapshots, leakage mutations, partition and artifact checks."""
from pathlib import Path
import json
import pandas as pd
import pytest
from smartbpm.dashboard import C
from smartbpm.ml_features import (FEATURES, METADATA, NUMERIC, extract_prefix,
    prefix_features, construct_target, build_dataset, assess_eligibility,
    validate_schema, audit_leakage, fit_preprocessor, transform_features, feature_matrix)

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def log():
    records=[]
    for i in range(20):
        start=pd.Timestamp('2020-01-01',tz='UTC')+pd.Timedelta(days=30*i)
        for name,offset in [('Submit',pd.Timedelta(0)),('Review',pd.Timedelta(hours=1)),('End',pd.Timedelta(days=i+1))]:
            records.append({C.case:f'case-{i:02}', C.activity:name,C.timestamp:start+offset,
                            '_source_order':len(records),C.resource:'Staff','org:role':'Role','id':'duplicate-id','case:Amount':100})
    return pd.DataFrame(records)


def test_exact_two_events_prediction_time_and_elapsed(log):
    prefix=extract_prefix(log)
    assert prefix.groupby(C.case).size().eq(2).all()
    features=prefix_features(log)
    assert features.first_activity.eq('Submit').all()
    assert features.second_activity.eq('Review').all()
    assert features.prefix_elapsed_hours.eq(1).all()
    assert features.prediction_timestamp.equals(features.second_timestamp)
    assert features.iloc[0].prediction_timestamp==pd.Timestamp('2020-01-01T01:00Z')
    assert features[C.case].tolist()==[f'case-{i:02}' for i in range(20)]


def test_ties_and_duplicate_records_retained(log):
    log.loc[:2,C.timestamp]=log.iloc[0][C.timestamp]
    prefix=prefix_features(log.sample(frac=1,random_state=10))
    assert prefix.iloc[0].second_activity=='Review'
    assert prefix.iloc[0].prefix_elapsed_hours==0
    duplicate=log.iloc[[0]].copy()
    duplicate['_source_order']=1000
    duplicate[C.case]='duplicate-case'
    other=duplicate.copy();other['_source_order']=1001
    extra=pd.concat([log,duplicate,other],ignore_index=True)
    assert prefix_features(extra).set_index(C.case).loc['duplicate-case','prefix_elapsed_hours']==0


def test_singletons_and_accounting(log):
    log=log.drop(index=[1,2])
    rows,audit,design=build_dataset(log)
    assert len(audit)==20 and len(rows)==19
    assert audit.set_index(C.case).loc['case-00','eligibility']=='fewer_than_two_events'
    assert audit.eligibility.value_counts().sum()==20


@pytest.mark.parametrize('problem',['empty','missing','null','naive','duplicate_source','bad_source','numeric_id'])
def test_invalid_inputs(log,problem):
    if problem=='empty':log=log.iloc[:0]
    elif problem=='missing':log=log.drop(columns=C.activity)
    elif problem=='null':log.loc[0,C.timestamp]=pd.NaT
    elif problem=='naive':log[C.timestamp]=log[C.timestamp].dt.tz_localize(None)
    elif problem=='duplicate_source':log['_source_order']=0
    elif problem=='bad_source':log['_source_order']=-1
    else:log[C.case]=1
    with pytest.raises(ValueError):build_dataset(log)


def test_missing_optional_fields_no_predictor_change(log):
    before=prefix_features(log)
    pd.testing.assert_frame_equal(before,prefix_features(log.drop(columns=[C.resource,'org:role','id','case:Amount'])))
    _,audit,_=build_dataset(log.drop(columns=[C.resource,'org:role']))
    assert audit['event2_org:role'].isna().all()


def test_target_boundary_and_known_positive_priority():
    assert construct_target(pd.Series([0.,1.,1.0001]),1).tolist()==[0,0,1]
    audit=pd.DataFrame({'prefix_elapsed_hours':[24,24.0001,48,0], 'event_count':[2,2,2,1],
                        'split':['train','train','purged_overlap',None]})
    result=assess_eligibility(audit,1)
    assert result.eligibility.tolist()==['unresolved_eligible','already_over_threshold','already_over_threshold','fewer_than_two_events']
    for values,threshold in [([-1],1),([float('nan')],1),([1],-1),([1],float('inf'))]:
        with pytest.raises(ValueError):construct_target(pd.Series(values),threshold)


def test_future_mutation_cannot_change_predictors(log):
    original=prefix_features(log)
    future=log[C.activity].eq('End')
    log.loc[future,C.activity]='SECRET FUTURE'
    log.loc[future,C.resource]='SECRET RESOURCE'
    log.loc[future,C.timestamp]+=pd.Timedelta(days=1000)
    log['case:Amount']=999999
    pd.testing.assert_frame_equal(original,prefix_features(log))
    assert set(original).isdisjoint({'end_timestamp','elapsed_days','case:Amount',C.resource,'org:role'})


def test_chronology_no_overlap_train_threshold_and_reproducibility(log):
    rows,audit,design=build_dataset(log)
    assert rows.groupby('split').size().to_dict()=={'train':12,'validation':4,'test':4}
    assert design['threshold_days']==pytest.approx(9.25)
    assert rows[C.case].is_unique
    assert rows.loc[rows.split.eq('train'),'prediction_timestamp'].max()<rows.loc[rows.split.eq('validation'),'prediction_timestamp'].min()
    repeat=build_dataset(log.sample(frac=1,random_state=7))
    pd.testing.assert_frame_equal(rows,repeat[0]);pd.testing.assert_frame_equal(audit,repeat[1])
    assert design==repeat[2]
    holdout=log[C.case].isin([f'case-{i:02}' for i in range(12,20)]) & log[C.activity].eq('End')
    log.loc[holdout,C.timestamp]+=pd.Timedelta(days=90)
    assert build_dataset(log)[2]['threshold_days']==design['threshold_days']


def test_endpoint_purge_including_equality(log):
    rows,audit,design=build_dataset(log)
    log.loc[log[C.case].eq('case-00') & log[C.activity].eq('End'),C.timestamp]=pd.Timestamp(design['validation_start'])
    changed,history,new=build_dataset(log)
    assert history.set_index(C.case).loc['case-00','eligibility']=='purged_overlap'
    assert 'case-00' not in set(changed[C.case])
    assert new['threshold_days']==pytest.approx(9.5)


def test_fit_train_only_unknown_categories_and_imputation(log):
    rows,_,_=build_dataset(log)
    train=rows.split.eq('train')
    rows.loc[train,'prefix_elapsed_hours']=2.
    rows.loc[train,'utc_hour']=1
    rows.loc[train,'prefix_elapsed_hours']=rows.loc[train,'prefix_elapsed_hours'].mask(rows.loc[train].index==0)
    spec=fit_preprocessor(rows)
    assert spec['numeric']['prefix_elapsed_hours']['median']==2
    assert spec['fit_cases']==rows.loc[train,C.case].tolist()
    mutated=rows.copy()
    mutated.loc[~train,'prefix_elapsed_hours']=999999.
    mutated.loc[~train,'second_activity']='Unseen'
    assert fit_preprocessor(mutated)==spec
    x=transform_features(mutated,spec)
    assert x.loc[~train,'["second_activity", "Review"]'].eq(0).all()
    assert not x.isna().any().any()
    assert x.loc[train,'prefix_elapsed_hours'].eq(0).all()
    with pytest.raises(ValueError):fit_preprocessor(rows.loc[~train])
    assert list(feature_matrix(rows))==FEATURES


@pytest.mark.parametrize('problem',['future_column','duplicate_case','wrong_elapsed','wrong_calendar','wrong_target','overlapping_partition'])
def test_schema_and_leakage_reject_corruption(log,problem):
    rows,audit,design=build_dataset(log)
    if problem=='future_column':rows['elapsed_days']=1.
    elif problem=='duplicate_case':rows.loc[1,C.case]=rows.loc[0,C.case]
    elif problem=='wrong_elapsed':rows.loc[0,'prefix_elapsed_hours']=99.
    elif problem=='wrong_calendar':rows.loc[0,'utc_hour']=23
    elif problem=='wrong_target':rows.loc[0,'target_long_observed']=1
    else:rows.loc[0,'split']='test'
    with pytest.raises(ValueError):audit_leakage(rows,audit,design)


@pytest.mark.integration
def test_actual_dataset_and_exports():
    source=ROOT/'data/processed/domestic_declarations_cleaned.parquet'
    events=pd.read_parquet(source)
    rows,audit,design=build_dataset(events)
    assert len(audit)==10500
    assert audit.eligibility.value_counts().to_dict()=={'unresolved_eligible':9536,'purged_overlap':497,'already_over_threshold':333,'fewer_than_two_events':134}
    assert design['threshold_days']==pytest.approx(11.105428240740741)
    assert audit.split.eq('purged_overlap').sum()==520
    assert (audit.split.eq('purged_overlap')&audit.already_above_threshold).sum()==23
    assert rows.groupby('split').target_long_observed.agg(['size','sum']).to_dict()=={'size':{'test':2001,'train':5783,'validation':1752},'sum':{'test':668,'train':1320,'validation':496}}
    exported=pd.read_parquet(ROOT/'data/processed/domestic_declarations_ml_ready.parquet')
    pd.testing.assert_frame_equal(rows,exported)
    assert set(rows)==set(FEATURES+METADATA)
    for name in ['eligibility_audit','split_summary','threshold_derivation','leakage_audit','preprocessing_spec','runtime']:
        json.loads((ROOT/f'outputs/reports/day7_8_{name}.json').read_text(encoding='utf-8'))
    assert audit_leakage(rows,audit,design)['checks_passed']
