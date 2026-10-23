"""Independently check actual validation metrics with rank/count formulas, not sklearn metrics."""
import json
from pathlib import Path
import sys
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from smartbpm.ml_training import load_development_data,load_validation_bundle,checked_features,C,TARGET
from smartbpm.ml_features import feature_matrix


def independent_metrics(y,p,threshold):
    y=np.asarray(y,dtype=int);p=np.asarray(p,dtype=float);prediction=p>=threshold
    positive=y==1;negative=~positive
    tp=int((positive&prediction).sum());fp=int((negative&prediction).sum())
    fn=int((positive&~prediction).sum());tn=int((negative&~prediction).sum())
    precision=tp/(tp+fp) if tp+fp else 0.;recall=tp/(tp+fn)
    descending=np.argsort(-p,kind='stable');sorted_p=p[descending];sorted_y=y[descending]
    ends=np.flatnonzero(np.r_[sorted_p[1:]!=sorted_p[:-1],True])
    cumulative=np.cumsum(sorted_y)[ends]
    ap=float(np.sum(np.diff(np.r_[0,cumulative])/positive.sum()*(cumulative/(ends+1))))
    ranks=pd.Series(p).rank(method='average').to_numpy()
    auc=float((ranks[positive].sum()-positive.sum()*(positive.sum()+1)/2)/(positive.sum()*negative.sum()))
    return {'accuracy':(tp+tn)/len(y),'precision':precision,'recall':recall,
            'f1':2*precision*recall/(precision+recall) if precision+recall else 0.,
            'roc_auc':auc,'average_precision':ap,'brier_score':float(np.mean((y-p)**2)),
            'class_prevalence':float(positive.mean()),'confusion_matrix':[[tn,fp],[fn,tp]]}


def main():
    train,validation,provenance=load_development_data(ROOT)
    models,predictions,report,manifest,_=load_validation_bundle(ROOT)
    assert set(manifest['training_case_ids'])==set(train[C.case])
    assert set(manifest['validation_case_ids'])==set(validation[C.case])
    y=validation[TARGET].to_numpy()
    checks={}
    for row in report['comparison']:
        family=row['family'];p=predictions[family+'_probability'].to_numpy()
        calculated=independent_metrics(y,p,row['decision_threshold'])
        for key,value in calculated.items():np.testing.assert_allclose(value,row[key],atol=1e-12,rtol=0)
        grid=np.round(np.arange(.01,1,.01),2)
        thresholds=[(float(t),independent_metrics(y,p,float(t))['f1']) for t in grid]
        best=max(thresholds,key=lambda pair:(pair[1],-abs(pair[0]-.5),pair[0]))[0]
        assert best==row['decision_threshold']
        scaler=models[family].named_steps['preprocess'].named_transformers_['elapsed'].named_steps['scale']
        np.testing.assert_allclose(scaler.mean_,[np.log1p(train.prefix_elapsed_hours).mean()],atol=1e-12)
        if family in ['logistic','tree']:
            encoder=models[family].named_steps['preprocess'].named_transformers_['category'].named_steps['encode']
            x=checked_features(feature_matrix(train))
            for name,categories in zip(['first_activity','second_activity','utc_month','utc_weekday','utc_hour'],encoder.categories_):
                assert list(categories)==sorted(x[name].unique())
        if family=='prevalence':np.testing.assert_allclose(p,train[TARGET].mean(),atol=1e-15)
        checks[family]=calculated
    result={'passed':True,'method':'Independent grouped precision/recall increments, Mann-Whitney average ranks, count confusion metrics and squared probability errors',
            'model_metrics':checks,'validation_cases':len(validation),'training_preprocessing_verified':True,
            'partition_identity_verified':True,'test_evaluated':False,'test_predictions_generated':False,
            'source_dataset_sha256':provenance['dataset_sha256']}
    (ROOT/'outputs/reports/day9_10_independent_verification.json').write_text(json.dumps(result,indent=2,allow_nan=False),encoding='utf-8')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
