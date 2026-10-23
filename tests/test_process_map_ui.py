"""Regression checks for map labels, hidden edges, isolation and activity inspection."""
import json
from pathlib import Path
import pandas as pd
import pytest
from smartbpm.dashboard import C,prepare_dashboard,load_dashboard_events
from smartbpm.process_mining import discover_transitions,select_transitions
from smartbpm.process_map_data import readable_activity,activity_map_rows,selected_activity_statistics
from smartbpm.process_mining_charts import process_map

ROOT=Path(__file__).resolve().parents[1]

@pytest.fixture
def events():
    return pd.DataFrame({C.case:['a','a','a','b','b','c'],
                         C.activity:['Declaration SUBMITTED by EMPLOYEE','Declaration APPROVED by ADMINISTRATION','Payment Handled',
                                     'Declaration SUBMITTED by EMPLOYEE','Declaration SUBMITTED by EMPLOYEE','Declaration SAVED by EMPLOYEE'],
                         C.timestamp:pd.to_datetime(['2020-01-01','2020-01-02','2020-01-03','2020-01-01','2020-01-02','2020-01-05'],utc=True),
                         C.resource:['R']*6,'_source_order':range(6)})


def test_human_labels_preserve_original_identifiers(events):
    assert readable_activity('Declaration FINAL_APPROVED by SUPERVISOR')=='Final approval\nSupervisor'
    assert readable_activity('Declaration FOR_APPROVAL by PRE_APPROVER')=='For approval\nPre Approver'
    assert readable_activity('Declaration REJECTED by MISSING')=='Rejection\nMissing (recorded role)'
    assert readable_activity('Unknown step')=='Unknown step'
    before=events.copy(deep=True)
    edges,_=discover_transitions(events)
    graph,rows=process_map(edges,edges,events[C.activity].value_counts().to_dict())
    assert len({row['node'] for row in rows})==events[C.activity].nunique()
    assert {row['activity'] for row in rows}==set(events[C.activity])
    assert any('Submit declaration' in n['name'] for n in graph['series'][0]['data'])
    assert any(n['raw_activity']=='Declaration SUBMITTED by EMPLOYEE' for n in graph['series'][0]['data'])
    pd.testing.assert_frame_equal(events,before)


def test_display_isolation_is_not_underlying_isolation(events):
    edges,_=discover_transitions(events)
    # Only the submission self-loop is visible; administration has hidden real edges.
    shown=edges.loc[edges.source.eq(edges.target)]
    rows=activity_map_rows(events[C.activity].value_counts().to_dict(),edges,shown)
    admin=next(row for row in rows if 'ADMINISTRATION' in row['activity'])
    assert admin['isolated_in_display'] and admin['full_relationships']==2
    assert admin['hidden_relationships']==2
    assert 'hidden' in admin['isolation_reason']
    saved=next(row for row in rows if 'SAVED' in row['activity'])
    assert saved['isolated_in_display'] and saved['full_relationships']==0
    assert 'No consecutive event pairs' in saved['isolation_reason']
    assert len(rows)==4  # No silent deletion of the complete activity inventory.


def test_selected_activity_counts_and_singleton_explanation(events):
    _,tables=prepare_dashboard(events)
    edges,_=discover_transitions(events)
    empty=select_transitions(edges,minimum=100)
    stats=selected_activity_statistics(events,tables['case_summary'],edges,empty,'Declaration SUBMITTED by EMPLOYEE')
    assert stats['event_count']==3 and stats['cases']==2 and stats['repeating_cases']==1
    assert stats['starting_cases']==2 and stats['ending_cases']==1
    assert stats['incoming_occurrences']==1 and stats['outgoing_occurrences']==2
    saved=selected_activity_statistics(events,tables['case_summary'],edges,empty,'Declaration SAVED by EMPLOYEE')
    assert saved['single_event_cases']==saved['event_count']==1
    assert 'Only observed in single-event cases' in saved['isolation_reason']
    with pytest.raises(ValueError):
        selected_activity_statistics(events,tables['case_summary'],edges,empty,'Absent')


def test_counts_cannot_change_or_create_bridged_edges(events):
    edges,summary=discover_transitions(events)
    shown=select_transitions(edges,maximum=1)
    original=edges.copy(deep=True)
    graph,rows=process_map(edges,shown,events[C.activity].value_counts().to_dict())
    assert int(edges.frequency.sum())==summary['events']-summary['cases']==3
    assert len(rows)==4
    pd.testing.assert_frame_equal(edges,original)
    changed=shown.copy();changed.loc[changed.index[0],'frequency']=100
    with pytest.raises(ValueError,match='change counts'):
        process_map(edges,changed,events[C.activity].value_counts().to_dict())
    bridged=shown.copy();bridged['source']='Declaration SUBMITTED by EMPLOYEE';bridged['target']='Payment Handled'
    with pytest.raises(ValueError,match='invent relationships'):
        process_map(edges,bridged,events[C.activity].value_counts().to_dict())


def test_inspected_isolate_and_direction(events):
    edges,_=discover_transitions(events)
    shown=select_transitions(edges,minimum=100)
    graph,rows=process_map(edges,shown,events[C.activity].value_counts().to_dict(),selected_activity='Declaration SAVED by EMPLOYEE',direction='LR')
    assert graph['series'][0]['data'][0]['itemStyle']['borderType']=='dashed'
    assert 'Save declaration' in graph['series'][0]['data'][0]['name']
    assert graph['series'][0]['data'][0]['x']>=0
    assert graph['series'][0]['links']==[]
    assert all(row['isolated_in_display'] for row in rows)


def test_quoted_labels_remain_plain_json_text():
    # No HTML node interpretation or injected DOT edges through labels.
    from smartbpm.process_mining import TRANSITION_COLUMNS
    edges=pd.DataFrame(columns=TRANSITION_COLUMNS)
    label='A "quoted" <activity>'
    graph,rows=process_map(edges,edges,{label:1},selected_activity=label)
    assert rows[0]['activity']==label
    assert json.loads(json.dumps(graph))['series'][0]['data'][0]['raw_activity']==label
    assert graph['series'][0]['links']==[]


@pytest.mark.integration
def test_real_labels_counts_and_old_isolated_nodes():
    path=ROOT/'data/processed/domestic_declarations_cleaned.parquet'
    if not path.exists():
        pytest.skip('Local dataset unavailable')
    events=load_dashboard_events(path)
    _,tables=prepare_dashboard(events)
    edges,summary=discover_transitions(events)
    frequencies=events[C.activity].value_counts().to_dict()
    original=edges.copy(deep=True)
    old_rows=activity_map_rows(frequencies,edges,select_transitions(edges,maximum=20))
    isolated=[row for row in old_rows if row['isolated_in_display']]
    assert len(isolated)==4 and all(row['full_relationships']>0 for row in isolated)
    all_rows=activity_map_rows(frequencies,edges,edges)
    assert len(all_rows)==17 and not any(row['isolated_in_display'] for row in all_rows)
    stats=selected_activity_statistics(events,tables['case_summary'],edges,select_transitions(edges,maximum=8),'Declaration SAVED by EMPLOYEE')
    assert (stats['event_count'],stats['cases'],stats['single_event_cases'])==(135,135,134)
    assert stats['full_relationships']==1
    assert summary['transition_occurrences']==45937 and len(edges)==39
    graph,_=process_map(edges,edges,frequencies,True)
    assert len(graph['series'][0]['links'])==39
    pd.testing.assert_frame_equal(edges,original)


@pytest.mark.integration
def test_ui_all_edges_activity_inspection_and_empty_display():
    from streamlit.testing.v1 import AppTest
    if not (ROOT/'data/processed/domestic_declarations_cleaned.parquet').exists():
        pytest.skip('Local dataset unavailable')
    app=AppTest.from_file(str(ROOT/'app.py'),default_timeout=90).run()
    app.sidebar.radio[0].set_value('Process Mining').run()
    assert not app.exception
    assert len(app.get('echarts_chart'))==1
    assert app.number_input(key='map_limit').value==7
    app.radio(key='map_detail').set_value('Detailed Process').run()
    assert not app.exception
    assert len(json.loads(app.get('echarts_chart')[0].proto.spec)['series'][0]['links'])==39
    assert len(json.loads(app.get('echarts_chart')[0].proto.spec)['series'][0]['data'])==17
    app.selectbox(key='map_activity').set_value('Declaration SAVED by EMPLOYEE').run()
    assert not app.exception
    assert next(m.value for m in app.metric if m.label=='Activity occurrences')=='135'
    app.radio(key='map_detail').set_value('Main Process').run()
    app.number_input(key='map_minimum').set_value(100000).run()
    assert not app.exception
    assert app.metric[0].value=='10,500'
    assert any(n['itemStyle']['borderType']=='dashed' for n in json.loads(app.get('echarts_chart')[0].proto.spec)['series'][0]['data'])



def test_layout_preserves_aspect_and_uses_distinct_lanes(events):
    from smartbpm.process_mining_charts import directed_positions
    edges,stats=discover_transitions(events)
    activity_counts=events[C.activity].value_counts().to_dict()
    option,_=process_map(edges,edges,activity_counts,starts=stats['starts'])
    assert option['series'][0]['preserveAspect'] is True
    assert option['series'][0]['roam'] is True
    positions=directed_positions(edges,set(edges.source)|set(edges.target),stats['starts'])
    assert len(set(positions.values()))==len(positions)
