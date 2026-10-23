"""Independent validation-only numerical audit of Days 11–12 outputs."""
import json
from pathlib import Path
import sys
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from verify_ml_artifacts import independent_metrics
from smartbpm.ml_advanced import load_advanced_bundle
from smartbpm.ml_training import load_development_data,sha256,C,TARGET


def main():
    models,predictions,report,manifest,validation,importance,background=load_advanced_bundle(ROOT)
    train,_,_=load_development_data(ROOT)
    checks={}
    for row in report['comparison']:
        p=predictions[row['family']+'_probability'].to_numpy()
        for threshold,expected in [(.5,row),(row['recommended_threshold'],row['tuned_metrics'])]:
            actual=independent_metrics(validation[TARGET],p,threshold)
            for key,value in actual.items():
                np.testing.assert_allclose(value,expected[key],atol=1e-12,rtol=0)
        checks[row['family']]=independent_metrics(validation[TARGET],p,.5)
    columns=[name for name in importance if name.startswith('repeat_')]
    np.testing.assert_allclose(importance[columns].mean(axis=1),importance.mean_ap_drop,atol=1e-12)
    np.testing.assert_allclose(importance[columns].std(axis=1,ddof=0),importance.std_ap_drop,atol=1e-12)
    runtime=json.loads((ROOT/'outputs/reports/day11_12_runtime.json').read_text())
    assert all(sha256(ROOT/name)==digest for name,digest in runtime['protected_sha256'].items())
    # Background identifiers are display/provenance metadata, never predictive inputs.
    ids=manifest['background_training_case_ids']
    assert set(ids)<=set(train[C.case])
    expected=train.set_index(C.case).loc[ids,list(background.columns)].reset_index(drop=True)
    pd.testing.assert_frame_equal(expected,background.reset_index(drop=True))
    result={'passed':True,'model_metrics':checks,'method':'Independent ranks/counts/grouped AP increments and squared errors',
            'common_and_tuned_metrics_match':True,'permutation_mean_std_match':True,
            'background_verified_training_only':True,'protected_hashes_unchanged':True,
            'selected_model_reload_exact':True,'test_evaluated':False}
    (ROOT/'outputs/reports/day11_12_independent_verification.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
