"""Binary historical validation metrics. No feature or estimator fitting here."""
import numpy as np
from sklearn.metrics import (accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, average_precision_score, confusion_matrix, brier_score_loss,
    roc_curve, precision_recall_curve)


def checked_outcomes(y, probabilities):
    y, p = np.asarray(y), np.asarray(probabilities,dtype=float)
    if y.ndim!=1 or p.ndim!=1 or len(y)!=len(p) or not len(y):
        raise ValueError('Expected nonempty, equally sized outcome/probability vectors')
    if not np.isin(y,[0,1]).all() or not np.isfinite(p).all() or ((p<0)|(p>1)).any():
        raise ValueError('Outcomes must be binary; probabilities finite in [0,1]')
    return y.astype('int8'),p


def evaluate(y, probabilities, decision_threshold=.5):
    y,p=checked_outcomes(y,probabilities)
    if not np.isfinite(decision_threshold) or not 0<=decision_threshold<=1:
        raise ValueError('Decision threshold must be in [0,1]')
    predicted=(p>=decision_threshold).astype('int8')
    both=len(np.unique(y))==2
    return {'cases':len(y),'decision_threshold':float(decision_threshold),
        'accuracy':float(accuracy_score(y,predicted)),
        'precision':float(precision_score(y,predicted,zero_division=0)),
        'recall':float(recall_score(y,predicted,zero_division=0)),
        'f1':float(f1_score(y,predicted,zero_division=0)),
        'roc_auc':float(roc_auc_score(y,p)) if both else None,
        'average_precision':float(average_precision_score(y,p)) if both else None,
        'brier_score':float(brier_score_loss(y,p)),
        'class_prevalence':float(y.mean()),
        'confusion_matrix':confusion_matrix(y,predicted,labels=[0,1]).tolist()}


def tune_threshold(y, probabilities):
    """Max validation F1 on a predefined .01:.01:.99 grid; ties nearest .5, then higher."""
    checked_outcomes(y,probabilities)
    grid=np.round(np.arange(.01,1.,.01),2)
    scores=[(t,evaluate(y,probabilities,float(t))['f1']) for t in grid]
    return float(max(scores,key=lambda item:(item[1],-abs(item[0]-.5),item[0]))[0])


def diagnostics(y, probabilities):
    y,p=checked_outcomes(y,probabilities)
    if len(np.unique(y))!=2:
        raise ValueError('ROC/PR diagnostics require both outcome classes')
    fpr,tpr,_=roc_curve(y,p)
    precision,recall,_=precision_recall_curve(y,p)
    bins=[]
    # Uniform bins, with p=1 included in the final bin; report occupancy.
    indices=np.minimum((p*10).astype(int),9)
    for index in range(10):
        mask=indices==index
        if mask.any():
            bins.append({'bin_lower':index/10,'bin_upper':(index+1)/10,'cases':int(mask.sum()),
                         'mean_probability':float(p[mask].mean()),'observed_positive_share':float(y[mask].mean())})
    return {'roc':{'false_positive_rate':fpr.tolist(),'true_positive_rate':tpr.tolist()},
            'precision_recall':{'recall':recall.tolist(),'precision':precision.tolist()},
            'reliability':bins,'brier_score':float(brier_score_loss(y,p)),
            'note':'Calibration diagnostic only: no post-hoc calibration fitted. Brier measures overall probability error, not calibration alone.'}
