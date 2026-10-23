"""SmartBPM: interactive process intelligence and observed process mining."""
from pathlib import Path
import math
import sys
import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))
from smartbpm.dashboard import C, csv_bytes, filter_cases, load_dashboard_events, prepare_dashboard
from smartbpm.dashboard_charts import dashboard_charts
from smartbpm.ui_mining import render_mining
from smartbpm.ui_performance import render_performance
from smartbpm.ui_ml import render_ml
from smartbpm.ui_predictive import render_predictive

st.set_page_config(page_title="SmartBPM | Process explorer", page_icon="◈", layout="wide")



@st.cache_data(show_spinner="Loading validated event log…", max_entries=2)
def cached_events(path, modified_ns, size):
    return load_dashboard_events(path)


@st.cache_data(show_spinner=False, max_entries=12)
def cached_analysis(events):
    return prepare_dashboard(events)


@st.cache_data(show_spinner=False, max_entries=12)
def cached_cohort(events, cases, activities, resources, first, last, duration):
    return filter_cases(events, cases, activities=activities, resources=resources,
                        start_date=first, end_date=last, duration_range=duration)


def plot(fig, key):
    st.plotly_chart(fig, width="stretch", key=key,
                    config={"displaylogo": False, "scrollZoom": True, "responsive": True})


def reset_filters(activities, resources, dates, duration):
    # Explicit values update browser widgets too; popping keys can leave a stale
    # native slider value that is resubmitted on the next navigation event.
    for key, value in (("activities", list(activities)), ("resources", list(resources)),
                       ("dates", dates), ("duration", duration)):
        st.session_state[key] = value


def main():
    st.title("SmartBPM")
    st.caption("PROCESS INTELLIGENCE  /  HISTORICAL EVIDENCE")
    st.markdown("Explore process behavior, inspect case histories, and compare observed performance.")
    path = ROOT / "data/processed/domestic_declarations_cleaned.parquet"
    try:
        info = path.stat()
        events = cached_events(str(path), info.st_mtime_ns, info.st_size)
        full, full_tables = cached_analysis(events)
    except (OSError, ValueError, TypeError, KeyError) as exc:
        st.error(f"Cannot load the analytical dataset: {exc}")
        st.code("python scripts/run_day2.py")
        st.stop()
    st.caption(f"FULL DATASET · Domestic Declarations · {full['total_cases']:,} cases · {full['total_events']:,} events · {full['total_activities']} activities")
    st.caption(f"Event date range (UTC): {events[C.timestamp].min():%d %b %Y %H:%M} — {events[C.timestamp].max():%d %b %Y %H:%M}")
    cases = full_tables["case_summary"]
    activity_options = sorted(events[C.activity].unique())
    resource_options = sorted(events[C.resource].dropna().unique())
    first, last = cases.start_timestamp.min().date(), cases.start_timestamp.max().date()
    maximum = max(1., float(math.ceil(cases.elapsed_days.max())))
    # One source of initial widget values. Reset callbacks update these same keys;
    # supplying widget defaults as well causes Streamlit's duplicate-state warning.
    for key, value in (("activities", activity_options), ("resources", resource_options),
                       ("dates", (first, last)), ("duration", (0., maximum))):
        if key not in st.session_state:
            st.session_state[key] = value
    with st.sidebar:
        st.markdown("### ◈ SmartBPM")
        section = st.radio("Explore", ["Overview", "Activities & resources", "Variants & repetition", "Case boundaries", "Case explorer", "Process Mining", "Performance Investigation", "ML Preparation", "Predictive Analytics"], key="navigation")
        st.divider()
        st.markdown("### Select a case cohort")
        st.caption("Matches retain complete case histories. OR within each selection; AND between filters. Activity and resource can match different events in a case.")
        with st.expander("Activity selection", expanded=False):
            activities = st.multiselect("Cases containing any activity", activity_options, key="activities")
        resources = st.multiselect("Cases involving any resource", resource_options, key="resources")
        dates = st.date_input("Case start date (UTC)", min_value=first, max_value=last, key="dates",
                              help="Select cases by their first recorded UTC date. Their later events remain included.")
        duration = st.slider("Observed case elapsed days", 0., maximum, step=.1, key="duration",
                             help="Last minus first recorded timestamp, including waiting; not active work time.")
        st.button("Reset filters", on_click=reset_filters, args=(activity_options, resource_options, (first, last), (0., maximum)), width="stretch")
        st.caption("Clear an activity or resource selection to show an empty cohort.")
    if section == 'ML Preparation':
        st.divider()
        render_ml(ROOT)
        return
    if section == 'Predictive Analytics':
        st.divider()
        render_predictive(ROOT)
        return
    if len(dates) != 2:
        st.info("Choose both a start and end date to apply the date range.")
        st.stop()
    cohort = cached_cohort(events, cases, tuple(activities), tuple(resources), dates[0], dates[1], duration)
    summary, tables = cached_analysis(cohort)
    st.caption(f"ACTIVE FILTERS · {len(activities)}/{len(activity_options)} activity matches · {len(resources)}/{len(resource_options)} resource matches · starts {dates[0]} to {dates[1]} UTC · elapsed {duration[0]:g}–{duration[1]:g} days")
    st.subheader("Selected case cohort")
    st.caption(f"{summary['total_cases'] / full['total_cases']:.1%} of all cases · All charts and tables below use the same selected cases.")
    cards = st.columns(4)
    cards[0].metric("Selected cases", f"{summary['total_cases']:,}", border=True, help="Complete cases matching all cohort filters.")
    cards[1].metric("Selected events", f"{summary['total_events']:,}", border=True, help="All recorded events of the selected cases, including events beyond the case-start date window.")
    cards[2].metric("Selected activities", f"{summary['total_activities']:,}", border=True)
    median = summary["duration_days"]["50%"]
    cards[3].metric("Median elapsed days", "—" if median is None else f"{median:.2f}", border=True, help="Median last-minus-first observed timestamp, including waiting. Not active processing time.")
    if cohort.empty:
        st.info("No cases match these filters. Broaden the selections or use Reset filters.")
        st.stop()
    visible_charts = {
        "Overview": ("duration", "trace_length"),
        "Activities & resources": ("activity_frequency", "resource_frequency"),
        "Variants & repetition": ("variants", "repetition"),
        "Case boundaries": ("starting_activities", "ending_activities"),
    }
    charts = dashboard_charts(tables, keys=visible_charts.get(section, ()))
    st.divider()
    if section == "Overview":
        st.subheader("Time across the observed process")
        st.caption("Elapsed duration includes waiting and unobserved intervals; it is not active processing time. Drag to zoom; double-click to reset.")
        left, right = st.columns(2)
        with left:
            st.markdown("#### Case elapsed duration")
            plot(charts["duration"], "duration_chart")
        with right:
            st.markdown("#### Events per case")
            plot(charts["trace_length"], "length_chart")
        st.dataframe(tables["duration_distribution"], hide_index=True, width="stretch")
    elif section == "Activities & resources":
        st.subheader("What happens, and who is recorded?")
        st.caption("Frequency describes observed workload; it does not identify causal bottlenecks. Resource labels represent broad categories, not individual workers.")
        with st.container(border=True):
            st.markdown("#### Activity frequency")
            plot(charts["activity_frequency"], "activity_chart")
            with st.expander("Inspect activity counts"):
                st.dataframe(tables["activity_frequency"], hide_index=True, width="stretch")
        with st.container(border=True):
            st.markdown("#### Resource frequency")
            plot(charts["resource_frequency"], "resource_chart")
            with st.expander("Inspect resource counts"):
                st.dataframe(tables["resource_frequency"], hide_index=True, width="stretch")
    elif section == "Variants & repetition":
        st.subheader("Paths and repeated work")
        st.caption("Repeated activities are possible rework signals, not confirmed waste or errors. Variant IDs are ranked within the selected cohort and may change with filters.")
        a, b = st.columns(2)
        a.metric("Observed variants", f"{summary['variant_count']:,}")
        b.metric("Cases with repeated activities", f"{summary['cases_with_repeated_activities']:,}")
        st.markdown("#### Most common variants")
        plot(charts["variants"], "variant_chart")
        st.caption("Hover to see the full sequence and case share. The table contains every variant.")
        st.dataframe(tables["process_variants"], hide_index=True, width="stretch")
        st.markdown("#### Activities repeated within a case")
        if tables["repeated_activity_summary"].empty:
            st.info("No repeated activities in the selected cases.")
        else:
            plot(charts["repetition"], "repeat_chart")
            st.dataframe(tables["repeated_activities_by_case"], hide_index=True, width="stretch")
    elif section == "Case boundaries":
        st.subheader("First and last observed activities")
        st.caption("Endpoints describe the log. A non-payment endpoint does not prove a case is incomplete; rejection or observation boundaries can also explain it.")
        for key, title in (("starting_activities", "Starting activities"), ("ending_activities", "Ending activities")):
            with st.container(border=True):
                st.markdown(f"#### {title}")
                plot(charts[key], key + "_chart")
    elif section == "Performance Investigation":
        render_performance(cohort, events, tables)
    elif section == "Process Mining":
        render_mining(cohort, summary, tables)
    else:
        st.subheader("Inspect the evidence")
        st.dataframe(tables["case_summary"], hide_index=True, width="stretch")
        st.download_button("Download selected case summary", csv_bytes(tables["case_summary"]), "smartbpm_selected_cases.csv", "text/csv", on_click="ignore")
        case_id = st.selectbox("Inspect a case", tables["case_summary"][C.case].tolist())
        st.dataframe(cohort.loc[cohort[C.case].eq(case_id)], hide_index=True, width="stretch")
    with st.expander("How to interpret these observations"):
        st.markdown("The first and last recorded events bound **observed elapsed duration**, including waiting. Unrecorded earlier or later events can censor a case. Equal timestamps retain source order without establishing causality. No SLA, processing time, worker capacity or causal bottleneck is inferred. All original records are retained.")
        st.caption("Source: BPI Challenge 2020 · Domestic Declarations · validated local analytical dataset. Charts are computed from underlying records, never from PNG exports.")


if __name__ == "__main__":
    main()




