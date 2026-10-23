"""Original-feature XAI and structured evidence controls; no LLM calls."""
import json
import pandas as pd
import plotly.express as px
import streamlit as st
from smartbpm.ml_features import feature_matrix
from smartbpm.ml_training import C,TARGET
from smartbpm.ml_xai import local_explanation,analytical_evidence,LABELS,LIMITATIONS


@st.cache_data(show_spinner=False,max_entries=128)
def cached_local(model_hash,family,case_id,_model,features,background):
    return local_explanation(_model,features,background)


def render_contributions(explanation,chart,key):
    terms=pd.DataFrame(explanation['contributions'])
    terms=terms.sort_values('contribution')
    st.write(f"Training-background mean risk **{explanation['base_probability']:.1%}** plus the six contributions gives **{explanation['probability']:.1%}**. All contributions are on the probability scale.")
    fig=px.bar(terms,x='contribution',y='label',orientation='h',color='contribution',
        color_continuous_scale=['#3b63cc','#dfe9ee','#087f8c'],color_continuous_midpoint=0,
        labels={'contribution':'Risk contribution','label':''})
    fig.update_layout(coloraxis_showscale=False,height=390)
    chart(fig,key)
    st.caption(f"Exact original-feature Shapley calculation: 64 coalitions, {explanation['background_cases']} fixed training background cases. Reconstruction error {explanation['absolute_reconstruction_error']:.2e}. Positive terms increase this model's risk relative to that background; negative terms decrease it. They are not causal effects.")
    nonzero=terms.loc[terms.contribution.abs().gt(1e-10)]
    if len(nonzero):
        leading=nonzero.iloc[nonzero.contribution.abs().argmax()]
        st.write(f"The largest absolute contribution is **{leading['label']}**, which {'raises' if leading.contribution>0 else 'lowers'} fitted risk by {abs(leading.contribution)*100:.2f} percentage points relative to this explanation's background allocation.")
    else:st.write('This model assigns the same risk regardless of these feature values; there is no measurable local contribution.')
    with st.expander('Exact grouped contribution values and method limits'):
        st.dataframe(terms[['feature','contribution']],hide_index=True,width='stretch')
        st.write('All original columns are masked as complete groups through the saved pipeline. The value function averages predicted probability over fixed training-background rows. Hybrid cases can be unrealistic when predictors are correlated; background sampling and masking assumptions affect attribution.')


def render_xai(models,report,manifest,validation,importance,background,chart):
    family=report['preferred_model'];model=models[family]
    row=next(r for r in report['comparison'] if r['family']==family)
    st.markdown(f"#### Explainable AI · selected model: {row['model']}")
    st.caption('These explanations are tied to the saved selected artifact. The Inspect model control elsewhere does not change this global XAI analysis.')
    scope=st.radio('Explanation view',['Global explanations','Local explanations','Analytical evidence'],horizontal=True,key='xai_view')
    if scope=='Global explanations':
        fig=px.bar(importance.assign(label=importance.feature.map(LABELS)),x='mean_ap_drop',y='label',error_x='std_ap_drop',orientation='h',
            labels={'mean_ap_drop':'AP drop after shuffling','label':''},color_discrete_sequence=['#087f8c'])
        chart(fig,'xai_permutation')
        display=importance[['feature','mean_ap_drop','std_ap_drop','min_ap_drop','max_ap_drop']].copy()
        display['feature']=display.feature.map(LABELS)
        st.dataframe(display.rename(columns={'feature':'Feature','mean_ap_drop':'Mean AP drop','std_ap_drop':'Shuffle SD','min_ap_drop':'Minimum','max_ap_drop':'Maximum'}),hide_index=True,width='stretch')
        st.write('A larger AP reduction means the fitted model relies more on that original feature for validation ranking. Error bars show variability over ten shuffles, not confidence intervals. Zero or negative values are retained.')
        low=importance.loc[importance.mean_ap_drop.le(.005),'feature'].map(LABELS).tolist()
        st.caption('Features with mean AP drop at most .005 in this run: '+(', '.join(low) if low else 'none')+'. Low measured reliance does not prove a feature is irrelevant in the process.')
        stability=report['xai']['seed_stability']
        st.write(f"Two fixed seed runs: rank correlation {stability['rank_correlation']}, top-feature agreement {stability['top_feature_agreement']}. The original seed was rerun and reproduced exactly.")
        st.markdown('##### Connect predictive associations to historical evidence')
        st.write('For timing-related associations, inspect Performance Investigation → Longer cases. For first/second activity associations, inspect Process Mining and Case explorer. These pages provide historical context; an important predictor does not identify a bottleneck or prove inefficiency.')
    else:
        case_id=st.selectbox('Explain a validation declaration',validation[C.case].tolist(),key='xai_case')
        selected=validation.loc[validation[C.case].eq(case_id)]
        snapshot=selected.iloc[0]
        threshold=st.slider('XAI probability decision threshold',.01,.99,float(row['recommended_threshold']),.01,key='xai_threshold',
            help='Explores classification only; model probabilities and explanations remain unchanged.')
        explanation=cached_local(manifest['file_sha256']['selected_model.joblib'],family,case_id,model,feature_matrix(selected),background)
        predicted=int(explanation['probability']>=threshold);actual=int(snapshot[TARGET])
        st.write(f"**{case_id}** · {snapshot.prediction_timestamp.isoformat()}")
        st.dataframe(feature_matrix(selected).rename(columns=LABELS),hide_index=True,width='stretch')
        a,b,c=st.columns(3)
        a.metric('Predicted risk',f"{explanation['probability']:.1%}")
        b.metric('Predicted class','Long-running' if predicted else 'Not long-running')
        c.metric('Historical outcome','Long-running' if actual else 'Not long-running')
        st.write('Correct classification' if predicted==actual else 'Incorrect classification')
        st.caption('Case ID is display metadata only; historical outcome is evaluation-only. Only the six Event-2 inputs above enter the model.')
        if scope=='Local explanations':render_contributions(explanation,chart,'xai_local')
        else:
            evidence=analytical_evidence(models,report,manifest,validation,importance,background,case_id,threshold)
            st.write('The export separates measured facts, bounded interpretations, provenance and limitations. It contains no recommendations and makes no LLM call.')
            st.json(evidence,expanded=False)
            st.download_button('Download analytical evidence JSON',json.dumps(evidence,indent=2,allow_nan=False),
                'smartbpm_analytical_evidence.json','application/json',on_click='ignore')
    with st.expander('XAI limitations'):
        for note in LIMITATIONS:st.write(note)
