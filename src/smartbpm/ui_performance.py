"""Performance Investigation presentation; all findings use reusable calculations."""
import pandas as pd
import plotly.express as px
import streamlit as st
from smartbpm.dashboard import csv_bytes
from smartbpm.performance import investigate, target_definition, candidate_comparison


@st.cache_data(show_spinner="Investigating historical performance...",max_entries=8)
def cached_investigation(events):
    return investigate(events)


@st.cache_data(show_spinner=False,max_entries=2)
def cached_target(events):
    return target_definition(events)[0]


def render_performance(events, full_events, tables):
    st.subheader("Performance Investigation")
    st.caption("Historical observations | Frozen research design | No predictions on this page")
    stats, views = cached_investigation(events)
    definition = cached_target(full_events)
    a,b,c = st.columns(3)
    a.metric("Mean observed days",f"{stats['mean_days']:.2f}",border=True)
    b.metric("Cases repeating activities",f"{stats['repeated_share']:.1%}",border=True)
    c.metric("Observed variants",str(stats['variants']),border=True)
    duration_tab,repeat_tab,variant_tab,design_tab=st.tabs(["Longer cases","Repeated activities","Alternative paths","ML research design"])
    with duration_tab:
        st.write("Long observed spans identify cases worth understanding; they do not establish failure or active work time.")
        chart=px.histogram(tables['case_summary'],x="elapsed_days",nbins=60,labels={"elapsed_days":"Observed elapsed days"},color_discrete_sequence=["#087f8c"])
        chart.add_vline(x=definition['threshold_days'],line_dash="dash",annotation_text="Frozen training research threshold")
        st.plotly_chart(chart,width="stretch",key="investigation_duration")
        st.dataframe(pd.DataFrame([stats])[["mean_days","median_days","p75_days","p90_days","p95_days"]],hide_index=True,width="stretch")
        st.dataframe(views['thresholds'],hide_index=True,width="stretch")
    with repeat_tab:
        compare=tables['case_summary'].assign(group=tables['case_summary'].repeated_activity_types.gt(0).map({True:"Repeated activity",False:"No repetition"}))
        st.plotly_chart(px.box(compare,x="group",y="elapsed_days",points=False,labels={"elapsed_days":"Observed elapsed days"}),width="stretch",key="investigation_repeat")
        st.dataframe(views['repetition_groups'],hide_index=True,width="stretch")
        st.dataframe(views['repeated_activities'],hide_index=True,width="stretch")
        st.caption("Differences are associations; case complexity and route choice can confound them. Repetition is not automatically avoidable work.")
    with variant_tab:
        variants=views['variants']
        st.plotly_chart(px.scatter(variants,x="case_count",y="median_days",hover_name="variant_id",hover_data=["p95_days"],log_x=True,labels={"case_count":"Cases per exact variant","median_days":"Median observed days"}),width="stretch",key="investigation_variants")
        st.write(f"{stats['rare_variants']} variants contain fewer than 10 cases each, covering {stats['rare_variant_cases']} selected cases. Rarity is a descriptive review rule, not an error label.")
        st.dataframe(views['rare_groups'],hide_index=True,width="stretch")
        st.dataframe(variants,hide_index=True,width="stretch")
        st.download_button("Export investigated variants",csv_bytes(variants),"smartbpm_investigated_variants.csv","text/csv",on_click="ignore")
    with design_tab:
        st.info("Frozen research design anchored to the FULL dataset. Sidebar filters change historical charts, not the target threshold or temporal split. Trained-model validation results are available in Predictive Analytics.")
        st.markdown("#### Predict a longer observed case span")
        st.write("Selected because it has a measurable continuous time basis and a manageable binary research label. Repetition is less frequent and semantically ambiguous; rare variants combine sparse, sample-dependent outcomes.")
        st.write(f"Target = 1 if observed elapsed days > {definition['threshold_days']!r}; otherwise 0.")
        st.caption("Strictly greater than training-only p75. Research-defined threshold, not an official SLA. Observed span is last minus first recorded timestamp.")
        st.write(definition['prediction_point'])
        st.write(f"Event-2 snapshots: {definition['eligible_cases']:,}. This landmark count excludes {definition['excluded_single_event_cases']:,} single-event traces and includes already-known positives and overlapping outcomes; it is not the final ML-ready count.")
        st.caption(f"{definition['already_above_threshold_cases']:,} eligible cases are already above the threshold at prediction time. Report them separately from the {definition['unknown_at_prediction_cases']:,} whose future label is not established by elapsed time alone.")
        st.dataframe(pd.DataFrame(definition['class_balance']),hide_index=True,width="stretch")
        st.markdown("##### Compare prediction points in this selected cohort")
        st.dataframe(views['prediction_points'],hide_index=True,width="stretch")
        st.caption("First-event resource/role are constant, with only two activities. Second event provides nine activities and a median 51-second prefix, at the cost of excluding singleton traces. A submission landmark excludes saved-only cases. A landmark at the last observed timestamp has little observed lead time.")
        st.write("Candidate features: "+", ".join(definition['candidate_features']))
        st.caption("These are Day 6 candidates. The implemented Days 7–8 primary features and final unresolved partitions are shown in ML Preparation. Resource and role remain sensitivity-only until ingestion-time availability is verified.")
        st.write(definition['attribute_availability'])
        with st.expander("Leakage rules and proposed evaluation"):
            st.write(definition['evaluation'])
            st.write("Excluded: "+", ".join(definition['excluded_features']))
            st.dataframe(pd.DataFrame(definition['unknown_label_class_balance']),hide_index=True,width='stretch')
            st.json({key:definition[key] for key in ('validation_start','test_start','split_counts','limitations')})
        candidates=candidate_comparison(stats)
        st.dataframe(candidates,hide_index=True,width="stretch")
        st.download_button("Export candidate comparison",csv_bytes(candidates),"smartbpm_candidate_targets.csv","text/csv",on_click="ignore")
        st.caption("Future human-reviewed interventions need additional evidence. Simulation can explore explicitly assumed span/path scenarios; completion-only timestamps cannot identify service times, capacity or queues. No recommendation or simulation is implemented.")
