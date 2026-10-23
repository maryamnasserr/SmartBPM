"""Auditable display labels, isolation explanations and selected-activity statistics."""
import pandas as pd
from smartbpm.preprocessing import Columns
C=Columns()


def readable_activity(name):
    """Presentation only; original labels remain identifiers and tooltip text."""
    prefix='Declaration '
    if name.startswith(prefix) and ' by ' in name:
        status,role=name[len(prefix):].split(' by ',1)
        descriptions={'SUBMITTED':'Submit declaration','SAVED':'Save declaration',
                      'APPROVED':'Approval','FINAL_APPROVED':'Final approval',
                      'REJECTED':'Rejection','FOR_APPROVAL':'For approval'}
        role_text=role.replace('_',' ').title()
        if role=='MISSING':
            role_text='Missing (recorded role)'
        return descriptions.get(status,status.replace('_',' ').title())+'\n'+role_text
    return name.replace('_',' ')


def validate_display_graph(transitions,shown,activities):
    """A visual edge must be an unmodified relationship from the complete DFG."""
    for frame in (transitions,shown):
        if frame.duplicated(['source','target']).any():
            raise ValueError('Duplicate graph relationships')
        for row in frame.itertuples():
            if row.source not in activities or row.target not in activities:
                raise ValueError('Unknown activity in graph relationship')
            if not isinstance(row.frequency,(int,float)) or row.frequency<1 or int(row.frequency)!=row.frequency:
                raise ValueError('Transition frequencies must be positive integers')
    lookup={(row.source,row.target):row.frequency for row in transitions.itertuples()}
    for row in shown.itertuples():
        if lookup.get((row.source,row.target))!=row.frequency:
            raise ValueError('Display controls cannot invent relationships or change counts')


def activity_map_rows(activities,transitions,shown):
    validate_display_graph(transitions,shown,activities)
    rows=[]
    for i,name in enumerate(sorted(activities)):
        full=transitions.source.eq(name)|transitions.target.eq(name)
        visible=shown.source.eq(name)|shown.target.eq(name)
        full_count,visible_count=int(full.sum()),int(visible.sum())
        reason=('All observed relationships are hidden by the current map controls.' if full_count else
                'No consecutive event pairs involving this activity occur in the selected cases.') if not visible_count else 'Connected in the displayed map.'
        rows.append({'node':f'A{i+1:02}','activity':name,'label':readable_activity(name),
                     'event_count':int(activities[name]),'full_relationships':full_count,
                     'visible_relationships':visible_count,'hidden_relationships':full_count-visible_count,
                     'isolated_in_display':visible_count==0,'isolation_reason':reason})
    return rows


def selected_activity_statistics(events,cases,transitions,shown,activity):
    if activity not in set(events[C.activity]):
        raise ValueError('Select an activity present in the case cohort')
    frequencies=events[C.activity].value_counts().to_dict()
    row=next(row for row in activity_map_rows(frequencies,transitions,shown) if row['activity']==activity)
    occurrences=events.loc[events[C.activity].eq(activity)]
    counts=occurrences.groupby(C.case).size()
    singleton=cases.event_count.eq(1)&cases.start_activity.eq(activity)
    row.update({'cases':int(occurrences[C.case].nunique()),'repeating_cases':int(counts.gt(1).sum()),
                'starting_cases':int(cases.start_activity.eq(activity).sum()),
                'ending_cases':int(cases.end_activity.eq(activity).sum()),
                'single_event_cases':int(singleton.sum()),
                'incoming_occurrences':int(transitions.loc[transitions.target.eq(activity),'frequency'].sum()),
                'outgoing_occurrences':int(transitions.loc[transitions.source.eq(activity),'frequency'].sum())})
    if row['full_relationships']==0 and row['single_event_cases']==row['event_count']:
        row['isolation_reason']='Only observed in single-event cases in this cohort; there is no previous or next recorded event.'
    return row
