"""Record representative local compute and actual Streamlit rerun timings.
Run with the project interpreter; measurements are workstation-dependent.
"""
import json
from pathlib import Path
import statistics
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from smartbpm.dashboard import load_dashboard_events,prepare_dashboard
from smartbpm.process_mining import discover_transitions,select_transitions
from smartbpm.process_mining_charts import process_map
from streamlit.testing.v1 import AppTest


def main():
    report={}
    def measure(name,function,n=3):
        timings=[]
        for _ in range(n):
            start=time.perf_counter();value=function();timings.append(time.perf_counter()-start)
        report[name]={'seconds':timings,'median_seconds':statistics.median(timings)}
        return value
    events=load_dashboard_events(ROOT/'data/processed/domestic_declarations_cleaned.parquet')
    summary,tables=prepare_dashboard(events)
    transitions,discovery=measure('dfg_and_transition_performance',lambda:discover_transitions(events))
    shown=select_transitions(transitions)
    measure('interactive_process_map_20_edges',lambda:process_map(transitions,shown,summary['activity_frequency']))
    app=AppTest.from_file(str(ROOT/'app.py'),default_timeout=90)
    measure('initial_apptest_run',lambda:app.run(),n=1)
    if app.exception:
        raise AssertionError(app.exception)
    measure('unchanged_cached_apptest_rerun',lambda:app.run())
    timings=[]
    maximum=app.sidebar.slider[0].max
    for bounds in ((1.,20.),(0.,float(maximum)),(1.,20.)):
        start=time.perf_counter();app.sidebar.slider[0].set_value(bounds).run();timings.append(time.perf_counter()-start)
        if app.exception:
            raise AssertionError(app.exception)
    report['filter_interactions']={'sequence':['first 1–20 day selection','return to all','repeat 1–20 day selection'],'seconds':timings}
    report['real_dataset']={name:discovery[name] for name in ('events','cases','activities','distinct_transitions','transition_occurrences')}
    report['note']='Three perf_counter samples except initial app run. Compute measurements exclude Python startup/imports. AppTest reruns include Streamlit execution but exclude browser/network rendering. Timings are local observations, not production guarantees; concurrent verification can affect them.'
    (ROOT/'outputs/reports/day4_5_runtime_benchmark.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2))


if __name__=='__main__':
    main()
