"""Reproduce Day 6 small research artifacts without training or duplicate data."""
import json,sys,time,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from smartbpm.dashboard import load_dashboard_events,prepare_dashboard
from smartbpm.performance import investigate,target_definition,candidate_comparison

def main():
    out=ROOT/'outputs/reports';out.mkdir(exist_ok=True,parents=True)
    times={"free_bytes_before":shutil.disk_usage(ROOT).free}
    tick=time.perf_counter();events=load_dashboard_events(ROOT/'data/processed/domestic_declarations_cleaned.parquet');times['load_seconds']=time.perf_counter()-tick
    tick=time.perf_counter();summary,tables=prepare_dashboard(events);times['analysis_seconds']=time.perf_counter()-tick
    tick=time.perf_counter();stats,views=investigate(events,tables);times['investigation_seconds']=time.perf_counter()-tick
    tick=time.perf_counter();definition,labels=target_definition(events,tables);times['target_design_seconds']=time.perf_counter()-tick
    candidate_comparison(stats).to_csv(out/'day6_candidate_targets.csv',index=False)
    (out/'day6_target_definition.json').write_text(json.dumps(definition,indent=2,allow_nan=False),encoding='utf-8')
    report={'duration_and_candidates':stats,'timing':times,**{k:v.to_dict(orient='records') for k,v in views.items() if k!='variants'}}
    report['variant_repetition_association']=tables['case_summary'].assign(repeats=tables['case_summary'].repeated_activity_types.gt(0)).groupby('variant_id').agg(cases=('repeats','size'),repeated_cases=('repeats','sum')).reset_index().merge(views['variants'][['variant_id','median_days']],on='variant_id').to_dict(orient='records')
    (out/'day6_investigation.json').write_text(json.dumps(report,indent=2,allow_nan=False),encoding='utf-8')
    print(json.dumps({'statistics':stats,'target':definition,'timing':times},indent=2))
if __name__=='__main__':main()
