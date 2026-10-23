"""Original-feature permutation importance and exact empirical grouped Shapley.

No SHAP-library dependency: six players permit all 64 coalitions to be evaluated
through the exact saved preprocessing pipeline, directly in probability units.
"""
from math import factorial
import numpy as np
import pandas as pd
from sklearn.inspection import permutation_importance
from smartbpm.ml_features import FEATURES,feature_matrix
from smartbpm.ml_training import checked_features,predict_probability,C,TARGET
from smartbpm.ml_evaluation import evaluate

LABELS={'first_activity':'First activity','second_activity':'Second activity','prefix_elapsed_hours':'Prefix elapsed hours',
        'utc_month':'UTC month','utc_weekday':'UTC weekday','utc_hour':'UTC hour'}
LIMITATIONS=['Predictive associations do not establish causes, bottlenecks, inefficiency or intervention benefits.',
    'Marginal shuffling/masking can combine correlated features unrealistically; importance may be shared or suppressed.',
    'Empirical Shapley values depend on the fixed training background; exact coalitions do not remove background-sampling uncertainty.',
    'Validation is reused for model selection, threshold exploration and XAI; test remains locked.',
    'Recorded endpoints may be censored; landmark and overlap-purging exclusions restrict the population.']


def global_importance(model,validation,repeats=10,seed=42):
    if set(validation.split)!={'validation'}:raise ValueError('Global XAI accepts validation rows only')
    if repeats<2:raise ValueError('At least two permutations required to quantify variability')
    x=checked_features(feature_matrix(validation))
    result=permutation_importance(model,x,validation[TARGET],scoring='average_precision',n_repeats=repeats,random_state=seed,n_jobs=1)
    table=pd.DataFrame({'feature':FEATURES,'mean_ap_drop':result.importances_mean,'std_ap_drop':result.importances_std,
        'min_ap_drop':result.importances.min(axis=1),'max_ap_drop':result.importances.max(axis=1)})
    for index in range(repeats):table[f'repeat_{index+1}']=result.importances[:,index]
    if not np.isfinite(table.select_dtypes('number')).all().all():raise ValueError('Invalid permutation importance')
    return table.sort_values('mean_ap_drop',ascending=False).reset_index(drop=True)


def shapley_from_coalitions(values,players=6):
    values=np.asarray(values,dtype=float)
    if values.shape!=(2**players,) or not np.isfinite(values).all():raise ValueError('Invalid coalition values')
    contributions=np.zeros(players)
    for feature in range(players):
        for mask in range(2**players):
            if mask&(1<<feature):continue
            size=mask.bit_count()
            weight=factorial(size)*factorial(players-size-1)/factorial(players)
            contributions[feature]+=weight*(values[mask|(1<<feature)]-values[mask])
    return contributions


def local_explanation(model,features,background):
    if len(features)!=1 or not len(background):raise ValueError('One case and nonempty training background required')
    checked_features(features);checked_features(background)
    features=features.loc[:,FEATURES];background=background.loc[:,FEATURES]
    hybrids=[]
    for mask in range(64):
        hybrid=background.copy()
        for index,name in enumerate(FEATURES):
            if mask&(1<<index):hybrid[name]=features.iloc[0][name]
        hybrids.append(hybrid)
    probabilities=predict_probability(model,pd.concat(hybrids,ignore_index=True)).reshape(64,len(background))
    values=probabilities.mean(axis=1);contributions=shapley_from_coalitions(values)
    probability=float(predict_probability(model,features)[0])
    reconstructed=float(values[0]+contributions.sum())
    error=abs(reconstructed-probability)
    if not np.isfinite(contributions).all() or error>1e-10:raise ValueError('Grouped Shapley probability reconstruction failed')
    return {'method':'Exact grouped interventional Shapley','output_scale':'positive_class_probability',
        'background_cases':len(background),'coalitions':64,'base_probability':float(values[0]),'probability':probability,
        'reconstructed_probability':reconstructed,'absolute_reconstruction_error':error,
        'contributions':[{'feature':name,'label':LABELS[name],'contribution':float(value)} for name,value in zip(FEATURES,contributions)],
        'note':'Base plus all six signed contributions equals probability. Positive values raise model risk relative to the training-background mean. These are probability units, not causal effects.'}


def importance_stability(first,second):
    a=first.set_index('feature').mean_ap_drop.reindex(FEATURES)
    b=second.set_index('feature').mean_ap_drop.reindex(FEATURES)
    correlation=a.rank().corr(b.rank())
    return {'rank_correlation':None if pd.isna(correlation) else float(correlation),
            'top_feature_agreement':first.iloc[0].feature==second.iloc[0].feature,
            'max_absolute_mean_difference':float((a-b).abs().max()),
            'note':'Permutation variation and seed sensitivity, not confidence intervals or an independent validation assessment.'}


def analytical_evidence(models,report,manifest,validation,importance,background,case_id=None,probability_threshold=None):
    family=report['preferred_model'];row=next(r for r in report['comparison'] if r['family']==family)
    threshold=row['recommended_threshold'] if probability_threshold is None else float(probability_threshold)
    if not np.isfinite(threshold) or not 0<=threshold<=1:raise ValueError('Invalid evidence decision threshold')
    references=[{'path':'outputs/reports/day5_transitions.csv','scope':'Full-log observed adjacency, not proof of bottlenecks'},
                {'path':'outputs/reports/day6_investigation.json','scope':'Historical duration/repetition/variant associations'},
                {'path':'docs/DAY7_8_ML_PREPARATION.md','scope':'Target, eligibility, chronology and purging'}]
    for reference in references:
        reference['sha256']=manifest.get('process_reference_sha256',{}).get(reference['path'])
        reference['available_at_export']=reference['sha256'] is not None
    facts={'model':{'family':family,'name':row['model'],'artifact_version':manifest['artifact_version'],
             'selected_model_sha256':manifest['file_sha256']['selected_model.joblib']},
        'prediction_definition':{'landmark':'Immediately after second recorded event','positive_class':'Observed total case duration strictly exceeds research cutoff',
            'duration_cutoff_days':manifest['outcome_threshold_days'],'probability_decision_threshold':threshold,
            'official_sla':False,'approved_features':FEATURES},
        'validation_metrics_at_common_0_5':dict(row['metrics_at_0_5']),
        'validation_metrics_at_saved_f1_threshold':dict(row['tuned_metrics']),
        'global_importance':importance[['feature','mean_ap_drop','std_ap_drop','min_ap_drop','max_ap_drop']].to_dict('records'),
        'process_mining_references':references,'case':None}
    if case_id is not None:
        selected=validation.loc[validation[C.case].eq(case_id)]
        if len(selected)!=1 or not selected.split.eq('validation').all():raise ValueError('Evidence case must be a unique eligible validation case')
        explanation=local_explanation(models[family],feature_matrix(selected),background)
        actual=int(selected[TARGET].iloc[0]);predicted=int(explanation['probability']>=threshold)
        facts['case']={'case_id_display_only':case_id,'prediction_timestamp':selected.prediction_timestamp.iloc[0].isoformat(),
            'event2_features':{k:v.item() if isinstance(v,np.generic) else v for k,v in feature_matrix(selected).iloc[0].items()},
            'predicted_probability':explanation['probability'],'predicted_class':predicted,
            'actual_historical_outcome_evaluation_only':actual,'classification_correct':predicted==actual,'explanation':explanation}
    return {'schema_version':'1.0','purpose':'Analytical evidence for future controlled retrieval; no recommendation generation',
        'facts':facts,'interpretations':{'scope':'Predictive associations only; no causal or intervention claim',
            'advanced_model_ap_gain':report['advanced_ap_gain_over_best_simple']},
        'limitations':LIMITATIONS,'provenance':{'dataset_sha256':manifest['dataset_sha256'],'validation_case_ids_sha256':manifest['partition_id_sha256']['validation'],
            'chronology':{'validation_start':manifest['validation_start'],'test_start':manifest['test_start'],
                         'partition_counts':manifest['partition_counts'],'endpoint_purging':'Training labels end before next evaluation cutoff'},
            'background_source':'Training only, fixed seeded sample','test_evaluated':False},
        'prohibited_inferences':['Feature causes inefficiency','Changing a feature reduces delay','Validated live organizational risk']}
