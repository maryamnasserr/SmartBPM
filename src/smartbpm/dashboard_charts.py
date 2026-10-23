"""Interactive Plotly figures built exclusively from analytical tables."""
import json
import plotly.express as px

TEAL = "#087f8c"
BLUE = "#3b63cc"


def dashboard_charts(tables, top_n=10, bins=40, keys=None):
    if not tables:
        return {}
    wanted = set(keys) if keys is not None else {"activity_frequency", "resource_frequency", "starting_activities", "ending_activities", "duration", "trace_length", "variants", "repetition"}
    charts = {}
    for key, label, value in (("activity_frequency", "activity", "event_count"),
                              ("resource_frequency", "resource", "event_count"),
                              ("starting_activities", "activity", "case_count"),
                              ("ending_activities", "activity", "case_count")):
        if key not in wanted:
            continue
        frame = tables[key].iloc[::-1]
        fig = px.bar(frame, x=value, y=label, orientation="h", color_discrete_sequence=[TEAL],
                     labels={value: value.replace("_", " ").title(), label: ""})
        fig.update_traces(hovertemplate="%{y}<br>Count: %{x:,}<extra></extra>")
        if label == "activity":
            fig.update_yaxes(tickmode="array", tickvals=frame[label], ticktext=[value.removeprefix("Declaration ").replace(" by ", "<br>") for value in frame[label]], tickfont=dict(size=12))
        fig.update_layout(height=max(320, len(frame) * 30 + 100))
        charts[key] = fig
    cases = tables["case_summary"]
    if "duration" in wanted:
        charts["duration"] = px.histogram(cases, x="elapsed_days", nbins=bins, color_discrete_sequence=[TEAL],
                                           labels={"elapsed_days": "Observed elapsed days"})
        charts["duration"].update_layout(yaxis_title="Cases", bargap=.06)
    if "trace_length" in wanted:
        lengths = cases.event_count.value_counts().sort_index().rename_axis("events_per_case").reset_index(name="cases")
        charts["trace_length"] = px.bar(lengths, x="events_per_case", y="cases", color_discrete_sequence=[BLUE],
                                        labels={"events_per_case": "Events per case", "cases": "Cases"})
    if "variants" in wanted:
        variants = tables["process_variants"].head(top_n).copy()
        variants["readable_sequence"] = variants.sequence.map(lambda s: "<br>".join(json.loads(s)))
        charts["variants"] = px.bar(variants, x="variant_id", y="case_count", custom_data=["case_share", "readable_sequence"],
                                    color_discrete_sequence=[TEAL], labels={"variant_id": "Variant (ranked within cohort)", "case_count": "Cases"})
        charts["variants"].update_traces(hovertemplate="%{x}: %{y:,} cases (%{customdata[0]:.1%})<br>%{customdata[1]}<extra></extra>")
    if "repetition" in wanted:
        repeated = tables["repeated_activity_summary"].iloc[::-1]
        charts["repetition"] = px.bar(repeated, x="cases", y="concept:name", orientation="h", custom_data=["excess_occurrences"],
                                      color_discrete_sequence=[BLUE], labels={"cases": "Cases repeating this activity", "concept:name": ""})
        charts["repetition"].update_traces(hovertemplate="%{y}<br>Cases: %{x:,}<br>Excess occurrences: %{customdata[0]:,}<extra></extra>")
        charts["repetition"].update_layout(height=max(320, len(repeated) * 30 + 100))
    for fig in charts.values():
        fig.update_layout(template="plotly_white", font=dict(family="Arial, sans-serif", color="#25334a"),
                          margin=dict(l=10, r=15, t=25, b=35), paper_bgcolor="rgba(0,0,0,0)",
                          plot_bgcolor="rgba(0,0,0,0)", showlegend=False, dragmode="zoom")
    return charts


