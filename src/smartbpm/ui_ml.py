"""Read-only, globally frozen ML preparation report view."""
import json
import pandas as pd
import streamlit as st


def render_ml(root):
    st.subheader('ML Preparation')
    st.info('These are historical labels and preparation statistics, not predictions. Open Predictive Analytics for saved models and historical validation results; the test set remains locked.')
    st.caption('Frozen full-dataset research design. Sidebar cohort filters do not refit thresholds, splits or these preparation statistics.')
    reports = root/'outputs/reports'
    try:
        eligibility = json.loads((reports/'day7_8_eligibility_audit.json').read_text(encoding='utf-8'))
        split = json.loads((reports/'day7_8_split_summary.json').read_text(encoding='utf-8'))
        dictionary = pd.read_csv(reports/'day7_8_feature_dictionary.csv')
    except (OSError,ValueError) as exc:
        st.error(f'Preparation artifacts unavailable: {exc}')
        st.code('python scripts/prepare_ml_dataset.py')
        return
    st.markdown('Predict whether **total observed elapsed duration** exceeds a research threshold, immediately after the **second recorded event**. Equality is negative. This is not remaining duration or an official SLA.')
    a,b,c = st.columns(3)
    a.metric('Unresolved eligible cases',f"{eligibility['final_unresolved_eligible']:,}")
    b.metric('Research threshold days',f"{split['threshold_days']:.12f}")
    c.metric('Already over threshold',f"{eligibility['already_above_threshold_including_overlap']:,}")
    st.markdown('#### Eligibility accounting')
    st.dataframe(pd.DataFrame(eligibility['mutually_exclusive_counts'].items(),columns=['Group','Cases']),hide_index=True,width='stretch')
    st.caption('Known-positive exclusions take priority over overlap exclusions. All case groups sum to the original 10,500 cases.')
    st.markdown('#### Chronological partitions and historical labels')
    st.dataframe(pd.DataFrame(split['final_class_balance']),hide_index=True,width='stretch')
    st.caption(f"Validation begins {split['validation_start']}; test begins {split['test_start']}. Equal timestamps stay together. Training/validation endpoints crossing the next cutoff are purged.")
    st.markdown('#### Feature availability')
    st.markdown('Primary features: first and second activities, prefix elapsed hours, UTC month, weekday and hour. Only two recorded events contribute. Resources and roles are sensitivity-only until ingestion availability is verified. Final case attributes and future outcomes are excluded. IDs and timestamps are audit metadata.')
    st.dataframe(dictionary,hide_index=True,width='stretch')
    st.warning('Observed endpoints do not certify completion. Censoring, source-order timestamp ties, singleton selection and overlap purging limit interpretation. Preprocessing fits only unresolved training rows; later unseen categories use zero indicators.')
