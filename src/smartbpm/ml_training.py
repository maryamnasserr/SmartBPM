"""Small interpretable sklearn experiment. Modeling APIs never evaluate test rows."""
import hashlib
import json
from pathlib import Path
import platform
import warnings
import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler, FunctionTransformer
from sklearn.impute import SimpleImputer
from sklearn.dummy import DummyClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from sklearn.exceptions import ConvergenceWarning
from smartbpm.ml_features import FEATURES, feature_matrix, construct_target
from smartbpm.dashboard import C
from smartbpm.ml_evaluation import evaluate,tune_threshold,diagnostics

VERSION='1.0'
SEED=42
TARGET='target_long_observed'
NAMES={'prevalence':'Training prevalence','elapsed':'Elapsed-time baseline',
       'logistic':'Logistic regression','tree':'Constrained decision tree'}
CALENDAR=['utc_month','utc_weekday','utc_hour']
CATEGORIES=['first_activity','second_activity']+CALENDAR


def sha256(path):
    with Path(path).open('rb') as source:return hashlib.file_digest(source,'sha256').hexdigest()


def checked_features(frame):
    """Reject metadata/future columns. Restore canonical order; allow nulls for imputers."""
    if not isinstance(frame,pd.DataFrame) or frame.empty or set(frame)!=set(FEATURES):
        raise ValueError('Prediction input must contain exactly the six approved predictors')
    result=frame.loc[:,FEATURES].copy()
    for name in ['prefix_elapsed_hours']+CALENDAR:
        result[name]=pd.to_numeric(result[name],errors='raise')
        if np.isinf(result[name].dropna()).any():raise ValueError('Infinite numerical feature')
    if result.prefix_elapsed_hours.dropna().lt(0).any():raise ValueError('Negative prefix elapsed time')
    for name,lower,upper in [('utc_month',1,12),('utc_weekday',0,6),('utc_hour',0,23)]:
        valid=result[name].dropna()
        if not valid.between(lower,upper).all() or not valid.eq(np.floor(valid)).all():
            raise ValueError('Invalid UTC calendar category')
        result[name]=result[name].map(lambda value:np.nan if pd.isna(value) else str(int(value))).astype(object)
    for name in ['first_activity','second_activity']:
        valid=result[name].dropna()
        if not valid.map(lambda value:isinstance(value,str) and bool(value.strip())).all():
            raise ValueError('Activities must be nonblank strings or missing')
        result[name]=result[name].astype(object).where(result[name].notna(),np.nan)
    return result


def load_development_data(root):
    """Read test identifiers/split/time metadata only, never test predictors/outcomes.

    Modeling records are predicate-filtered to train/validation. The existing audit
    supplies outcome consistency and endpoint checks for those partitions only.
    """
    root=Path(root)
    path=root/'data/processed/domestic_declarations_ml_ready.parquet'
    metadata=pd.read_parquet(path,columns=[C.case,'split','prediction_timestamp'])
    if metadata.empty or not metadata[C.case].is_unique or metadata.isna().any().any() or not metadata.split.isin(['train','validation','test']).all():
        raise ValueError('Invalid frozen partition metadata')
    original_membership=pd.read_parquet(root/'data/processed/domestic_declarations_ml_audit.parquet',
        columns=[C.case,'split','prediction_timestamp'],filters=[('eligibility','==','unresolved_eligible')])
    if not metadata.sort_values(C.case).reset_index(drop=True).equals(original_membership.sort_values(C.case).reset_index(drop=True)):
        raise ValueError('Partition assignments differ from the frozen preparation audit')
    for a,b in [('train','validation'),('validation','test')]:
        earlier=metadata.loc[metadata.split.eq(a),'prediction_timestamp']
        later=metadata.loc[metadata.split.eq(b),'prediction_timestamp']
        if earlier.empty or later.empty or earlier.max()>=later.min():raise ValueError('Invalid chronological partitions')
    rows=pd.read_parquet(path,filters=[('split','in',['train','validation'])])
    if set(rows.split)!= {'train','validation'} or rows.isna().any().any():raise ValueError('Invalid development dataset')
    checked_features(feature_matrix(rows))
    design=json.loads((root/'outputs/reports/day7_8_split_summary.json').read_text(encoding='utf-8'))
    audit=pd.read_parquet(root/'data/processed/domestic_declarations_ml_audit.parquet',
                          filters=[('split','in',['train','validation']),('eligibility','==','unresolved_eligible')])
    audit=audit.set_index(C.case).loc[rows[C.case]]
    if len(audit)!=len(rows) or not audit.index.is_unique:raise ValueError('Audit membership mismatch')
    for name in FEATURES+['split','prediction_timestamp',TARGET]:
        if not np.array_equal(rows[name],audit[name]):raise ValueError('Frozen row differs from case audit: '+name)
    if not np.array_equal(rows[TARGET],construct_target(audit.elapsed_days,design['threshold_days'])):
        raise ValueError('Outcome threshold/label mismatch')
    if rows.prefix_elapsed_hours.gt(design['threshold_days']*24).any():raise ValueError('Known positive in unresolved cohort')
    for split,boundary in [('train','validation_start'),('validation','test_start')]:
        if audit.loc[audit.split.eq(split),'end_timestamp'].ge(pd.Timestamp(design[boundary])).any():
            raise ValueError('Outcome overlaps evaluation cutoff')
    train=rows.loc[rows.split.eq('train')].reset_index(drop=True)
    validation=rows.loc[rows.split.eq('validation')].reset_index(drop=True)
    for part in [train,validation]:
        if set(part[TARGET])!={0,1}:raise ValueError('Both outcome classes required')
    return train,validation,{'outcome_threshold_days':design['threshold_days'],
        'partition_counts':{str(k):int(v) for k,v in metadata.split.value_counts().items()},
        'partition_id_sha256':{name:hashlib.sha256('\n'.join(sorted(g[C.case])).encode()).hexdigest() for name,g in metadata.groupby('split')},
        'validation_start':design['validation_start'],'test_start':design['test_start'],
        'dataset_sha256':sha256(path),'test_policy':'Locked: no test feature transformation, prediction, metrics or tuning. Only identifiers/split/time metadata checked.'}


def make_pipeline(family, *, c=1., depth=3):
    elapsed=Pipeline([('impute',SimpleImputer(strategy='median',keep_empty_features=True)),
                      ('log1p',FunctionTransformer(np.log1p,feature_names_out='one-to-one')),
                      ('scale',StandardScaler())])
    transformers=[('elapsed',elapsed,['prefix_elapsed_hours'])]
    if family in ['logistic','tree']:
        categorical=Pipeline([('impute',SimpleImputer(strategy='constant',fill_value='__MISSING__',keep_empty_features=True)),
                              ('encode',OneHotEncoder(handle_unknown='ignore',sparse_output=False))])
        transformers.append(('category',categorical,CATEGORIES))
    preprocess=ColumnTransformer(transformers,remainder='drop',sparse_threshold=0)
    if family=='prevalence':model=DummyClassifier(strategy='prior',random_state=SEED)
    elif family in ['elapsed','logistic']:
        model=LogisticRegression(C=c,solver='lbfgs',max_iter=2000,tol=1e-8,random_state=SEED)
    elif family=='tree':model=DecisionTreeClassifier(max_depth=depth,min_samples_leaf=100,random_state=SEED)
    else:raise ValueError('Unknown model family')
    return Pipeline([('preprocess',preprocess),('model',model)])


def predict_probability(pipeline, features):
    x=checked_features(features)
    p=pipeline.predict_proba(x)[:,list(pipeline.classes_).index(1)]
    if not np.isfinite(p).all() or ((p<0)|(p>1)).any():raise ValueError('Invalid predicted probabilities')
    return p


def train_compare(train,validation):
    if set(train.split)!={'train'} or set(validation.split)!={'validation'}:
        raise ValueError('Training/comparison accepts train and validation partitions only')
    if not train[C.case].is_unique or not validation[C.case].is_unique or set(train[C.case])&set(validation[C.case]):
        raise ValueError('Overlapping or duplicate development cases')
    if train.prediction_timestamp.max()>=validation.prediction_timestamp.min():raise ValueError('Development partitions not chronological')
    x=checked_features(feature_matrix(train));xv=feature_matrix(validation)
    y=train[TARGET].to_numpy();yv=validation[TARGET].to_numpy()
    if set(y)!={0,1} or set(yv)!={0,1}:raise ValueError('Both binary classes required')
    candidates=[('prevalence',{}),('elapsed',{}),('logistic',{'c':.1}),('logistic',{'c':1.}),
                ('tree',{'depth':3}),('tree',{'depth':4})]
    selected={};search=[]
    for family,config in candidates:
        model=make_pipeline(family,**config)
        # A convergence defect is a training failure; never silently publish it.
        with warnings.catch_warnings():
            warnings.simplefilter('error',ConvergenceWarning)
            model.fit(x,y)
        probabilities=predict_probability(model,xv)
        score=evaluate(yv,probabilities)
        entry={'family':family,'configuration':config,'average_precision':score['average_precision'],'brier_score':score['brier_score']}
        search.append(entry)
        rank=(score['average_precision'],-score['brier_score'])
        if family not in selected or rank>selected[family]['rank']:
            selected[family]={'rank':rank,'pipeline':model,'configuration':config,'probabilities':probabilities}
    models={};comparison=[];curves={};predictions=validation[[C.case,'prediction_timestamp',TARGET]].reset_index(drop=True).copy()
    for family,item in selected.items():
        models[family]=item['pipeline'];p=item['probabilities']
        threshold=tune_threshold(yv,p)
        comparison.append({'family':family,'model':NAMES[family],'configuration':item['configuration'],
                           **evaluate(yv,p,threshold),'metrics_at_0_5':evaluate(yv,p,.5)})
        curves[family]=diagnostics(yv,p)
        predictions[family+'_probability']=p
    # Predeclared .005 AP near-tie margin, favor simpler baseline/logistic models.
    best=max(row['average_precision'] for row in comparison)
    preferred=next(family for family in ['prevalence','elapsed','logistic','tree']
                   if next(row for row in comparison if row['family']==family)['average_precision']>=best-.005)
    preferred_row=next(row for row in comparison if row['family']==preferred)
    strongest_baseline=max(row['average_precision'] for row in comparison if row['family'] in ['prevalence','elapsed'])
    return models,predictions,{'artifact_version':VERSION,'random_seed':SEED,
        'preferred_model':preferred,'comparison':comparison,'limited_search':search,
        'selection_rule':'Highest validation average precision; within .005 of best favor prevalence, elapsed, logistic, then tree. Brier breaks within-family ties.',
        'threshold_rule':'Per-model validation F1 maximized on .01:.01:.99; ties nearest .5, then higher. Positive if p >= threshold.',
        'positive_class':'1: total observed elapsed duration strictly greater than frozen research threshold',
        'preferred_ap_gain_over_strongest_baseline':preferred_row['average_precision']-strongest_baseline,
        'descriptive_improvement_margin':.01,
        'calibration':curves,'feature_policy':FEATURES,
        'validation_caveat':'Same validation set used for selection and threshold tuning: exploratory, optimistically selected results, not final generalization estimates.'}


def global_explanation(pipeline, family):
    names=pipeline.named_steps['preprocess'].get_feature_names_out()
    model=pipeline.named_steps['model']
    if family in ['logistic','elapsed']:
        return pd.DataFrame({'transformed_feature':names,'coefficient':model.coef_[0],
                             'odds_multiplier_per_unit':np.exp(model.coef_[0])}).sort_values('coefficient',key=abs,ascending=False)
    if family=='tree':
        return pd.DataFrame({'transformed_feature':names,'split_importance':model.feature_importances_}).sort_values('split_importance',ascending=False)
    return pd.DataFrame({'explanation':['Every case receives the training positive fraction. No feature-specific effects.']})


def explain_case(pipeline, features, family):
    if len(features)!=1:raise ValueError('Choose exactly one case')
    x=checked_features(features)
    transformed=pipeline.named_steps['preprocess'].transform(x)
    names=pipeline.named_steps['preprocess'].get_feature_names_out()
    model=pipeline.named_steps['model'];p=float(predict_probability(pipeline,features)[0])
    if family in ['logistic','elapsed']:
        terms=transformed[0]*model.coef_[0]
        intercept=float(model.intercept_[0]);logit=intercept+float(terms.sum())
        reconstructed=float(1/(1+np.exp(-logit)))
        if not np.isclose(reconstructed,p,atol=1e-12):raise ValueError('Logistic explanation does not reconstruct probability')
        return {'kind':'logistic','probability':p,'intercept':intercept,'log_odds':logit,
                'reconstructed_probability':reconstructed,
                'terms':[{'feature':str(n),'transformed_value':float(v),'coefficient':float(c),'log_odds_contribution':float(t)}
                         for n,v,c,t in zip(names,transformed[0],model.coef_[0],terms)],
                'note':'Intercept plus signed terms equals model log-odds; sigmoid gives risk. Terms are associations relative to the encoded origin, not probability-point changes or causal effects.'}
    if family=='tree':
        tree=model.tree_;node=0;path=[]
        while tree.children_left[node]!=tree.children_right[node]:
            index=tree.feature[node];value=float(transformed[0,index]);threshold=float(tree.threshold[node])
            left=value<=threshold
            path.append({'feature':str(names[index]),'transformed_value':value,'operator':'<=' if left else '>',
                         'split_threshold':threshold,'training_cases_at_node':int(tree.n_node_samples[node])})
            node=tree.children_left[node] if left else tree.children_right[node]
        values=tree.value[node,0];reconstructed=float(values[1]/values.sum())
        if not np.isclose(reconstructed,p,atol=1e-12):raise ValueError('Tree explanation does not reconstruct probability')
        return {'kind':'tree','probability':p,'path':path,'leaf_training_cases':int(tree.n_node_samples[node]),
                'leaf_positive_share':reconstructed,
                'note':'Risk is the training positive fraction in this leaf; listed conditions are the exact transformed decision path, not causes.'}
    return {'kind':'prevalence','probability':p,'training_positive_fraction':float(model.class_prior_[1]),
            'note':'Constant training prevalence; no case-specific feature explanation.'}


def save_artifacts(directory,models,predictions,report,provenance):
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
    model_path=directory/'models.joblib';prediction_path=directory/'validation_predictions.parquet'
    joblib.dump(models,model_path,compress=3)
    predictions.to_parquet(prediction_path,index=False)
    manifest={'artifact_version':VERSION,'sklearn_version':sklearn.__version__,'numpy_version':np.__version__,
              'pandas_version':pd.__version__,'python_version':platform.python_version(),
              'model_sha256':sha256(model_path),'predictions_sha256':sha256(prediction_path),**provenance}
    (directory/'manifest.json').write_text(json.dumps(manifest,indent=2,allow_nan=False),encoding='utf-8')
    (directory/'validation_report.json').write_text(json.dumps(report,indent=2,allow_nan=False),encoding='utf-8')
    return manifest


def load_artifacts(directory):
    """Load this project's trusted local artifacts only (joblib uses pickle)."""
    directory=Path(directory)
    manifest=json.loads((directory/'manifest.json').read_text(encoding='utf-8'))
    if manifest['artifact_version']!=VERSION or manifest['sklearn_version']!=sklearn.__version__:
        raise ValueError('Artifact version/environment mismatch; regenerate with the pinned environment')
    if sha256(directory/'models.joblib')!=manifest['model_sha256'] or sha256(directory/'validation_predictions.parquet')!=manifest['predictions_sha256']:
        raise ValueError('Artifact integrity check failed')
    models=joblib.load(directory/'models.joblib')
    predictions=pd.read_parquet(directory/'validation_predictions.parquet')
    report=json.loads((directory/'validation_report.json').read_text(encoding='utf-8'))
    if set(models)!=set(NAMES) or set(predictions.columns)!={C.case,'prediction_timestamp',TARGET,*[f+'_probability' for f in NAMES]}:
        raise ValueError('Invalid model/prediction artifact schema')
    return models,predictions,report,manifest


def load_validation_bundle(root):
    """Verify deployed artifacts and validation predictions, without fitting/test inference."""
    root=Path(root)
    models,predictions,report,manifest=load_artifacts(root/'outputs/models/day9_10')
    source=root/'data/processed/domestic_declarations_ml_ready.parquet'
    if sha256(source)!=manifest['dataset_sha256']:raise ValueError('Dataset changed since model preparation')
    validation=pd.read_parquet(source,filters=[('split','==','validation')])
    if not predictions[C.case].is_unique or predictions[C.case].tolist()!=validation[C.case].tolist():
        raise ValueError('Validation prediction membership/order mismatch')
    if manifest['validation_case_ids']!=validation[C.case].tolist() or not np.array_equal(validation[TARGET],predictions[TARGET]):
        raise ValueError('Validation artifact outcomes/membership mismatch')
    for family in models:
        p=predict_probability(models[family],feature_matrix(validation))
        if not np.array_equal(p,predictions[family+'_probability']):raise ValueError('Reloaded model predictions differ')
        row=next(r for r in report['comparison'] if r['family']==family)
        for name,value in evaluate(validation[TARGET],p,row['decision_threshold']).items():
            if row[name]!=value:raise ValueError('Saved validation metrics differ: '+name)
    return models,predictions,report,manifest,validation
