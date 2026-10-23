"""Known-answer prediction point, target, temporal maturity and UI regressions."""
from pathlib import Path
import io
import pandas as pd
import pytest
from smartbpm.dashboard import C,prepare_dashboard,csv_bytes,filter_cases,load_dashboard_events
from smartbpm.performance import duration_labels,prediction_prefix,temporal_design,investigate,target_definition
ROOT=Path(__file__).resolve().parents[1]

@pytest.fixture
def history():
    records=[]
    for i in range(20):
        start=pd.Timestamp('2020-01-01',tz='UTC')+pd.Timedelta(days=i*30)
        for j,(name,offset) in enumerate([('Submit',0),('End',i+1)]):
            records.append({C.case:f'C{i:02}',C.activity:name,C.timestamp:start+pd.Timedelta(days=offset),C.resource:'Staff', 'org:role':'Role','case:Amount':i*100,'_source_order':len(records)})
    return pd.DataFrame(records)


def test_target_boundaries_and_invalid():
    assert duration_labels(pd.Series([0.,1.,1.00001,2]),1).tolist()==[0,0,1,1]
    for values,threshold in [([None],1),([-1],1),([float('inf')],1),([1],float('nan')),([1],-1)]:
        with pytest.raises((ValueError,TypeError)):
            duration_labels(pd.Series(values),threshold)


def test_prediction_prefix_no_future_leakage_and_order(history):
    original=prediction_prefix(history)
    changed=history.copy();changed.loc[changed[C.activity].eq('End'),C.activity]='Secret outcome'
    changed.loc[changed[C.activity].eq('Secret outcome'),C.resource]='Future only'
    changed['case:Amount']=999999
    pd.testing.assert_frame_equal(original,prediction_prefix(changed.sample(frac=1,random_state=2)))
    assert original.activity_prefix.tolist()==[('Submit',)]*20
    assert 'case:Amount' not in original and 'elapsed_days' not in original
    assert original.prefix_elapsed_hours.eq(0).all()
    assert prediction_prefix(history,2).prefix_position.eq(2).all()
    assert prediction_prefix(history,activity='End').prefix_position.eq(2).all()
    with pytest.raises(ValueError):prediction_prefix(history,0)
    tied=history.iloc[:2].copy();tied[C.timestamp]=tied.iloc[0][C.timestamp]
    assert prediction_prefix(tied.iloc[::-1]).current_activity.tolist()==['Submit']
    assert prediction_prefix(tied,2).current_activity.tolist()==['End']


def test_missing_event_attributes_and_invalid_provenance(history):
    missing=prediction_prefix(history.drop(columns=[C.resource,'org:role']))
    assert missing[C.resource].eq('Unknown').all()
    broken=history.copy();broken.loc[0,C.timestamp]=pd.NaT
    with pytest.raises(ValueError):prediction_prefix(broken)
    broken=history.copy();broken['_source_order']=0
    with pytest.raises(ValueError):prediction_prefix(broken)


def test_temporal_training_threshold_and_holdout_invariance(history):
    _,tables=prepare_dashboard(history)
    prefix=prediction_prefix(history)
    rows,design=temporal_design(tables['case_summary'],prefix)
    assert design['threshold_days']==pytest.approx(9.25)
    assert design['split_counts']=={'train':12,'validation':4,'test':4}
    assert int(rows.loc[rows.split.eq('train'),'target_long_observed'].sum())==3
    altered=tables['case_summary'].copy();altered.loc[altered[C.case].isin(['C16','C17','C18','C19']),'elapsed_days']=10000
    _,after=temporal_design(altered,prefix)
    assert after['threshold_days']==design['threshold_days']
    # A training case whose label reaches validation is purged, including equality.
    altered.loc[altered[C.case].eq('C00'),'end_timestamp']=pd.Timestamp(design['validation_start'])
    purged,after=temporal_design(altered,prefix)
    assert purged.set_index(C.case).loc['C00','split']=='purged_overlap'
    assert after['split_counts']['train']==11


def test_eligibility_singletons_and_known_durations(history):
    singleton=history.loc[~((history[C.case]=='C00')&(history[C.activity]=='End'))]
    assert len(prediction_prefix(singleton))==20
    assert len(prediction_prefix(singleton,2))==19
    assert len(prediction_prefix(singleton,activity='End'))==19
    stats,views=investigate(singleton)
    assert stats['single_event_cases']==1
    assert stats['mean_days']==pytest.approx(sum(range(2,21))/20)
    definition,labels=target_definition(singleton)
    assert definition['eligible_cases']==19
    assert labels.target_long_observed.sum()==sum(labels.elapsed_days>definition['threshold_days'])
    exported=pd.read_csv(io.BytesIO(csv_bytes(views['prediction_points'])))
    pd.testing.assert_frame_equal(exported,views['prediction_points'])


@pytest.mark.integration
def test_real_day6_counts_and_labels():
    events=load_dashboard_events(ROOT/'data/processed/domestic_declarations_cleaned.parquet')
    definition,labels=target_definition(events)
    stats,views=investigate(events)
    assert len(labels)==definition['eligible_cases']==10366
    assert stats['repeated_cases']==1019 and stats['variants']==99
    assert stats['mean_days']==pytest.approx(11.525722,abs=1e-6)
    assert stats['single_event_cases']==134
    assert views['prediction_points'].eligible_cases.tolist()==[10500,10366,10365]
    assert sum(x['positive']+x['negative'] for x in definition['class_balance'][1:])==10366
    frozen=__import__('json').loads((ROOT/'outputs/reports/day6_target_definition.json').read_text(encoding='utf-8'))
    assert frozen['threshold_days']==definition['threshold_days']
    assert frozen['class_balance']==definition['class_balance']


@pytest.mark.integration
def test_performance_page_filter_and_reset():
    from streamlit.testing.v1 import AppTest
    app=AppTest.from_file(str(ROOT/'app.py'),default_timeout=90).run()
    app.sidebar.radio[0].set_value('Performance Investigation').run()
    assert not app.exception and len(app.get('plotly_chart'))==3
    assert any('Event-2 snapshots: 10,366' in m.value for m in app.markdown)
    app.sidebar.multiselect[0].set_value(['Declaration FOR_APPROVAL by ADMINISTRATION']).run()
    assert not app.exception and app.metric[0].value=='1'
    assert any('Event-2 snapshots: 10,366' in m.value for m in app.markdown)
    app.sidebar.multiselect[0].set_value([]).run()
    assert not app.exception and not app.get('plotly_chart')
    app.sidebar.button[0].click().run()
    assert not app.exception and app.metric[0].value=='10,500'


def test_second_prefix_is_invariant_to_third_future_event(history):
    prefixes=prediction_prefix(history,2)
    later=history.groupby(C.case).tail(1).copy()
    later[C.timestamp]=later[C.timestamp]+pd.Timedelta(days=100)
    later[C.activity]='Future outcome'
    later['_source_order']=range(len(history),len(history)+len(later))
    combined=pd.concat([history,later],ignore_index=True)
    pd.testing.assert_frame_equal(prefixes,prediction_prefix(combined.sample(frac=1,random_state=7),2))
    definition,labels=target_definition(combined)
    assert labels.loc[labels.already_above_threshold_at_prediction,'target_long_observed'].eq(1).all()
    assert sum(r['cases'] for r in definition['unknown_label_class_balance'])==definition['unknown_at_prediction_cases']


def test_temporal_ties_share_partition(history):
    _,tables=prepare_dashboard(history)
    prefix=prediction_prefix(history)
    prefix.loc[prefix[C.case].isin(['C11','C12']),'prediction_timestamp']=prefix.loc[prefix[C.case].eq('C12'),'prediction_timestamp'].iloc[0]
    rows,_=temporal_design(tables['case_summary'],prefix)
    assert rows.set_index(C.case).loc['C11','split']==rows.set_index(C.case).loc['C12','split']
