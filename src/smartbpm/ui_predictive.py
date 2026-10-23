"""Interactive validation workbench. Never trains a model or evaluates the test set."""
import numpy as np
import calendar
from html import escape
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from smartbpm.dashboard import C
from smartbpm.ml_features import feature_matrix
from smartbpm.ml_training import (TARGET,explain_case,
    predict_probability,global_explanation)
from smartbpm.ml_advanced import load_advanced_bundle,NAMES
from smartbpm.ml_xai import local_explanation
from smartbpm.ui_xai import render_xai,render_contributions,cached_local
from smartbpm.ml_evaluation import evaluate,diagnostics

METRICS={'Average precision (PR-AUC)':'average_precision','ROC-AUC':'roc_auc',
         'Brier score (lower is better)':'brier_score','Accuracy':'accuracy',
         'Precision':'precision','Recall':'recall','F1-score':'f1'}


def feature_label(name):
    if name=='elapsed__prefix_elapsed_hours':return 'Elapsed time (log-scaled)'
    for prefix,title in [('category__first_activity_','First activity'),('category__second_activity_','Second activity')]:
        if name.startswith(prefix):
            value=escape(name.removeprefix(prefix).removeprefix('Declaration ').replace('_',' ').title())
            return title+'<br>'+value.replace(' By ','<br>')
    for prefix,title in [('category__utc_month_','Month'),('category__utc_weekday_','Weekday'),('category__utc_hour_','UTC hour')]:
        if name.startswith(prefix):
            value=name.removeprefix(prefix)
            if value.isdigit():
                value=calendar.month_name[int(value)] if title=='Month' else (calendar.day_name[int(value)] if title=='Weekday' else value)
            return title+': '+value
    return name


@st.cache_resource(show_spinner='Verifying saved models and validation predictions...',max_entries=2)
def cached_bundle(root,manifest_ns,models_ns,report_ns,predictions_ns,source_ns):
    return load_advanced_bundle(root)


def chart(fig,key):
    fig.update_layout(template='plotly_white',font=dict(family='Arial, sans-serif',color='#25334a'),
                      margin=dict(l=15,r=20,t=35,b=45),height=fig.layout.height or 350,legend=dict(orientation='h',y=-.22))
    st.plotly_chart(fig,width='stretch',key=key,config={'displaylogo':False,'responsive':True})


def render_predictive(root):
    st.subheader('Predictive Analytics')
    st.caption('EVENT-2 RISK  /  HISTORICAL VALIDATION WORKBENCH')
    try:
        directory=root/'outputs/models/day11_12'
        times=[p.stat().st_mtime_ns for p in [directory/'manifest.json',directory/'models.joblib',
            directory/'validation_report.json',directory/'validation_predictions.parquet',
            root/'data/processed/domestic_declarations_ml_ready.parquet']]
        models,predictions,report,manifest,validation,importance,background=cached_bundle(str(root),*times)
    except (OSError,ValueError,KeyError,TypeError) as exc:
        st.error(f'Predictive artifacts unavailable or inconsistent: {exc}')
        st.code('python scripts/run_day11_12.py')
        return
    preferred=report['preferred_model']
    st.info('These are historical validation results. The test set is locked. This page does not provide live organizational predictions.')
    st.markdown(f"Estimate whether **total observed case duration exceeds {manifest['outcome_threshold_days']!r} days**, immediately after the **second recorded event**. This research cutoff is not an official SLA.")
    st.caption('Frozen unresolved cohort: sidebar filters do not change these models or validation cases. No training occurs when you use this page.')
    st.caption(f"Eligible unresolved population: {sum(manifest['partition_counts'].values()):,} cases after singleton, already-known-positive and overlap exclusions. The research target and partitions are unchanged.")
    selected_row=next(row for row in report['comparison'] if row['family']==preferred)
    a,b,c,d=st.columns(4)
    a.metric('Training cases',f"{report['training_cases']:,}")
    b.metric('Validation cases',f"{report['validation_cases']:,}")
    c.metric('Preferred model',{'logistic':'Logistic','tree':'Small tree','elapsed':'Elapsed only','prevalence':'Prevalence','forest':'Forest','boosting':'Boosting'}[preferred],help=NAMES[preferred])
    d.metric('Validation average precision',f"{selected_row['average_precision']:.3f}",help='Area summarized by average precision; higher is better. This is selected validation performance, not final test performance.')
    st.caption(f"Locked test cases: {manifest['partition_counts']['test']:,}. Positive class = historical observed duration strictly above the research cutoff. Equality is negative.")
    family=st.selectbox('Inspect model',list(NAMES),index=list(NAMES).index(preferred),format_func=NAMES.get,key='predictive_model')
    row=next(r for r in report['comparison'] if r['family']==family)
    # Keep model-specific thresholds stable when switching the model control.
    recommended=row['recommended_threshold']
    threshold=st.slider('Probability decision threshold',.01,.99,float(recommended),.01,
                        key='predictive_threshold_'+family,
                        help='Classify as long-running when risk is at least this probability. This is separate from the duration cutoff in days. Moving it explores validation tradeoffs; it does not retrain or save changes.')
    st.caption(f"Saved validation-F1 threshold for this model: {recommended:.2f}. Current threshold: {threshold:.2f}. Initial comparison uses the same 0.50 threshold for all models.")
    comparison_tab,evaluation_tab,case_tab,threshold_tab,xai_tab,interpretation_tab=st.tabs(['Model comparison','Validation evaluation','Case prediction explorer','Decision threshold explorer','Explainable AI','Research interpretation'])
    with comparison_tab:
        metric_label=st.selectbox('Comparison metric',list(METRICS),key='predictive_metric')
        metric=METRICS[metric_label]
        policy=st.selectbox('Comparison threshold policy',['Common 0.50','Validation-F1 thresholds'],key='predictive_comparison_policy')
        comparison=[dict(r,**r['tuned_metrics']) if policy=='Validation-F1 thresholds' else r for r in report['comparison']]
        records=[{key:r[key] for key in ['model','decision_threshold','accuracy','precision','recall','f1','roc_auc','average_precision','brier_score','class_prevalence']} for r in comparison]
        table=pd.DataFrame(records)
        st.caption('All six models use the same validation cases. Initial classification metrics use probability 0.50 for every model; the optional tuned view is explicitly exploratory. Advanced hyperparameters use purged temporal folds within training only.')
        chart(px.bar(table,x=metric,y='model',orientation='h',color='model',color_discrete_sequence=['#92a8bd','#668bab','#087f8c','#3b63cc','#8f6ca8','#bc843b'],
                     labels={'model':'','average_precision':'Average precision','roc_auc':'ROC-AUC',metric:metric_label}), 'predictive_comparison')
        st.dataframe(table.rename(columns={'model':'Model','decision_threshold':'Decision threshold','average_precision':'Average precision (PR-AUC)',
            'roc_auc':'ROC-AUC','brier_score':'Brier score','class_prevalence':'Validation prevalence'}),hide_index=True,width='stretch')
        st.caption('ROC-AUC, average precision and Brier use probabilities. Accuracy, precision, recall, F1 and confusion matrices use thresholded classes. Undefined precision when no positives are predicted is reported as 0. Average precision is not trapezoidal PR area.')
        with st.expander('Why compare baselines and fixed thresholds?'):
            st.write('Training prevalence gives every case the same risk. The elapsed-time baseline uses only the gap between Events 1 and 2. A richer model should add value beyond these simple references. Threshold tuning can change accuracy substantially; inspect the fixed 0.50 results below as well.')
            fixed=pd.DataFrame([{'Model':r['model'],**{key:r['metrics_at_0_5'][key] for key in ['accuracy','precision','recall','f1']}} for r in report['comparison']])
            st.dataframe(fixed,hide_index=True,width='stretch')
    p=predictions[family+'_probability'].to_numpy();y=predictions[TARGET].to_numpy()
    current=evaluate(y,p,threshold)
    diagnostic=diagnostics(y,p)
    with evaluation_tab:
        st.markdown(f'#### {NAMES[family]} · validation evidence')
        left,right=st.columns(2)
        with left:
            matrix=np.array(current['confusion_matrix'])
            fig=go.Figure(go.Heatmap(z=matrix,x=['Predicted not long','Predicted long'],y=['Observed not long','Observed long'],
                                    text=matrix,texttemplate='%{text}',colorscale='Teal',showscale=False))
            fig.update_layout(title=f'Confusion matrix · probability ≥ {threshold:.2f}')
            chart(fig,'predictive_confusion')
            st.caption('Rows are historical outcomes; columns are predicted classes. Off-diagonal cells are mistakes. The duration cutoff and probability decision threshold are different quantities.')
        with right:
            dist=pd.DataFrame({'Outcome':['Not long-running','Long-running'],'Cases':[(y==0).sum(),(y==1).sum()]})
            chart(px.bar(dist,x='Outcome',y='Cases',color='Outcome',color_discrete_sequence=['#668bab','#087f8c'],title='Validation class distribution'),'predictive_classes')
            st.caption(f"Historical positive share: {current['class_prevalence']:.1%}. Precision = positive predictions that were positive; recall = historical positives identified.")
        left,right=st.columns(2)
        with left:
            fig=go.Figure(go.Scatter(x=diagnostic['roc']['false_positive_rate'],y=diagnostic['roc']['true_positive_rate'],mode='lines',name=NAMES[family]))
            fig.add_scatter(x=[0,1],y=[0,1],mode='lines',line=dict(dash='dash',color='#92a8bd'),name='Chance reference')
            fig.update_layout(title=f"ROC curve · AUC {current['roc_auc']:.3f}",xaxis_title='False positive rate',yaxis_title='True positive rate (recall)')
            chart(fig,'predictive_roc')
        with right:
            fig=go.Figure(go.Scatter(x=diagnostic['precision_recall']['recall'],y=diagnostic['precision_recall']['precision'],mode='lines',name=NAMES[family]))
            fig.add_hline(y=float(y.mean()),line_dash='dash',annotation_text='Validation prevalence')
            fig.update_layout(title=f"Precision–recall · average precision {current['average_precision']:.3f}",xaxis_title='Recall',yaxis_title='Precision')
            chart(fig,'predictive_pr')
        st.caption('ROC and precision–recall curves sweep probability thresholds. They do not move when only the current decision threshold changes. PR is especially useful for the smaller positive class.')
        bins=pd.DataFrame(diagnostic['reliability'])
        fig=go.Figure(go.Scatter(x=bins.mean_probability,y=bins.observed_positive_share,mode='lines+markers',
            customdata=bins[['cases']].to_numpy(),hovertemplate='Mean risk %{x:.1%}<br>Observed positive %{y:.1%}<br>Cases %{customdata[0]}<extra></extra>',name=NAMES[family]))
        fig.add_scatter(x=[0,1],y=[0,1],mode='lines',line=dict(dash='dash',color='#92a8bd'),name='Perfect agreement')
        fig.update_layout(title=f"Reliability curve · Brier {current['brier_score']:.4f}",xaxis_title='Mean predicted probability',yaxis_title='Observed positive share',xaxis_range=[0,1],yaxis_range=[0,1])
        chart(fig,'predictive_calibration')
        st.caption(f"Mean predicted validation risk: {p.mean():.1%}; observed positive share: {y.mean():.1%}. This comparison checks overall agreement, not individual certainty.")
        st.caption('Each point groups cases in a probability bin; hover for its sample size. Near the diagonal means better agreement. Sparse bins are uncertain. Lower Brier means lower average squared probability error; it is not a pure calibration measure. No recalibration was fitted.')
    with case_tab:
        case_id=st.selectbox('Choose a validation case',validation[C.case].tolist(),key='predictive_case')
        selected=validation.loc[validation[C.case].eq(case_id)]
        snapshot=selected.iloc[0]
        probability=float(predict_probability(models[family],feature_matrix(selected))[0])
        actual=int(snapshot[TARGET]);predicted=int(probability>=threshold)
        st.markdown('#### Information recorded at Event 2')
        st.write(f"First activity: **{snapshot.first_activity}**")
        st.write(f"Second activity: **{snapshot.second_activity}**")
        st.caption(f"Prediction timestamp: {snapshot.prediction_timestamp.isoformat()} · prefix elapsed: {snapshot.prefix_elapsed_hours:.6f} hours")
        a,b,c=st.columns(3)
        a.metric('Predicted long-running risk',f'{probability:.1%}')
        b.metric('Predicted class','Long-running' if predicted else 'Not long-running')
        c.metric('Actual historical outcome','Long-running' if actual else 'Not long-running')
        st.write(f"**{'Correct classification' if predicted==actual else 'Incorrect classification'}** at probability threshold {threshold:.2f}.")
        st.caption('Only approved Event-2 features enter the model. The historical outcome is shown for retrospective evaluation and is never supplied as a predictor. This case belongs to validation, not the test set.')
        explanation=(dict(cached_local(manifest['file_sha256']['models.joblib'],family,case_id,models[family],feature_matrix(selected),background),kind='grouped_shapley')
            if family in ['forest','boosting'] else explain_case(models[family],feature_matrix(selected),family))
        st.markdown('#### Why did this model assign this risk?')
        if explanation['kind']=='grouped_shapley':
            render_contributions(explanation,chart,'predictive_grouped_contributions')
        elif explanation['kind']=='logistic':
            terms=pd.DataFrame(explanation['terms'])
            active=terms.loc[terms.log_odds_contribution.abs().gt(1e-12)].copy()
            active=active.sort_values('log_odds_contribution',key=abs,ascending=False)
            st.write(f"Starting log-odds {explanation['intercept']:.4f}, plus recorded-feature contributions {terms.log_odds_contribution.sum():.4f}, gives log-odds {explanation['log_odds']:.4f}. Converting with the logistic function gives {probability:.1%} risk.")
            if not active.empty:
                active['readable_feature']=active.feature.map(feature_label)
                fig=px.bar(active,x='log_odds_contribution',y='readable_feature',orientation='h',custom_data=['feature'],
                           labels={'log_odds_contribution':'Contribution to model log-odds','readable_feature':''},color_discrete_sequence=['#087f8c'])
                fig.update_layout(height=max(350,len(active)*65))
                chart(fig, 'predictive_case_terms')
            st.caption('Positive terms raise model log-odds; negative terms lower them relative to the encoded reference. These are not percentage-point changes or causal effects. Calendar values are categories; elapsed time is log-transformed and standardized on training data.')
            with st.expander('Exact additive calculation'):
                st.dataframe(terms,hide_index=True,width='stretch')
        elif explanation['kind']=='tree':
            st.write(f"This case follows the rules below to a leaf containing {explanation['leaf_training_cases']:,} training cases. Their positive share is {explanation['leaf_positive_share']:.1%}, which equals the predicted risk.")
            path=pd.DataFrame(explanation['path'])
            if not path.empty:path['feature']=path.feature.map(lambda name:feature_label(name).replace('<br>',' · '))
            st.dataframe(path,hide_index=True,width='stretch')
        else:
            st.write(f"This baseline assigns every case the training positive fraction: {probability:.1%}. It makes no case-specific feature distinction.")
        st.caption('Associations explain the fitted calculation; they do not prove why a case took longer.')
    with threshold_tab:
        st.markdown('#### Decision threshold explorer')
        a,b,c=st.columns(3)
        a.metric('Precision at current threshold',f"{current['precision']:.3f}")
        b.metric('Recall at current threshold',f"{current['recall']:.3f}")
        c.metric('F1 at current threshold',f"{current['f1']:.3f}")
        grid=np.round(np.arange(.01,1.,.01),2)
        positive=p[:,None]>=grid
        tp=(positive&(y[:,None]==1)).sum(axis=0);fp=(positive&(y[:,None]==0)).sum(axis=0)
        precision=np.divide(tp,tp+fp,out=np.zeros_like(grid),where=tp+fp>0)
        recall=tp/y.sum();f1=np.divide(2*precision*recall,precision+recall,out=np.zeros_like(grid),where=precision+recall>0)
        curves=pd.DataFrame({'Probability threshold':grid,'Precision':precision,'Recall':recall,'F1':f1})
        figure=px.line(curves,x='Probability threshold',y=['Precision','Recall','F1'])
        figure.add_vline(x=threshold,line_dash='dash')
        chart(figure,'predictive_threshold_tradeoffs')
        st.dataframe(pd.DataFrame(current['confusion_matrix'],index=['Observed negative','Observed positive'],columns=['Predicted negative','Predicted positive']),width='stretch')
        st.caption('Changing the slider changes classes, precision, recall, F1 and confusion counts. It never refits preprocessing/models or changes risk probabilities. These are reused-validation tradeoffs, not independent final performance.')
    with xai_tab:
        render_xai(models,report,manifest,validation,importance,background,chart)
    with interpretation_tab:
        gain=report['preferred_ap_gain_over_strongest_baseline']
        st.markdown(f"#### Preferred model: {NAMES[preferred]}")
        st.write(f"{report['selection_rule']} Validation average precision gain over the strongest baseline: {gain:+.4f}.")
        if gain>=report['descriptive_improvement_margin']:
            st.write('The preferred model adds descriptive validation ranking value beyond the baselines. This is exploratory evidence, not a significance test or a demonstrated operational benefit.')
        else:
            st.write('The preferred model does not show a clear validation improvement over the strongest baseline under the predefined 0.01 descriptive margin. Do not claim that model complexity has demonstrated practical value.')
        st.write(report['validation_caveat'])
        advanced_gain=report['advanced_ap_gain_over_best_simple']
        st.write(f"Best advanced model: {NAMES[report['best_advanced_model']]}; AP difference versus best simpler model: {advanced_gain:+.4f}. "+('Advanced ML exceeded the predefined .01 descriptive margin.' if advanced_gain>=.01 else 'The predefined .01 improvement margin was not met; the simpler model is retained.'))
        leading=importance.iloc[0]
        st.write(f"Largest measured original-feature reliance: {leading.feature}, mean validation AP drop {leading.mean_ap_drop:.4f} ± {leading.std_ap_drop:.4f} across ten permutations. See Explainable AI for variability and masking limits.")
        st.markdown(f'##### Feature associations · {NAMES[family]}')
        if family in ['forest','boosting']:
            global_table=pd.DataFrame({'transformed_feature':models[family].named_steps['preprocess'].get_feature_names_out(),
                                       'supplementary_native_importance':models[family].named_steps['model'].feature_importances_}).sort_values('supplementary_native_importance',ascending=False)
        else:global_table=global_explanation(models[family],family).copy()
        if 'transformed_feature' in global_table:
            global_table.insert(0,'Feature',global_table.transformed_feature.map(lambda name:feature_label(name).replace('<br>',' · ')))
        st.dataframe(global_table,hide_index=True,width='stretch')
        st.caption('Logistic coefficients are per transformed unit; exp(coefficient) multiplies model odds. Full one-hot category coefficients should be interpreted relative to the encoded origin or contrasted within the same feature group. Tree split importance is training impurity reduction, not direction, validation importance or a causal effect.')
        st.warning('Recorded durations may be censored. Singleton/known-positive exclusions and endpoint purging restrict the population and can bias results. A single historical validation period does not establish future generalization or calibrated live risk. No intervention benefit follows from these associations.')
        with st.expander('Reproducibility and model settings'):
            st.json({key:report[key] for key in ['artifact_version','random_seed','limited_search','threshold_rule','feature_transformations','test_policy']})
