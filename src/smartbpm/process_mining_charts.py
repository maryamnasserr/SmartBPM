"""Interactive directed ECharts graph and Plotly duration distributions."""
from html import escape
import networkx as nx
import plotly.express as px
from smartbpm.process_map_data import activity_map_rows


def directed_positions(shown,names,starts=None,direction="TB"):
    """Acyclic ranking is only a layout aid; every displayed edge still renders."""
    layout=nx.DiGraph();layout.add_nodes_from(sorted(names))
    root=max((name for name in (starts or {}) if name in names),key=lambda name:starts[name],default=None)
    for edge in shown.sort_values(["frequency","source","target"],ascending=[False,True,True]).itertuples():
        if edge.source==edge.target or edge.target==root or nx.has_path(layout,edge.target,edge.source):
            continue
        layout.add_edge(edge.source,edge.target)
    positions={}
    for level,group in enumerate(nx.topological_generations(layout)):
        group=sorted(group)
        for i,name in enumerate(group):
            cross=(i-(len(group)-1)/2)*210;along=level*(115 if direction=="TB" else 245)
            positions[name]=(cross,along) if direction=="TB" else (along,cross*.60)
    # Keep the strongest forward route aligned; side routes occupy another lane.
    current=root
    primary=set()
    while current is not None and current not in primary:
        primary.add(current)
        candidates=shown.loc[shown.source.eq(current)&~shown.target.isin(primary)]
        candidates=candidates.loc[candidates.target.isin(layout.successors(current))]
        current=candidates.iloc[0].target if len(candidates) else None
    if primary:
        levels={}
        for name,(x,y) in positions.items():
            levels.setdefault(y if direction=="TB" else x,[]).append(name)
        for along,names_at_level in levels.items():
            others=sorted(name for name in names_at_level if name not in primary)
            offsets={name:0 for name in names_at_level if name in primary}
            for i,name in enumerate(others):
                offsets[name]=(-1 if i%2==0 else 1)*210*(i//2+1)
            for name,cross in offsets.items():
                positions[name]=(cross,along) if direction=="TB" else (along,cross*.60)
    return positions


def process_map(transitions,shown,activities,show_counts=False,*,selected_activity=None,direction="TB",starts=None,ends=None):
    """Return a JSON ECharts option and complete, unmodified activity inventory."""
    if direction not in ("TB","LR"):raise ValueError("Direction must be TB or LR")
    rows=activity_map_rows(activities,transitions,shown)
    if selected_activity is not None and selected_activity not in activities:raise ValueError("Unknown inspected activity")
    connected={row["activity"] for row in rows if not row["isolated_in_display"]}
    positions=directed_positions(shown,connected,starts,direction)
    lookup={row["activity"]:row for row in rows}
    if selected_activity is not None and selected_activity not in positions:
        last=max((p[1 if direction=="TB" else 0] for p in positions.values()),default=-115)
        positions[selected_activity]=(0,last+230) if direction=="TB" else (last+230,0)
    nodes=[]
    for name,(x,y) in positions.items():
        row=lookup[name];isolated=row["isolated_in_display"];selected=name==selected_activity
        boundary=("First / last observed" if name in (starts or {}) and name in (ends or {}) else "First observed" if name in (starts or {}) else "Last observed" if name in (ends or {}) else "")
        label=row["label"]+("\nNo visible edges" if isolated else "")
        nodes.append({"id":row["node"],"name":label,"raw_activity":name,"boundary":boundary,"x":x,"y":y,"value":row["event_count"],
                      "itemStyle":{"color":"#fff2d6" if isolated else "#cfeef4" if selected else "#e6f3eb" if name in (ends or {}) else "#eaf0fb" if name in (starts or {}) else "#f0f8f8",
                                   "borderColor":"#9c6b14" if isolated else "#087f8c","borderWidth":3 if selected else 1.5,
                                   "borderType":"dashed" if isolated else "solid"},
                      "tooltip":{"formatter":escape(name)+"<br>"+boundary+f"<br>{row['node']} | {row['event_count']:,} occurrences<br>"+escape(row["isolation_reason"])}})
    layers={}
    for x,y in positions.values():
        coordinate=y if direction=="TB" else x
        layers[coordinate]=layers.get(coordinate,0)+1
    parallel=max(layers.values(),default=1)
    initial_zoom=max(1,(parallel+1)/4) if direction=="TB" else (1.18 if len(shown)>20 else 1)
    mobile_zoom=max(1,(parallel+1)/2)
    largest=max([1]+shown.frequency.tolist());links=[]
    for row in shown.itertuples():
        first,second=positions[row.source],positions[row.target]
        back=second[1 if direction=="TB" else 0]<=first[1 if direction=="TB" else 0]
        along_gap=abs(second[1 if direction=="TB" else 0]-first[1 if direction=="TB" else 0])
        bend=.35 if back else min(.9,210/along_gap) if along_gap>(150 if direction=="TB" else 365) and first[0 if direction=="TB" else 1]==second[0 if direction=="TB" else 1] else 0.04
        tooltip=escape(row.source)+" -> "+escape(row.target)+f"<br>{row.frequency:,} consecutive transitions | {row.case_count:,} cases<br>Median elapsed gap: {row.median_hours:.2f} h"
        links.append({"source":lookup[row.source]["node"],"target":lookup[row.target]["node"],
                      "raw_source":row.source,"raw_target":row.target,"value":int(row.frequency),
                      "lineStyle":{"color":"#718496","width":1+3*row.frequency/largest,"curveness":bend,"opacity":.9},
                      "tooltip":{"formatter":tooltip}})
    return {"animation":False,"tooltip":{"trigger":"item","confine":True},
            "toolbox":{"left":8,"top":4,"feature":{"restore":{"title":"Reset graph view"}}},
            "series":[{"id":"observed-process","type":"graph","layout":"none","roam":True,
                       "zoom":initial_zoom,"scaleLimit":{"min":.25,"max":8},"nodeScaleRatio":.05,"symbol":"roundRect","symbolSize":[164,56] if direction=="TB" else [136 if len(shown)<=20 else 112,58],"preserveAspect":True,"roamTrigger":"global",
                       "left":"9%","right":"9%","top":55,"bottom":55,"data":nodes,"links":links,
                       "label":{"show":True,"position":"inside","color":"#173744","fontSize":12 if direction=="TB" else 11,"lineHeight":17},
                       "edgeSymbol":["none","arrow"],"edgeSymbolSize":[0,10],
                       "edgeLabel":{"show":show_counts,"formatter":"{c}","fontSize":11,"color":"#253f50","backgroundColor":"#ffffff"},
                       "emphasis":{"focus":"none","lineStyle":{"width":4}}}],
            "media":[{"query":{"maxWidth":600},"option":{"series":[{"id":"observed-process","symbolSize":[120,54],"zoom":mobile_zoom,"data":[dict(n,x=n["y"],y=n["x"]) for n in nodes] if direction=="LR" else nodes,"label":{"fontSize":10,"lineHeight":14}}]}}]},rows


def duration_comparison(cases,group):
    figure=px.box(cases,x=group,y="elapsed_days",points=False,color_discrete_sequence=["#087f8c"],labels={group:"Case group","elapsed_days":"Observed elapsed days"})
    figure.update_layout(template="plotly_white",height=430,margin=dict(l=20,r=20,t=20,b=60),showlegend=False)
    return figure
