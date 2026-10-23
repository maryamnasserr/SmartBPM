"""Purged optimization, artifact binding and exact grouped XAI regression tests."""
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
from smartbpm.ml_training import C,TARGET,train_compare,checked_features,predict_probability,sha256,load_development_data
from smartbpm.ml_features import FEATURES,feature_matrix
from smartbpm.ml_advanced import temporal_folds,fit_advanced,NAMES,save_bundle,load_advanced_bundle
from smartbpm.ml_xai import global_importance,local_explanation,shapley_from_coalitions,importance_stability,analytical_evidence

ROOT=Path(__file__).resolve().parents[1]


@pytest.fixture(scope='module')
def development():
    records=[]
    for i in range(300):
        timestamp=pd.Timestamp('2018-01-01',tz='UTC')+pd.Timedelta(days=i*4)
        records.append({C.case:f'c{i:04}','split':'train' if i<240 else 'validation','prediction_timestamp':timestamp,
            'first_activity':'Submit','second_activity':'Reject' if i%5==0 else 'Review',
            'prefix_elapsed_hours':float(i%9),'utc_month':i%12+1,'utc_weekday':i%7,'utc_hour':i%24,
            TARGET:int(i%5==0 or i%9>=7),'end_timestamp':timestamp+pd.Timedelta(days=2)})
    rows=pd.DataFrame(records);train=rows.loc[rows.split.eq('train')].reset_index(drop=True)
    validation=rows.loc[rows.split.eq('validation')].reset_index(drop=True)
    ends=train.set_index(C.case).end_timestamp
    return train,validation,ends


@pytest.fixture(scope='module')
def experiment(development):
    train,validation,ends=development
    legacy,_,report=train_compare(train,validation)
    return fit_advanced(train,validation,ends,legacy,report)


def test_purged_training_only_temporal_folds(development):
    train,validation,ends=development
    for fold in temporal_folds(train,ends):
        fit=train.iloc[fold['fit']];assess=train.iloc[fold['assess']]
        assert set(fit[C.case]).isdisjoint(assess[C.case])
        assert set(fit[C.case]).isdisjoint(validation[C.case])
        assert fit.prediction_timestamp.max()<assess.prediction_timestamp.min()
        assert ends.loc[fit[C.case]].lt(pd.Timestamp(fold['cutoff'])).all()
    fold=temporal_folds(train,ends)[0]
    changed=ends.copy();case=train.iloc[fold['fit'][0]][C.case]
    changed.loc[case]=pd.Timestamp(fold['cutoff'])
    after=temporal_folds(train,changed)[0]
    assert case not in set(train.iloc[after['fit']][C.case])
    assert after['purged_cases']==fold['purged_cases']+1
    with pytest.raises(ValueError):temporal_folds(train.assign(split='test'),ends)


def test_advanced_models_comparison_and_training_transforms(development,experiment):
    train,validation,_=development;models,predictions,report=experiment
    assert set(models)==set(NAMES) and len(report['comparison'])==6
    assert all(r['decision_threshold']==.5 for r in report['comparison'])
    assert len(report['limited_search'])==4
    for family in ['forest','boosting']:
        scaler=models[family].named_steps['preprocess'].named_transformers_['elapsed'].named_steps['scale']
        assert scaler.mean_[0]==pytest.approx(np.log1p(train.prefix_elapsed_hours).mean())
        p=predict_probability(models[family],feature_matrix(validation))
        np.testing.assert_array_equal(p,predictions[family+'_probability'])
        assert np.isfinite(p).all() and ((p>=0)&(p<=1)).all()
        reordered=feature_matrix(validation)[FEATURES[::-1]]
        np.testing.assert_array_equal(p,predict_probability(models[family],reordered))
        unknown=reordered.iloc[[0]].copy();unknown['second_activity']='Unseen';unknown['prefix_elapsed_hours']=np.nan
        assert np.isfinite(predict_probability(models[family],unknown)).all()
        with pytest.raises(ValueError):predict_probability(models[family],reordered.assign(**{'case:Amount':100}))
    with pytest.raises(ValueError):fit_advanced(train,validation.assign(split='test'),train.set_index(C.case).end_timestamp,{}, {})


def test_permutation_original_groups_and_exact_repeatability(development,experiment):
    _,validation,_=development;models,_,report=experiment
    selected=models[report['preferred_model']]
    first=global_importance(selected,validation,repeats=3,seed=42)
    second=global_importance(selected,validation,repeats=3,seed=42)
    pd.testing.assert_frame_equal(first,second)
    assert set(first.feature)==set(FEATURES) and len(first)==6
    repeats=first[['repeat_1','repeat_2','repeat_3']].to_numpy()
    np.testing.assert_allclose(first.mean_ap_drop,repeats.mean(axis=1))
    np.testing.assert_allclose(first.std_ap_drop,repeats.std(axis=1))
    assert importance_stability(first,second)['top_feature_agreement']
    with pytest.raises(ValueError):global_importance(selected,validation.assign(split='test'))


def test_exact_shapley_known_additive_game_and_symmetry():
    effects=np.array([.1,.2,-.1,0,.03,-.02])
    values=[.4+sum(effects[i] for i in range(6) if mask&(1<<i)) for mask in range(64)]
    np.testing.assert_allclose(shapley_from_coalitions(values),effects,atol=1e-14)
    np.testing.assert_allclose(shapley_from_coalitions([.3]*64),0,atol=1e-14)
    with pytest.raises(ValueError):shapley_from_coalitions([np.nan]*64)
    with pytest.raises(ValueError):shapley_from_coalitions([0]*63)


def test_local_fidelity_all_models_and_schema(development,experiment):
    train,validation,_=development;models,_,_=experiment
    background=feature_matrix(train.iloc[:5]);features=feature_matrix(validation.iloc[[0]])
    for family,model in models.items():
        explanation=local_explanation(model,features,background)
        repeated=local_explanation(model,features,background)
        assert explanation==repeated
        assert explanation['output_scale']=='positive_class_probability'
        assert [r['feature'] for r in explanation['contributions']]==FEATURES
        total=explanation['base_probability']+sum(r['contribution'] for r in explanation['contributions'])
        assert total==pytest.approx(predict_probability(model,features)[0],abs=1e-10)
        assert explanation['absolute_reconstruction_error']<=1e-10
        if family=='prevalence':assert all(abs(r['contribution'])<1e-14 for r in explanation['contributions'])
    with pytest.raises(ValueError):local_explanation(models['forest'],features.assign(case_id='forbidden'),background)
    with pytest.raises(ValueError):local_explanation(models['forest'],features,background.iloc[:0])


def test_serialization_and_evidence_binding(development,experiment,tmp_path):
    train,validation,_=development;models,predictions,report=experiment
    processed=tmp_path/'data/processed';processed.mkdir(parents=True)
    path=processed/'domestic_declarations_ml_ready.parquet'
    pd.concat([train,validation],ignore_index=True).to_parquet(path,index=False)
    background=feature_matrix(train.iloc[:5]);importance=global_importance(models[report['preferred_model']],validation,repeats=2)
    provenance={'dataset_sha256':sha256(path),'validation_case_ids':validation[C.case].tolist(),
        'outcome_threshold_days':11.,'partition_id_sha256':{'validation':'synthetic-validation-hash'},
        'validation_start':validation.prediction_timestamp.min().isoformat(),'test_start':'2030-01-01T00:00:00+00:00',
        'partition_counts':{'train':len(train),'validation':len(validation),'test':0}}
    directory=tmp_path/'outputs/models/day11_12'
    manifest=save_bundle(directory,models,predictions,report,provenance,importance,background)
    restored,after,_,restored_manifest,_,_,_=load_advanced_bundle(tmp_path)
    pd.testing.assert_frame_equal(predictions,after)
    for family in models:
        np.testing.assert_array_equal(predict_probability(models[family],feature_matrix(validation)),predict_probability(restored[family],feature_matrix(validation)))
    evidence=analytical_evidence(restored,report,restored_manifest,validation,importance,background,validation[C.case].iloc[0])
    json.dumps(evidence,allow_nan=False)
    assert evidence['facts']['model']['selected_model_sha256']==manifest['file_sha256']['selected_model.joblib']
    assert set(evidence['facts']['case']['event2_features'])==set(FEATURES)
    assert evidence['provenance']['test_evaluated'] is False
    assert set(['facts','interpretations','limitations','provenance']).issubset(evidence)
    with pytest.raises(ValueError):analytical_evidence(restored,report,manifest,validation,importance,background,'TEST-CASE-NOT-AVAILABLE')
    (directory/'selected_model.joblib').write_bytes(b'corrupted')
    with pytest.raises(ValueError,match='integrity'):load_advanced_bundle(tmp_path)


@pytest.mark.integration
def test_real_model_xai_and_locked_test(monkeypatch):
    original=pd.read_parquet;accesses=[]
    def guard(path,*args,**kwargs):
        if str(path).endswith('domestic_declarations_ml_ready.parquet'):
            assert kwargs.get('filters')==[('split','==','validation')]
            accesses.append(kwargs)
        return original(path,*args,**kwargs)
    monkeypatch.setattr(pd,'read_parquet',guard)
    models,predictions,report,manifest,validation,importance,background=load_advanced_bundle(ROOT)
    assert len(validation)==len(predictions)==1752 and set(models)==set(NAMES)
    assert report['partition_counts']=={'train':5783,'test':2001,'validation':1752}
    assert not report['test_evaluated']
    assert len(importance)==6 and set(background)==set(FEATURES)
    assert set(manifest['background_training_case_ids']).issubset(manifest['training_case_ids'])
    for row in report['comparison']:assert row['cases']==1752 and row['decision_threshold']==.5
    case=validation.iloc[[0]]
    xai=local_explanation(models[report['preferred_model']],feature_matrix(case),background)
    assert xai['absolute_reconstruction_error']<1e-10
    assert accesses


@pytest.mark.integration
def test_xai_dashboard_controls_and_evidence():
    from streamlit.testing.v1 import AppTest
    app=AppTest.from_file(str(ROOT/'app.py'),default_timeout=90).run()
    app.sidebar.radio[0].set_value('Predictive Analytics').run()
    assert not app.exception
    assert len(app.selectbox(key='predictive_model').options)==6
    for family in ['forest','boosting']:
        app.selectbox(key='predictive_model').set_value(family).run()
        assert not app.exception
        before=[m.value for m in app.metric]
        app.slider(key='predictive_threshold_'+family).set_value(.5).run()
        assert not app.exception
    app.radio(key='xai_view').set_value('Local explanations').run()
    assert not app.exception
    assert any('reconstruction' in e.value.lower() for e in app.caption)
    app.selectbox(key='xai_case').set_value(app.selectbox(key='xai_case').options[-1]).run()
    assert not app.exception
    app.radio(key='xai_view').set_value('Analytical evidence').run()
    assert not app.exception and app.get('download_button')
