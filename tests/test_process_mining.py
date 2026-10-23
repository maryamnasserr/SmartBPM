"""Known-answer process discovery, performance, export and UI regressions."""
from datetime import date
import io
import json
from pathlib import Path
import pandas as pd
import pytest
from smartbpm.dashboard import C, prepare_dashboard, filter_cases, csv_bytes, load_dashboard_events
from smartbpm.dashboard_charts import dashboard_charts
from smartbpm.process_mining import discover_transitions, ordered_events, select_transitions, variant_performance, repetition_performance
from smartbpm.process_mining_charts import process_map

ROOT = Path(__file__).resolve().parents[1]

@pytest.fixture
def log():
    return pd.DataFrame({C.case: ['a']*4+['b']*2+['c'], C.activity: ['A','B','A','B','A','B','C'],
                         C.resource: ['R']*7,
                         C.timestamp: pd.to_datetime(['2020-01-01','2020-01-02','2020-01-03','2020-01-04','2020-01-01','2020-01-01','2020-01-05'],utc=True),
                         '_source_order': range(7)})


def test_known_dfg_and_elapsed_gaps(log):
    edges, stats = discover_transitions(log)
    indexed = edges.set_index(['source','target'])
    assert indexed.frequency.to_dict() == {('A','B'):3, ('B','A'):1}
    assert indexed.loc[('A','B'),'case_count'] == 2
    assert indexed.loc[('A','B'),'median_hours'] == 24
    assert indexed.loc[('A','B'),'mean_hours'] == 16
    assert indexed.loc[('A','B'),'p95_hours'] == 24
    assert indexed.loc[('A','B'),'zero_gap_occurrences'] == 1
    assert stats['starts'] == {'A':2,'C':1}
    assert stats['ends'] == {'B':2,'C':1}
    assert stats['transition_occurrences'] == 7-3


def test_order_ties_input_preservation(log):
    shuffled = log.sample(frac=1, random_state=42)
    before = shuffled.copy(deep=True)
    pd.testing.assert_frame_equal(ordered_events(shuffled),log)
    pd.testing.assert_frame_equal(discover_transitions(shuffled)[0],discover_transitions(log)[0])
    pd.testing.assert_frame_equal(shuffled,before)


def test_no_bridge_or_cross_case_edges(log):
    edges,_=discover_transitions(log)
    assert not ((edges.source=='B') & (edges.target=='C')).any()
    displayed=select_transitions(edges,minimum=2,maximum=1,focus=['B'])
    assert list(zip(displayed.source,displayed.target))==[('A','B')]
    assert set(zip(displayed.source,displayed.target)) <= set(zip(edges.source,edges.target))
    filtered=filter_cases(log,prepare_dashboard(log)[1]['case_summary'],activities=['B'])
    assert len(filtered)==6
    assert discover_transitions(filtered)[1]['transition_occurrences']==4


def test_hidden_intermediate_node_never_creates_edge(log):
    chain=log.iloc[:3].copy()
    chain[C.activity]=['A','B','C']
    edges,_=discover_transitions(chain)
    assert set(zip(select_transitions(edges,focus=['A']).source,select_transitions(edges,focus=['A']).target))=={('A','B')}
    assert ('A','C') not in set(zip(edges.source,edges.target))


def test_singletons_empty_and_self_loops(log):
    singleton=log.iloc[[-1]]
    assert discover_transitions(singleton)[0].empty
    empty=log.iloc[:0]
    assert discover_transitions(empty)[1]['transition_occurrences']==0
    repeated=log.iloc[:2].copy();repeated[C.activity]='A'
    edges,_=discover_transitions(repeated)
    assert edges.iloc[0].source==edges.iloc[0].target=='A'
    figure,legend=process_map(edges,edges,{'A':2})
    assert figure["series"][0]["links"][0]["source"]==figure["series"][0]["links"][0]["target"] and legend[0]['event_count']==2


@pytest.mark.parametrize('problem',['missing','naive','null_time','duplicate_source','nonstring','blank','negative_source'])
def test_invalid_inputs(log,problem):
    if problem=='missing':
        log=log.drop(columns=C.case)
    elif problem=='naive':
        log[C.timestamp]=log[C.timestamp].dt.tz_localize(None)
    elif problem=='null_time':
        log.loc[0,C.timestamp]=pd.NaT
    elif problem=='duplicate_source':
        log.loc[1,'_source_order']=0
    elif problem=='nonstring':
        log[C.activity]=log[C.activity].astype(object);log.loc[0,C.activity]=123
    elif problem=='blank':
        log.loc[0,C.activity]=' '
    else:
        log.loc[0,'_source_order']=-1
    with pytest.raises(ValueError):
        discover_transitions(log)


def test_variant_duration_and_sequence_oracle(log):
    summary,tables=prepare_dashboard(log)
    variants=variant_performance(tables['case_summary'],tables['process_variants'])
    assert summary['variant_count']==3
    bysequence={tuple(json.loads(r.sequence)):r for r in variants.itertuples()}
    assert bysequence[('A','B','A','B')].median_days==3
    assert bysequence[('A','B')].p95_days==0
    assert variants.case_count.sum()==3
    assert variants.case_share.sum()==pytest.approx(1)
    # Includes ties and noncontiguous source rows; compare with Pandas grouping oracle.
    expected=log.groupby(C.case)[C.activity].agg(tuple).value_counts().to_dict()
    assert {key:int(row.case_count) for key,row in bysequence.items()}==expected


def test_repetition_and_overlapping_label_groups(log):
    log[C.activity]=['X APPROVED by ROLE','X REJECTED by ROLE']*2+['Submit','End','Save']
    _,tables=prepare_dashboard(log)
    flags,groups=repetition_performance(tables['case_summary'],tables['repeated_activities_by_case'])
    a=flags.set_index(C.case).loc['a']
    assert a.repeated_approval and a.repeated_rejection
    assert a.repetition_group=='Repeated activity'
    assert groups.cases.tolist()==[2,1,1,1]
    assert groups.iloc[1].median_days==3
    assert groups.iloc[0].median_days==0


def test_lazy_charts_and_exact_display_export(log):
    _,tables=prepare_dashboard(log)
    assert set(dashboard_charts(tables,keys=('duration','trace_length')))=={'duration','trace_length'}
    assert dashboard_charts(tables,keys=())=={}
    edges,_=discover_transitions(log)
    displayed=select_transitions(edges,minimum=2)
    restored=pd.read_csv(io.BytesIO(csv_bytes(displayed)))
    pd.testing.assert_frame_equal(restored,displayed.reset_index(drop=True))
    cases=pd.read_csv(io.BytesIO(csv_bytes(tables['case_summary'])))
    assert len(cases)==3 and cases.event_count.sum()==7


@pytest.mark.parametrize('bounds',[(float('nan'),2),(0,float('inf'))])
def test_nonfinite_duration_is_rejected(log,bounds):
    with pytest.raises(ValueError):
        filter_cases(log,prepare_dashboard(log)[1]['case_summary'],duration_range=bounds)


@pytest.mark.integration
def test_real_mining_and_historical_equivalence():
    path=ROOT/'data/processed/domestic_declarations_cleaned.parquet'
    if not path.exists():
        pytest.skip('Local dataset unavailable')
    events=load_dashboard_events(path)
    summary,tables=prepare_dashboard(events)
    edges,stats=discover_transitions(events)
    assert stats['transition_occurrences']==56437-10500
    assert stats['starts']==summary['common_starts']
    assert stats['ends']==summary['common_ends']
    historical=json.loads((ROOT/'outputs/reports/initial_eda_summary.json').read_text())
    for key in ('total_cases','total_events','total_activities','variant_count','duration_days','top_variants','cases_with_repeated_activities'):
        assert summary[key]==historical[key]
    performance=variant_performance(tables['case_summary'],tables['process_variants'])
    assert performance.case_count.sum()==10500
    assert performance.median_days.ge(0).all()
    assert edges.frequency.sum()==45937


@pytest.mark.integration
def test_process_mining_ui_controls_and_filtered_cohorts():
    from streamlit.testing.v1 import AppTest
    if not (ROOT/'data/processed/domestic_declarations_cleaned.parquet').exists():
        pytest.skip('Local dataset unavailable')
    app=AppTest.from_file(str(ROOT/'app.py'),default_timeout=90).run()
    app.sidebar.radio[0].set_value('Process Mining').run()
    assert not app.exception
    assert len(app.get('plotly_chart'))==2
    assert len(app.get('echarts_chart'))==1
    assert app.metric[4].value=='45,937'
    app.number_input(key='map_minimum').set_value(100000).run()
    assert not app.exception
    assert any('No edges meet' in x.value for x in app.info)
    assert app.metric[0].value=='10,500'
    app.number_input(key='map_minimum').set_value(1).run()
    app.multiselect(key='compare_variants').set_value([]).run()
    assert not app.exception
    app.selectbox(key="inspect_variant").set_value("V0002").run()
    app.multiselect(key="compare_variants").set_value(["V0002", "V0003"]).run()
    app.sidebar.multiselect[0].set_value(['Declaration FOR_APPROVAL by ADMINISTRATION']).run()
    assert not app.exception
    assert app.metric[0].value=='1'
    app.sidebar.multiselect[0].set_value([]).run()
    assert not app.exception
    assert not app.get('plotly_chart')
    app.sidebar.button[0].click().run()
    assert not app.exception
    assert app.metric[0].value=='10,500'


