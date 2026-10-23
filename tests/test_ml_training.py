"""Known-answer metrics, train-only fitting, lock guards and exact explanations."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
import pytest
from smartbpm.ml_features import FEATURES,feature_matrix
from smartbpm.ml_training import (C,TARGET,checked_features,make_pipeline,predict_probability,
    train_compare,save_artifacts,load_artifacts,load_development_data,load_validation_bundle,
    explain_case,global_explanation)
from smartbpm.ml_evaluation import evaluate,tune_threshold,diagnostics

ROOT=Path(__file__).resolve().parents[1]


@pytest.fixture(scope='module')
def development():
    records=[]
    for i in range(300):
        records.append({C.case:f'case-{i:04}','split':'train' if i<240 else 'validation',
            'prediction_timestamp':pd.Timestamp('2020-01-01',tz='UTC')+pd.Timedelta(days=i),
            'first_activity':'Submit','second_activity':'Reject' if i%3==0 else 'Approve',
            'prefix_elapsed_hours':float(i%10),'utc_month':i%12+1,'utc_weekday':i%7,'utc_hour':i%24,
            TARGET:int(i%3==0 or i%10>=8)})
    rows=pd.DataFrame(records)
    return rows.loc[rows.split.eq('train')].copy(),rows.loc[rows.split.eq('validation')].copy()


@pytest.fixture(scope='module')
def experiment(development):return train_compare(*development)


def test_known_answer_metrics_and_boundaries():
    result=evaluate([0,0,1,1],[.1,.8,.6,.4],.5)
    assert result['confusion_matrix']==[[1,1],[1,1]]
    for metric in ['accuracy','precision','recall','f1','class_prevalence']:assert result[metric]==.5
    assert result['roc_auc']==.5
    assert result['average_precision']==pytest.approx(7/12)
    assert result['brier_score']==pytest.approx(.2925)
    assert evaluate([0,1],[.5,.5],.5)['confusion_matrix']==[[0,1],[0,1]]
    single=evaluate([0,0],[.1,.2])
    assert single['roc_auc'] is None and single['average_precision'] is None
    assert single['precision']==single['recall']==0


@pytest.mark.parametrize('y,p,t',[([],[],.5),([0],[np.nan],.5),([0],[1.1],.5),([2],[.2],.5),([0],[.2],-1),([0],[.2],np.nan),([0,1],[.5],.5)])
def test_invalid_metrics(y,p,t):
    with pytest.raises(ValueError):evaluate(y,p,t)


def test_threshold_and_calibration_known_answers():
    y=[0,0,1,1];p=[.1,.2,.8,.9]
    assert tune_threshold(y,p)==.5
    data=diagnostics(y,p)
    assert sum(row['cases'] for row in data['reliability'])==4
    assert data['brier_score']==pytest.approx(.025)
    assert data['roc']['false_positive_rate'][0]==0
    assert data['precision_recall']['recall'][0]==1
    # Include p=1 exactly in last bin, rather than dropping it.
    assert diagnostics([0,1],[0,1])['reliability'][-1]['cases']==1


def test_prevalence_is_training_fraction(development,experiment):
    train,validation=development
    models,predictions,_=experiment
    np.testing.assert_allclose(predictions.prevalence_probability,train[TARGET].mean())
    assert train[TARGET].mean()!=.5
    changed=feature_matrix(validation).copy();changed['prefix_elapsed_hours']=999.
    np.testing.assert_array_equal(predict_probability(models['prevalence'],changed),predictions.prevalence_probability)


def test_elapsed_baseline_cannot_use_other_predictors(development,experiment):
    train,validation=development
    models,predictions,_=experiment
    changed=feature_matrix(validation).copy();changed['second_activity']='SECRET';changed['utc_hour']=0
    np.testing.assert_array_equal(predict_probability(models['elapsed'],changed),predictions.elapsed_probability)
    assert list(models['elapsed'].named_steps['preprocess'].get_feature_names_out())==['elapsed__prefix_elapsed_hours']


def test_train_only_preprocessor_and_unknowns(development,experiment):
    train,validation=development
    models,_,_=experiment
    pipeline=models['logistic'].named_steps['preprocess']
    scaler=pipeline.named_transformers_['elapsed'].named_steps['scale']
    assert scaler.mean_[0]==pytest.approx(np.log1p(train.prefix_elapsed_hours).mean())
    encoder=pipeline.named_transformers_['category'].named_steps['encode']
    assert encoder.categories_[1].tolist()==['Approve','Reject']
    unknown=feature_matrix(validation).iloc[:2].copy()
    unknown['first_activity']='NEW';unknown['second_activity']='UNSEEN'
    p=predict_probability(models['logistic'],unknown)
    assert np.isfinite(p).all() and ((p>=0)&(p<=1)).all()
    missing=unknown.copy();missing.loc[:,'prefix_elapsed_hours']=np.nan
    missing['first_activity']=None;missing['utc_month']=np.nan
    for model in models.values():assert np.isfinite(predict_probability(model,missing)).all()
    # New development data can never alter a previously fitted transform.
    assert scaler.mean_[0]==pytest.approx(np.log1p(train.prefix_elapsed_hours).mean())


def test_predictor_schema_order_and_forbidden_metadata(development,experiment):
    _,validation=development;models,_,_=experiment
    original=feature_matrix(validation)
    np.testing.assert_array_equal(predict_probability(models['logistic'],original),predict_probability(models['logistic'],original[FEATURES[::-1]]))
    for bad in [original.drop(columns='first_activity'),original.assign(target_long_observed=1),original.assign(end_timestamp='future'),original.iloc[:0]]:
        with pytest.raises(ValueError):predict_probability(models['logistic'],bad)
    corrupted=original.copy();corrupted.loc[corrupted.index[0],'utc_month']=13
    with pytest.raises(ValueError):checked_features(corrupted)
    corrupted=original.copy();corrupted.loc[corrupted.index[0],'prefix_elapsed_hours']=-1
    with pytest.raises(ValueError):checked_features(corrupted)


def test_no_future_attributes_used_and_no_test_fit(development,experiment):
    train,validation=development
    before=feature_matrix(train)
    changed=train.assign(final_duration=99999,**{'case:Amount':99999})
    pd.testing.assert_frame_equal(before,feature_matrix(changed))
    with pytest.raises(ValueError):train_compare(train,validation.assign(split='test'))
    with pytest.raises(ValueError):train_compare(train.assign(split='test'),validation)
    overlap=validation.copy();overlap.loc[overlap.index[0],C.case]=train.iloc[0][C.case]
    with pytest.raises(ValueError):train_compare(train,overlap)


def test_explanations_exactly_reconstruct_each_probability(development,experiment):
    _,validation=development;models,_,_=experiment
    for family,model in models.items():
        explanation=explain_case(model,feature_matrix(validation.iloc[[0]]),family)
        p=float(predict_probability(model,feature_matrix(validation.iloc[[0]]))[0])
        assert explanation['probability']==p
        if family in ['elapsed','logistic']:
            summed=explanation['intercept']+sum(t['log_odds_contribution'] for t in explanation['terms'])
            assert 1/(1+np.exp(-summed))==pytest.approx(p,abs=1e-12)
        elif family=='tree':assert explanation['leaf_positive_share']==pytest.approx(p)
        assert not global_explanation(model,family).empty


def test_serialization_integrity_reproducibility(development,experiment,tmp_path):
    _,validation=development;models,predictions,report=experiment
    save_artifacts(tmp_path,models,predictions,report,{'test_policy':'locked'})
    restored,after,after_report,_=load_artifacts(tmp_path)
    pd.testing.assert_frame_equal(predictions,after)
    assert report==after_report
    for family in models:
        np.testing.assert_array_equal(predict_probability(models[family],feature_matrix(validation)),predict_probability(restored[family],feature_matrix(validation)))
    repeat=train_compare(*development)
    pd.testing.assert_frame_equal(predictions,repeat[1])
    assert report==repeat[2]
    (tmp_path/'models.joblib').write_bytes(b'broken')
    with pytest.raises(ValueError,match='integrity'):load_artifacts(tmp_path)


@pytest.mark.integration
def test_actual_frozen_dataset_and_locked_test(monkeypatch):
    original=pd.read_parquet;reads=[]
    def guarded(path,*args,**kwargs):
        if str(path).endswith('domestic_declarations_ml_ready.parquet'):
            # Test inputs/outcomes must never be returned to the modeling loader.
            metadata=kwargs.get('columns')==[C.case,'split','prediction_timestamp']
            filtered=kwargs.get('filters') in [[('split','in',['train','validation'])],[('split','==','validation')]]
            assert metadata or filtered
            reads.append(kwargs)
        return original(path,*args,**kwargs)
    monkeypatch.setattr(pd,'read_parquet',guarded)
    train,validation,provenance=load_development_data(ROOT)
    assert len(train)==5783 and len(validation)==1752
    assert provenance['partition_counts']=={'train':5783,'test':2001,'validation':1752}
    assert provenance['outcome_threshold_days']==pytest.approx(11.105428240740741)
    models,predictions,report,manifest,_=load_validation_bundle(ROOT)
    assert not report['test_evaluated']
    assert set(predictions[C.case])==set(validation[C.case])
    assert len(report['comparison'])==4
    for row in report['comparison']:
        calculated=evaluate(validation[TARGET],predictions[row['family']+'_probability'],row['decision_threshold'])
        assert all(row[key]==value for key,value in calculated.items())
    assert reads


@pytest.mark.integration
def test_predictive_dashboard_real_values_and_controls():
    from streamlit.testing.v1 import AppTest
    app=AppTest.from_file(str(ROOT/'app.py'),default_timeout=90).run()
    app.sidebar.radio[0].set_value('Predictive Analytics').run()
    assert not app.exception
    assert [m.value for m in app.metric[:2]]==['5,783','1,752']
    from smartbpm.ml_advanced import NAMES as ADVANCED_NAMES
    report=json.loads((ROOT/'outputs/models/day11_12/validation_report.json').read_text())
    assert app.metric[2].value in ['Logistic','Forest','Boosting','Small tree','Prevalence','Elapsed only']
    assert len(app.get('plotly_chart'))>=7
    assert app.metric[3].value==f"{next(r for r in report['comparison'] if r['family']==report['preferred_model'])['average_precision']:.3f}"
    for family in ['tree','elapsed','prevalence','logistic']:
        app.selectbox(key='predictive_model').set_value(family).run()
        assert not app.exception
        app.slider(key='predictive_threshold_'+family).set_value(.5).run()
        assert not app.exception
    app.selectbox(key='predictive_case').set_value(app.selectbox(key='predictive_case').options[-1]).run()
    assert not app.exception
    app.sidebar.multiselect[0].set_value([]).run()
    assert not app.exception and app.metric[1].value=='1,752'
    app.sidebar.radio[0].set_value('ML Preparation').run()
    assert not app.exception
    assert any('Open Predictive Analytics' in element.value for element in app.info)
    assert not any('has not been trained' in element.value for element in app.info)
    app.sidebar.button[0].click().run()
    app.sidebar.radio[0].set_value('Overview').run()
    assert not app.exception and app.metric[0].value=='10,500'
