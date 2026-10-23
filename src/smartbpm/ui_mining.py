"""Streamlit presentation for observed process mining; analytical logic stays reusable."""
import json
import pandas as pd
import streamlit as st
from smartbpm.dashboard import C, csv_bytes
from smartbpm.process_mining import discover_transitions, select_transitions, variant_performance, repetition_performance
from smartbpm.process_mining_charts import process_map, duration_comparison
from smartbpm.process_map_data import selected_activity_statistics


@st.cache_data(show_spinner="Discovering observed transitions…", max_entries=8)
def cached_discovery(events):
    return discover_transitions(events)


def render_mining(events, summary, tables):
    st.subheader("Process Intelligence Workspace")
    st.caption("Understand the routes cases take, explore an activity, and compare observed performance.")
    transitions, discovered = cached_discovery(events)
    metrics = st.columns(3)
    metrics[0].metric("Observed transitions", f"{discovered['transition_occurrences']:,}", border=True, help="Consecutive within-case event pairs, counting each occurrence.")
    metrics[1].metric("Distinct relationships", f"{discovered['distinct_transitions']:,}", border=True)
    metrics[2].metric("Observed variants", f"{summary['variant_count']:,}", border=True)
    map_tab, variant_tab, repeat_tab = st.tabs(["Process map & transitions", "Variant performance", "Repetition & duration"])
    with map_tab:
        st.markdown("#### Explore the process")

        mode = st.radio("Map detail", ["Main Process", "Detailed Process"], horizontal=True, key="map_detail")
        reveal_all = mode == "Detailed Process"
        st.caption("Main Process highlights frequent connections, not a single case route. Detailed Process shows every observed connection. Sidebar filters select cases; map controls only change visibility.")
        a, b = st.columns(2)
        minimum = a.number_input("Minimum transition frequency", min_value=1, value=1, step=1, key="map_minimum", disabled=reveal_all)
        maximum = b.number_input("Maximum displayed edges", min_value=1, max_value=100, value=7, step=1, key="map_limit", disabled=reveal_all)
        options = sorted(events[C.activity].unique())
        if "map_focus" in st.session_state:
            st.session_state["map_focus"] = [value for value in st.session_state.map_focus if value in options]
        focus = st.multiselect("Focus on activities (optional)", options, key="map_focus", disabled=reveal_all,
                                help="Display existing edges touching these activities. Empty means no focus. Detailed Process bypasses these display filters.")
        view = st.columns(2)
        direction = view[0].selectbox("Reading direction", ["Left to right", "Top to bottom"], key="map_direction")
        counts = view[1].checkbox("Show edge frequency labels", value=False, help="Counts are always available in arrow tooltips and the transition table. Labels can add clutter in the complete graph.")
        shown = transitions.copy() if reveal_all else select_transitions(transitions, minimum, maximum, focus)
        if "map_activity" in st.session_state and st.session_state.map_activity not in options:
            st.session_state.pop("map_activity")
        selected = st.selectbox("Inspect an activity", options, index=options.index(events[C.activity].value_counts().index[0]), key="map_activity")
        inspected = selected_activity_statistics(events, tables["case_summary"], transitions, shown, selected)
        figure, inventory = process_map(transitions, shown, summary["activity_frequency"], counts,
                                        selected_activity=selected, direction="TB" if direction=="Top to bottom" else "LR", starts=discovered["starts"], ends=discovered["ends"])
        coverage = int(shown.frequency.sum()) if len(shown) else 0
        hidden = len(transitions)-len(shown)
        st.caption(f"DISPLAY ONLY · {len(shown)} relationships shown · {hidden} hidden · {coverage:,} of {discovered['transition_occurrences']:,} transition occurrences. Underlying cases, events and frequencies are unchanged.")
        if shown.empty:
            st.info("No edges meet these display controls. Lower the minimum, clear focus, or choose Detailed Process. Single-event cases have no consecutive pairs.")
        axis = "y" if direction == "Top to bottom" else "x"
        extent = max((node[axis] for node in figure["series"][0]["data"]), default=500)
        chart_height = int(max(640, min(1100, extent + 150))) if axis == "y" else 460
        st.echarts_chart(figure, width="stretch", height=chart_height, renderer="svg", key="process_map_graph",
                         alt="Directed activity graph with zoom and pan. Boxes show readable names; arrows are consecutive event pairs.")
        st.caption("Drag to pan; scroll to zoom. Hover an arrow for its count. Blue marks observed starts; green marks observed ends; teal highlights your selection. These are recorded endpoints, not proof of completion.")
        isolated = pd.DataFrame([row for row in inventory if row["isolated_in_display"]])
        if len(isolated):
            st.info(f"{len(isolated)} activities have no visible relationships. They remain in the data and activity selector; they are listed below rather than scattered around the main flow.")
            with st.expander("Activities outside this view"):
                st.dataframe(isolated[["activity", "event_count", "full_relationships", "hidden_relationships", "isolation_reason"]], hide_index=True, width="stretch")
        else:
            st.caption("Every activity has at least one visible relationship in this view.")
        st.markdown("#### Activity details")
        st.caption(f"Display code: {inspected['node']} | Exact recorded activity below")
        st.write(selected)
        values = st.columns(3)
        values[0].metric("Activity occurrences", f"{inspected['event_count']:,}", border=True)
        values[1].metric("Cases containing activity", f"{inspected['cases']:,}", border=True)
        values[2].metric("Cases repeating activity", f"{inspected['repeating_cases']:,}", border=True)
        st.caption(f"Starts {inspected['starting_cases']:,} cases · ends {inspected['ending_cases']:,} cases · {inspected['incoming_occurrences']:,} incoming / {inspected['outgoing_occurrences']:,} outgoing transition occurrences · {inspected['single_event_cases']:,} single-event cases.")
        st.caption(inspected["isolation_reason"])
        preceding = transitions.loc[transitions.target.eq(selected)].sort_values("frequency", ascending=False)
        following = transitions.loc[transitions.source.eq(selected)].sort_values("frequency", ascending=False)
        left, right = st.columns(2)
        with left:
            st.markdown("##### Common preceding activities")
            st.dataframe(preceding[["source", "frequency", "median_hours"]], hide_index=True, width="stretch") if len(preceding) else st.caption("No previous recorded activity in this cohort.")
        with right:
            st.markdown("##### Common following activities")
            st.dataframe(following[["target", "frequency", "median_hours"]], hide_index=True, width="stretch") if len(following) else st.caption("No next recorded activity in this cohort.")
        st.caption("Median hours describe observed gaps between events, including waiting and unobserved intervals.")
        st.markdown("#### Process insights")
        leading = tables["process_variants"].iloc[0]
        st.write(f"The most common recorded route contains {int(leading.case_count):,} cases ({leading.case_share:.1%} of this cohort).")
        repeats = tables["repeated_activity_summary"]
        if len(repeats):
            st.write(f"{summary['cases_with_repeated_activities']:,} cases repeat an activity. The most commonly repeated label is {repeats.iloc[0][C.activity]} ({int(repeats.iloc[0]['cases']):,} cases). Repetition alone is not a defect.")
        st.caption("Compare longer cases and alternative targets in Performance Investigation. These observations describe associations, not causes.")
        with st.expander("Exact activity names, display codes and related transitions"):
            st.caption("A01-style codes are generated display identifiers, not codes supplied by the XES dataset. Original activity names and counts are preserved. Readable box labels only change presentation.")
            st.dataframe(pd.DataFrame(inventory), hide_index=True, width="stretch")
            st.dataframe(transitions.loc[transitions.source.eq(selected)|transitions.target.eq(selected)], hide_index=True, width="stretch")
        with st.expander("How to read this map"):
            st.write("A variant is the exact recorded activity sequence of one case. Repeated activities can reflect resubmission, additional review or other behavior; repetition alone does not establish an error. Hidden relationships still exist in the complete graph and can be revealed. Frequencies describe recorded behavior, not causal delay or active work. Gaps include waiting and unobserved intervals, which cannot be separated here.")
        st.markdown("#### Displayed transitions and observed elapsed gaps")
        st.dataframe(shown, hide_index=True, width="stretch")
        st.caption("Gap hours = next recorded timestamp minus current timestamp in a case. This can include service, waiting and unobserved intervals; it does not separately measure them. Low-frequency relationships have uncertain percentile estimates. No causal bottleneck is inferred.")
        with st.expander("All cohort transition performance (including hidden edges)"):
            st.dataframe(transitions.sort_values(["p95_hours", "frequency"], ascending=False), hide_index=True, width="stretch")
        x, y = st.columns(2)
        x.download_button("Export displayed transitions", csv_bytes(shown), "smartbpm_displayed_transitions.csv", "text/csv", on_click="ignore")
        y.download_button("Export all cohort transitions", csv_bytes(transitions), "smartbpm_all_transitions.csv", "text/csv", on_click="ignore")
    with variant_tab:
        st.markdown("#### Paths and observed case duration")
        st.caption("Variants are exact ordered activity sequences. Cases are ordered by UTC timestamp and original source row for ties; tied-event causal order remains unknown. IDs/ranks are specific to this cohort.")
        performance = variant_performance(tables["case_summary"], tables["process_variants"])
        st.dataframe(performance, hide_index=True, width="stretch")
        variant_options = performance.variant_id.tolist()
        if "inspect_variant" in st.session_state and st.session_state.inspect_variant not in variant_options:
            st.session_state.pop("inspect_variant")
        if "compare_variants" in st.session_state:
            st.session_state["compare_variants"] = [value for value in st.session_state.compare_variants if value in variant_options]
        selected = st.selectbox("Inspect a variant", variant_options, key="inspect_variant")
        row = performance.loc[performance.variant_id.eq(selected)].iloc[0]
        st.write(" → ".join(json.loads(row.sequence)))
        st.caption(f"{row.case_count:,} cases · {row.case_share:.2%} of selected cases · median elapsed {row.median_days:.2f} days · p95 {row.p95_days:.2f} days")
        chosen = tables["case_summary"].loc[tables["case_summary"].variant_id.eq(selected)]
        st.dataframe(chosen, hide_index=True, width="stretch")
        comparison = st.multiselect("Compare variant duration distributions", performance.variant_id.tolist(), default=None if "compare_variants" in st.session_state else performance.variant_id.head(5).tolist(), key="compare_variants")
        if comparison:
            selected_cases = tables["case_summary"].loc[tables["case_summary"].variant_id.isin(comparison)]
            st.plotly_chart(duration_comparison(selected_cases, "variant_id"), key="variant_duration", width="stretch")
        else:
            st.info("Choose at least one variant for a duration comparison.")
        st.download_button("Export variant performance", csv_bytes(performance), "smartbpm_variant_performance.csv", "text/csv", on_click="ignore")
    with repeat_tab:
        st.markdown("#### Repetition and elapsed-duration associations")
        st.caption("A repeated activity is not automatically unnecessary rework. Case complexity, route, timing and observation boundaries may explain group differences. These are associations, not intervention effects.")
        labeled, groups = repetition_performance(tables["case_summary"], tables["repeated_activities_by_case"])
        st.dataframe(groups, hide_index=True, width="stretch")
        st.caption("Approval/rejection subsets use the observed APPROVED/REJECTED label text. They can overlap each other and the any-repetition group; they are not additive totals or case outcomes.")
        st.plotly_chart(duration_comparison(labeled, "repetition_group"), key="repetition_duration", width="stretch")
        st.dataframe(tables["repeated_activity_summary"], hide_index=True, width="stretch")
        st.download_button("Export repetition group statistics", csv_bytes(groups), "smartbpm_repetition_groups.csv", "text/csv", on_click="ignore")
        st.download_button("Export case repetition flags", csv_bytes(labeled), "smartbpm_case_repetition_flags.csv", "text/csv", on_click="ignore")






