"""Controlled advanced-model search with purged expanding folds inside training."""
import json
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.ensemble import RandomForestClassifier,GradientBoostingClassifier
from smartbpm.ml_features import FEATURES,feature_matrix
from smartbpm.ml_training import (NAMES as OLD_NAMES,SEED,C,TARGET,make_pipeline,
    checked_features,predict_probability,load_development_data,load_validation_bundle,sha256)
from smartbpm.ml_evaluation import evaluate,tune_threshold,diagnostics

VERSION='2.0'
NAMES={**OLD_NAMES,'forest':'Random forest','boosting':'Gradient boosting'}
CONFIGS={'forest':[{'depth':5},{'depth':8}], 'boosting':[{'depth':1},{'depth':2}]}


def advanced_pipeline(family,depth):
    pipeline=make_pipeline('tree')
    if family=='forest':
        model=RandomForestClassifier(n_estimators=120,max_depth=depth,min_samples_leaf=30,
            max_features='sqrt',max_samples=.8,n_jobs=1,random_state=SEED)
    elif family=='boosting':
        model=GradientBoostingClassifier(n_estimators=100,learning_rate=.05,max_depth=depth,
            min_samples_leaf=30,subsample=1.,n_iter_no_change=None,random_state=SEED)
    else:raise ValueError('Unknown advanced model')
    return pipeline.set_params(model=model)


def temporal_folds(train,ends, fractions=(.4,.6,.8,1.)):
    """Equal timestamps stay together; fit labels must end strictly before fold start."""
    if set(train.split)!={'train'} or not train[C.case].is_unique:
        raise ValueError('Inner search accepts unique outer-training cases only')
    if not train[C.case].isin(ends.index).all() or not ends.index.is_unique:
        raise ValueError('Missing/duplicate training endpoint metadata')
    times=train.prediction_timestamp.sort_values().reset_index(drop=True)
    if len(times)<20:raise ValueError('At least 20 training cases required')
    folds=[]
    for start,end in zip(fractions[:-1],fractions[1:]):
        cutoff=times.iloc[int(len(times)*start)]
        stop=times.iloc[int(len(times)*end)] if end<1 else None
        before=train.prediction_timestamp.lt(cutoff)
        mature=train[C.case].map(ends).lt(cutoff)
        fit=np.flatnonzero((before&mature).to_numpy())
        assess=train.prediction_timestamp.ge(cutoff)
        if stop is not None:assess &= train.prediction_timestamp.lt(stop)
        validation=np.flatnonzero(assess.to_numpy())
        if not len(fit) or not len(validation) or set(train.iloc[fit][TARGET])!={0,1} or set(train.iloc[validation][TARGET])!={0,1}:
            raise ValueError('Temporal fold lacks cases or both classes')
        folds.append({'fit':fit,'assess':validation,'cutoff':cutoff.isoformat(),
            'evaluation_end_exclusive':stop.isoformat() if stop is not None else None,
            'purged_cases':int((before&~mature).sum()),'training_cases':len(fit),'assessment_cases':len(validation)})
    return folds


def fit_advanced(train,validation,ends,legacy_models,legacy_report):
    if set(validation.split)!={'validation'} or set(train[C.case])&set(validation[C.case]):
        raise ValueError('Invalid development partition membership')
    if train.prediction_timestamp.max()>=validation.prediction_timestamp.min():raise ValueError('Invalid chronology')
    folds=temporal_folds(train,ends)
    search=[];models=dict(legacy_models);chosen={}
    for family,configs in CONFIGS.items():
        scored=[]
        for config in configs:
            scores=[]
            for fold in folds:
                fit=train.iloc[fold['fit']];assess=train.iloc[fold['assess']]
                model=advanced_pipeline(family,**config)
                model.fit(checked_features(feature_matrix(fit)),fit[TARGET])
                result=evaluate(assess[TARGET],predict_probability(model,feature_matrix(assess)),.5)
                scores.append({'average_precision':result['average_precision'],'brier_score':result['brier_score'],
                               'training_cases':len(fit),'assessment_cases':len(assess)})
            item={'family':family,'configuration':config,'folds':scores,
                  'mean_average_precision':float(np.mean([s['average_precision'] for s in scores])),
                  'std_average_precision':float(np.std([s['average_precision'] for s in scores])),
                  'mean_brier_score':float(np.mean([s['brier_score'] for s in scores]))}
            search.append(item);scored.append(item)
        winner=max(scored,key=lambda r:(r['mean_average_precision'],-r['mean_brier_score'],-r['configuration']['depth']))
        chosen[family]=winner['configuration']
        model=advanced_pipeline(family,**winner['configuration'])
        model.fit(checked_features(feature_matrix(train)),train[TARGET])
        models[family]=model
    predictions=validation[[C.case,'prediction_timestamp',TARGET]].reset_index(drop=True).copy()
    comparison=[];curves={}
    for family,model in models.items():
        p=predict_probability(model,feature_matrix(validation));predictions[family+'_probability']=p
        t=tune_threshold(validation[TARGET],p)
        config=chosen[family] if family in chosen else next(r['configuration'] for r in legacy_report['comparison'] if r['family']==family)
        comparison.append({'family':family,'model':NAMES[family],'configuration':config,
            **evaluate(validation[TARGET],p,.5),'metrics_at_0_5':evaluate(validation[TARGET],p,.5),
            'recommended_threshold':t,'tuned_metrics':evaluate(validation[TARGET],p,t)})
        curves[family]=diagnostics(validation[TARGET],p)
    # Require >= .01 absolute AP gain to replace an adequate simpler model.
    simple=max((r for r in comparison if r['family'] in OLD_NAMES),key=lambda r:(r['average_precision'],-r['brier_score']))
    advanced=max((r for r in comparison if r['family'] not in OLD_NAMES),key=lambda r:(r['average_precision'],-r['brier_score']))
    gain=advanced['average_precision']-simple['average_precision']
    preferred=advanced if gain>=.01 else simple
    baseline=max(r['average_precision'] for r in comparison if r['family'] in ['prevalence','elapsed'])
    return models,predictions,{'artifact_version':VERSION,'random_seed':SEED,'preferred_model':preferred['family'],
        'comparison':comparison,'calibration':curves,'limited_search':search,'chosen_advanced_configurations':chosen,
        'fold_design':[{k:v for k,v in f.items() if k not in ['fit','assess']} for f in folds],
        'selection_rule':'Advanced settings chosen by mean training-only purged temporal-fold AP, Brier then shallower depth as tie-breaks. Replace strongest simpler model only for >=.01 absolute outer-validation AP improvement.',
        'advanced_ap_gain_over_best_simple':gain,'best_advanced_model':advanced['family'],'best_simple_model':simple['family'],
        'preferred_ap_gain_over_strongest_baseline':preferred['average_precision']-baseline,
        'descriptive_improvement_margin':.01,'initial_probability_threshold':.5,
        'threshold_rule':'Initial comparison uses .50 for all six. Exploratory per-model validation-F1 grid .01:.01:.99 retained separately; p>=threshold is positive.',
        'feature_policy':FEATURES,'test_evaluated':False,
        'validation_caveat':'Reused historical validation for family comparison, threshold tuning and XAI: selected exploratory evidence, not independent final performance. Legacy settings were already selected on this validation in Days 9-10.',
        'feature_transformations':legacy_report.get('feature_transformations', 'Training-only median imputation, log1p and scaling for elapsed time; missing-category imputation and safe one-hot encoding for categorical features.'),
        'test_policy':legacy_report.get('test_policy', 'Locked: no test inference, evaluation, calibration or tuning.')}


def save_bundle(directory,models,predictions,report,provenance,importance,background):
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
    joblib.dump(models,directory/'models.joblib',compress=3)
    joblib.dump(models[report['preferred_model']],directory/'selected_model.joblib',compress=3)
    predictions.to_parquet(directory/'validation_predictions.parquet',index=False)
    background.to_parquet(directory/'training_background.parquet',index=False)
    importance.to_csv(directory/'permutation_importance.csv',index=False)
    (directory/'validation_report.json').write_text(json.dumps(report,indent=2,allow_nan=False),encoding='utf-8')
    names=['models.joblib','selected_model.joblib','validation_predictions.parquet','training_background.parquet','permutation_importance.csv','validation_report.json']
    manifest={**provenance,'artifact_version':VERSION,'sklearn_version':sklearn.__version__,
        'numpy_version':np.__version__,'pandas_version':pd.__version__,'random_seed':SEED,
        'file_sha256':{name:sha256(directory/name) for name in names},'selected_model':report['preferred_model'],'feature_schema':FEATURES}
    (directory/'manifest.json').write_text(json.dumps(manifest,indent=2,allow_nan=False),encoding='utf-8')
    return manifest


def load_advanced_bundle(root):
    root=Path(root);directory=root/'outputs/models/day11_12'
    manifest=json.loads((directory/'manifest.json').read_text(encoding='utf-8'))
    if manifest['artifact_version']!=VERSION or manifest['sklearn_version']!=sklearn.__version__ or manifest['feature_schema']!=FEATURES:
        raise ValueError('Advanced artifact version/schema mismatch')
    for name,digest in manifest['file_sha256'].items():
        if Path(name).name!=name or sha256(directory/name)!=digest:raise ValueError('Advanced artifact integrity failure')
    source=root/'data/processed/domestic_declarations_ml_ready.parquet'
    if sha256(source)!=manifest['dataset_sha256']:raise ValueError('Prepared dataset changed')
    validation=pd.read_parquet(source,filters=[('split','==','validation')])
    models=joblib.load(directory/'models.joblib')
    selected=joblib.load(directory/'selected_model.joblib')
    predictions=pd.read_parquet(directory/'validation_predictions.parquet')
    report=json.loads((directory/'validation_report.json').read_text(encoding='utf-8'))
    if set(models)!=set(NAMES) or report['preferred_model']!=manifest['selected_model']:raise ValueError('Advanced model identity mismatch')
    if validation[C.case].tolist()!=predictions[C.case].tolist() or not predictions[C.case].is_unique or not np.array_equal(validation[TARGET],predictions[TARGET]):
        raise ValueError('Validation prediction membership/outcome mismatch')
    if validation[C.case].tolist()!=manifest['validation_case_ids']:raise ValueError('Validation provenance mismatch')
    for family,model in models.items():
        p=predict_probability(model,feature_matrix(validation))
        if not np.array_equal(p,predictions[family+'_probability']):raise ValueError('Advanced reload prediction mismatch')
        row=next(r for r in report['comparison'] if r['family']==family)
        for name,value in evaluate(validation[TARGET],p,.5).items():
            if row[name]!=value:raise ValueError('Advanced comparison mismatch')
    if not np.array_equal(predict_probability(selected,feature_matrix(validation)),predictions[report['preferred_model']+'_probability']):
        raise ValueError('Selected pipeline does not match selected model')
    importance=pd.read_csv(directory/'permutation_importance.csv')
    if set(importance.feature)!=set(FEATURES) or len(importance)!=6:raise ValueError('Invalid original-feature importance schema')
    background=pd.read_parquet(directory/'training_background.parquet')
    checked_features(background)
    return models,predictions,report,manifest,validation,importance,background
