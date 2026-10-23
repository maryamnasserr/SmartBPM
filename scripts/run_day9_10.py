"""Train the small Day 9-10 experiment and export validation-only artifacts."""
import json
from pathlib import Path
import sys
import time
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from smartbpm.ml_features import feature_matrix
from smartbpm.ml_training import (load_development_data,train_compare,save_artifacts,
    load_artifacts,predict_probability,global_explanation,explain_case,sha256,C)


def main():
    tick=time.perf_counter()
    protected=[ROOT/'data/raw/DomesticDeclarations.xes',ROOT/'data/processed/domestic_declarations_cleaned.parquet',
               ROOT/'data/processed/domestic_declarations_ml_ready.parquet',ROOT/'data/processed/domestic_declarations_ml_audit.parquet']
    before={str(p.relative_to(ROOT)):sha256(p) for p in protected}
    train,validation,provenance=load_development_data(ROOT)
    models,predictions,report=train_compare(train,validation)
    report.update({'outcome_threshold_days':provenance['outcome_threshold_days'],
        'partition_counts':provenance['partition_counts'],'test_evaluated':False,
        'training_cases':len(train),'validation_cases':len(validation),
        'training_class_prevalence':float(train.target_long_observed.mean()),
        'test_policy':provenance['test_policy'],
        'feature_transformations':'Train-median imputation; log1p elapsed hours then train-standardization; first/second activity and UTC calendar categories train-one-hot, unknown -> zero indicators. No class weighting, resampling or post-hoc calibration.',
        'limitations':['Unknown censoring and true outcome availability','Purging/landmark selection limits population',
                      'Single historical validation interval; same validation used for limited selection and decision threshold tuning',
                      'Coefficients, tree rules and importances are associations, not causal effects',
                      'No new organizational-data/live inference interface; test holdout remains locked']})
    provenance['training_case_ids']=train[C.case].tolist()
    provenance['validation_case_ids']=validation[C.case].tolist()
    directory=ROOT/'outputs/models/day9_10'
    manifest=save_artifacts(directory,models,predictions,report,provenance)
    restored,restored_predictions,restored_report,restored_manifest=load_artifacts(directory)
    for family in models:
        p=predict_probability(restored[family],feature_matrix(validation))
        np.testing.assert_array_equal(p,predictions[family+'_probability'])
        for index in [0,len(validation)//2,len(validation)-1]:
            explain_case(restored[family],feature_matrix(validation.iloc[[index]]),family)
        global_explanation(models[family],family).to_csv(directory/f'{family}_explanation.csv',index=False)
    reports=ROOT/'outputs/reports'
    table=[{k:v for k,v in row.items() if k not in ['configuration','metrics_at_0_5','confusion_matrix']} for row in report['comparison']]
    import pandas as pd
    pd.DataFrame(table).to_csv(reports/'day9_10_model_comparison.csv',index=False)
    (reports/'day9_10_validation_results.json').write_text(json.dumps(report,indent=2,allow_nan=False),encoding='utf-8')
    (reports/'day9_10_calibration.json').write_text(json.dumps(report['calibration'],indent=2,allow_nan=False),encoding='utf-8')
    example=validation.iloc[[0]]
    example_report={'case_id':example[C.case].iloc[0],'snapshot':json.loads(example.to_json(orient='records',date_format='iso'))[0],
                    'selected_model':report['preferred_model'],
                    'explanation':explain_case(models[report['preferred_model']],feature_matrix(example),report['preferred_model'])}
    (reports/'day9_10_example_case.json').write_text(json.dumps(example_report,indent=2,allow_nan=False),encoding='utf-8')
    after={str(p.relative_to(ROOT)):sha256(p) for p in protected}
    if before!=after:raise ValueError('Protected dataset changed')
    runtime={'total_seconds':time.perf_counter()-tick,'source_sha256_unchanged':True,'protected_source_sha256':before,
             'artifacts_reloaded_predictions_exact':True,'test_predictions_generated':False,
             'artifact_bytes':{p.name:p.stat().st_size for p in directory.iterdir() if p.is_file()}}
    (reports/'day9_10_runtime.json').write_text(json.dumps(runtime,indent=2),encoding='utf-8')
    print(json.dumps({'comparison':table,'preferred_model':report['preferred_model'],
                      'gain_over_baseline':report['preferred_ap_gain_over_strongest_baseline'],'runtime':runtime},indent=2))


if __name__=='__main__':main()
