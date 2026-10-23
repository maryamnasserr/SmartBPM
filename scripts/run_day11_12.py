"""Reproducible advanced ML, original-feature XAI and evidence export; no test scoring."""
import json
from pathlib import Path
import sys
import time
import numpy as np
import pandas as pd
from threadpoolctl import threadpool_limits

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from smartbpm.ml_training import load_development_data,load_validation_bundle,sha256,C,TARGET,predict_probability
from smartbpm.ml_features import feature_matrix
from smartbpm.ml_advanced import fit_advanced,save_bundle,load_advanced_bundle
from smartbpm.ml_xai import global_importance,importance_stability,local_explanation,analytical_evidence,LIMITATIONS


def main():
    tick=time.perf_counter()
    protected=[ROOT/'data/raw/DomesticDeclarations.xes',*sorted((ROOT/'data/processed').glob('*.parquet')),
               *sorted((ROOT/'outputs/models/day9_10').glob('*'))]
    hashes={str(p.relative_to(ROOT)):sha256(p) for p in protected if p.is_file()}
    train,validation,provenance=load_development_data(ROOT)
    legacy_models,_,legacy_report,legacy_manifest,_=load_validation_bundle(ROOT)
    audit=pd.read_parquet(ROOT/'data/processed/domestic_declarations_ml_audit.parquet',
        columns=[C.case,'end_timestamp'],filters=[('split','==','train'),('eligibility','==','unresolved_eligible')])
    ends=audit.set_index(C.case).end_timestamp
    with threadpool_limits(limits=1):
        models,predictions,report=fit_advanced(train,validation,ends,legacy_models,legacy_report)
        selected=models[report['preferred_model']]
        importance=global_importance(selected,validation,repeats=10,seed=42)
        independent_seed=global_importance(selected,validation,repeats=10,seed=43)
        repeated=global_importance(selected,validation,repeats=10,seed=42)
        pd.testing.assert_frame_equal(importance,repeated)
    background_rows=train.sample(n=min(32,len(train)),random_state=42)
    background=feature_matrix(background_rows).reset_index(drop=True)
    report.update({'training_cases':len(train),'validation_cases':len(validation),
        'training_class_prevalence':float(train[TARGET].mean()),'partition_counts':provenance['partition_counts'],
        'outcome_threshold_days':provenance['outcome_threshold_days'],'limitations':LIMITATIONS,
        'xai':{'global_method':'Original-six-column validation permutation AP drop','repeats':10,'seeds':[42,43],
               'same_seed_exactly_reproduced':True,'seed_stability':importance_stability(importance,independent_seed),
               'local_method':'Exact grouped interventional Shapley, probability scale, all 64 coalitions',
               'background_cases':len(background),'background_seed':42,'background_source':'Training only; no outcome-based sampling',
               'library_note':'Direct finite-coalition Shapley implementation avoids a new SHAP/numba dependency and keeps original-feature groups intact through the saved pipeline. This is not a claim that the SHAP package is incompatible.'}})
    report['model_configurations']={family:{'classifier':type(model.named_steps['model']).__name__,
        'parameters':model.named_steps['model'].get_params(deep=False)} for family,model in models.items()}
    provenance['process_reference_sha256']={path:sha256(ROOT/path) for path in [
        'outputs/reports/day5_transitions.csv','outputs/reports/day6_investigation.json','docs/DAY7_8_ML_PREPARATION.md'] if (ROOT/path).is_file()}
    provenance.update({'training_case_ids':train[C.case].tolist(),'validation_case_ids':validation[C.case].tolist(),
        'background_training_case_ids':background_rows[C.case].tolist(),
        'legacy_model_sha256':legacy_manifest['model_sha256']})
    directory=ROOT/'outputs/models/day11_12'
    manifest=save_bundle(directory,models,predictions,report,provenance,importance,background)
    (directory/'feature_schema.json').write_text(json.dumps({'approved_predictors':list(feature_matrix(train).columns),
        'source_dtypes':{c:str(train[c].dtype) for c in feature_matrix(train)},
        'forbidden_inputs':['case ID','target','split','absolute timestamps','final case attributes','resource/role','future events'],
        'preprocessing':'Training-only median/log1p/standardization for elapsed; training one-hot for activities and nominal calendar categories'},indent=2),encoding='utf-8')
    manifest['file_sha256']['feature_schema.json']=sha256(directory/'feature_schema.json')
    (directory/'manifest.json').write_text(json.dumps(manifest,indent=2,allow_nan=False),encoding='utf-8')
    restored,restored_predictions,restored_report,restored_manifest,_,restored_importance,restored_background=load_advanced_bundle(ROOT)
    pd.testing.assert_frame_equal(predictions,restored_predictions)
    pd.testing.assert_frame_equal(importance,restored_importance,check_exact=False,atol=1e-15,rtol=1e-12)
    fidelity=[]
    # Cases fixed by position, not explanation appeal or prediction correctness.
    for index in [0,len(validation)//2,len(validation)-1]:
        row=validation.iloc[[index]];x=feature_matrix(row)
        first=local_explanation(restored[report['preferred_model']],x,restored_background)
        second=local_explanation(restored[report['preferred_model']],x,restored_background)
        assert first==second
        fidelity.append({'case_id':row[C.case].iloc[0],'probability':first['probability'],
                        'absolute_reconstruction_error':first['absolute_reconstruction_error'],'repeated_call_exact':True})
    report['xai']['fidelity_checks']=fidelity
    # Persist the final report and refresh its integrity hash without changing models.
    (directory/'validation_report.json').write_text(json.dumps(report,indent=2,allow_nan=False),encoding='utf-8')
    manifest['file_sha256']['validation_report.json']=sha256(directory/'validation_report.json')
    (directory/'manifest.json').write_text(json.dumps(manifest,indent=2,allow_nan=False),encoding='utf-8')
    reports=ROOT/'outputs/reports'
    importance.to_csv(reports/'day11_12_permutation_importance.csv',index=False)
    independent_seed.to_csv(reports/'day11_12_permutation_seed43.csv',index=False)
    pd.DataFrame([{k:v for k,v in row.items() if k not in ['configuration','confusion_matrix','metrics_at_0_5','tuned_metrics']} for row in report['comparison']]).to_csv(reports/'day11_12_model_comparison.csv',index=False)
    (reports/'day11_12_validation_results.json').write_text(json.dumps(report,indent=2,allow_nan=False),encoding='utf-8')
    evidence=analytical_evidence(restored,report,manifest,validation,importance,restored_background)
    (reports/'day11_12_analytical_evidence.json').write_text(json.dumps(evidence,indent=2,allow_nan=False),encoding='utf-8')
    example=analytical_evidence(restored,report,manifest,validation,importance,restored_background,case_id=validation[C.case].iloc[0])
    (reports/'day11_12_example_evidence.json').write_text(json.dumps(example,indent=2,allow_nan=False),encoding='utf-8')
    after={name:sha256(ROOT/name) for name in hashes}
    if hashes!=after:raise ValueError('Protected data/legacy artifact changed')
    runtime={'elapsed_seconds':time.perf_counter()-tick,'protected_hashes_unchanged':True,'protected_sha256':hashes,
        'reload_predictions_exact':True,'test_predicted_or_evaluated':False,'global_same_seed_exact':True,
        'local_max_reconstruction_error':max(r['absolute_reconstruction_error'] for r in fidelity),
        'artifact_bytes':{p.name:p.stat().st_size for p in directory.iterdir() if p.is_file()}}
    (reports/'day11_12_runtime.json').write_text(json.dumps(runtime,indent=2),encoding='utf-8')
    print(json.dumps({'preferred':report['preferred_model'],'advanced_ap_gain':report['advanced_ap_gain_over_best_simple'],
        'comparison':[{k:r[k] for k in ['family','accuracy','precision','recall','f1','roc_auc','average_precision','brier_score']} for r in report['comparison']],
        'importance':importance[['feature','mean_ap_drop','std_ap_drop']].to_dict('records'),'runtime':runtime},indent=2))


if __name__=='__main__':main()
