"""Actual Edge interaction checks. Streamlit :8505, dedicated Edge CDP :9225."""
import json
from pathlib import Path
import time
from urllib.request import urlopen
from websockets.sync.client import connect
import verify_uat_browser as base

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'outputs/reports/browser_checks/day9_10'


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    base.OUT=OUT
    base.PAGES['Predictive Analytics']='HISTORICAL VALIDATION WORKBENCH'
    pages=json.load(urlopen('http://127.0.0.1:9225/json/list'))
    page=next((p for p in pages if p['url'].startswith('http://127.0.0.1:8505')),next(p for p in pages if p['type']=='page'))
    report=json.loads((ROOT/'outputs/models/day9_10/validation_report.json').read_text())
    example=json.loads((ROOT/'outputs/reports/day9_10_example_case.json').read_text())
    results={}
    with connect(page['webSocketDebuggerUrl'],max_size=30_000_000) as socket:
        b=base.Browser(socket)
        try:
            b.command('Page.enable');b.command('Runtime.enable');b.command('Log.enable')
            # Scope logs to this run, excluding buffered errors from prior server restarts.
            b.command('Log.clear');b.events.clear()
            b.command('Emulation.setDeviceMetricsOverride',{'width':1440,'height':1100,'deviceScaleFactor':1,'mobile':False})
            b.command('Page.navigate',{'url':'http://127.0.0.1:8505'})
            b.wait("document.body?.innerText.includes('Time across the observed process')")
            tick=time.perf_counter();b.nav('Predictive Analytics')
            b.wait("document.querySelector('input[aria-label=\"Choose a validation case\"]')!==null")
            results['first_predictive_navigation_seconds']=time.perf_counter()-tick
            results['overview_metrics']=b.js("Array.from(document.querySelectorAll('[data-testid=stMetric]')).map(x=>x.innerText)")
            assert '5,783' in results['overview_metrics'][0] and '1,752' in results['overview_metrics'][1]
            assert 'Logistic' in results['overview_metrics'][2]
            preferred=next(r for r in report['comparison'] if r['family']==report['preferred_model'])
            assert f"{preferred['average_precision']:.3f}" in results['overview_metrics'][3]
            assert 'test set is locked' in b.text().lower()
            b.screenshot('overview_comparison_desktop.png')
            b.select('Comparison metric','ROC-AUC')
            b.wait("Array.from(document.querySelectorAll('.js-plotly-plot')).some(x=>x._fullLayout?.yaxis?.title?.text==='ROC-AUC')")
            results['comparison_metric_control']=True
            b.click('[role=tab]','Validation evaluation')
            b.wait("document.body?.innerText.includes('Reliability curve')")
            b.screenshot('evaluation_desktop.png')
            results['evaluation_charts']=b.js("Array.from(document.querySelectorAll('.js-plotly-plot')).filter(x=>x.getBoundingClientRect().height>0).map(x=>x._fullLayout.title.text)")
            assert len(results['evaluation_charts'])==5
            # Verify actual confusion cells against the saved probability threshold.
            matrix=b.js("Array.from(document.querySelectorAll('.js-plotly-plot')).find(x=>x._fullData[0]?.type==='heatmap')._fullData[0].z.map(row=>Array.from(row))")
            assert matrix==preferred['confusion_matrix']
            results['confusion_matches_verified_metrics']=True
            b.click('[role=tab]','Case prediction explorer')
            b.wait("document.body?.innerText.includes('Predicted long-running risk')")
            text=b.text()
            assert f"{example['explanation']['probability']:.1%}" in text
            assert 'Incorrect classification' in text
            b.js("Array.from(document.querySelectorAll('h4')).find(x=>x.innerText.includes('Information recorded')).scrollIntoView({block:'start'})")
            b.screenshot('case_logistic_desktop.png')
            results['example_case']=example['case_id']
            results['example_probability']=example['explanation']['probability']
            cases=json.loads((ROOT/'outputs/models/day9_10/manifest.json').read_text())['validation_case_ids']
            b.select('Choose a validation case',cases[-1])
            b.wait("document.querySelector('input[aria-label=\"Choose a validation case\"]')?.value==="+json.dumps(cases[-1]))
            results['case_selection']=cases[-1]
            import pandas as pd
            prediction=pd.read_parquet(ROOT/'outputs/models/day9_10/validation_predictions.parquet').iloc[-1]
            display_to_family={r['model']:r['family'] for r in report['comparison']}
            for display in ['Constrained decision tree','Elapsed-time baseline','Training prevalence','Logistic regression']:
                b.select('Inspect model',display)
                expected=float(prediction[display_to_family[display]+'_probability'])
                b.wait('document.body?.innerText.includes('+json.dumps(f'{expected:.1%}')+')')
                b.wait("document.querySelector('[data-testid=stApp]')?.getAttribute('data-test-script-state')==='notRunning'")
                assert b.js("document.querySelectorAll('[data-testid=stException]').length")==0
                if display=='Constrained decision tree':
                    b.wait("document.body?.innerText.includes('training cases. Their positive share')")
                    b.screenshot('case_tree_desktop.png')
            results['all_four_models_selected']=True
            slider="Array.from(document.querySelectorAll('[data-testid=stSlider]')).find(x=>x.innerText.includes('Probability decision threshold')).querySelector('input[type=range]')"
            b.js(slider+'.focus()');b.key('End',35);b.key('Tab',9)
            b.wait("document.body?.innerText.includes('Current threshold: 0.99')")
            results['decision_threshold_control']=True
            b.click('[role=tab]','Research interpretation')
            b.wait("document.body?.innerText.includes('Feature associations')")
            b.screenshot('interpretation_desktop.png')
            b.command('Emulation.setDeviceMetricsOverride',{'width':390,'height':844,'deviceScaleFactor':1,'mobile':True})
            for tab in ['Model comparison','Validation evaluation','Case prediction explorer','Research interpretation']:
                b.click('[role=tab]',tab);time.sleep(.4)
                width=b.js('({viewport:innerWidth,document:document.documentElement.scrollWidth})')
                assert width=={'viewport':390,'document':390},(tab,width)
                results.setdefault('mobile_widths',{})[tab]=width
            b.click('[role=tab]','Case prediction explorer')
            b.js("Array.from(document.querySelectorAll('h4')).find(x=>x.innerText.includes('Information recorded')).scrollIntoView({block:'start'})")
            b.screenshot('case_mobile.png')
            b.js('window.scrollTo(0,0)');b.screenshot('overview_mobile.png')
            b.command('Emulation.setDeviceMetricsOverride',{'width':1440,'height':1100,'deviceScaleFactor':1,'mobile':False})
            # Existing application sections still render after using the new page.
            for name in base.PAGES:
                if name=='Predictive Analytics':continue
                b.nav(name)
                results.setdefault('existing_pages',{})[name]=True
            b.nav('Predictive Analytics')
            results['exceptions']=b.js("document.querySelectorAll('[data-testid=stException]').length")
            results['console_errors']=[e for e in b.events if e['method']=='Runtime.exceptionThrown' or (e['method']=='Log.entryAdded' and e['params']['entry'].get('level')=='error')]
            assert results['exceptions']==0
            assert not results['console_errors']
            results['passed']=True
        except Exception as exc:
            results['passed']=False;results['failure']=repr(exc)
            b.screenshot('failure.png')
            (OUT/'failure_dom.txt').write_text(b.text(),encoding='utf-8')
            raise
        finally:
            (OUT/'verification.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
            print(json.dumps(results,indent=2))


if __name__=='__main__':main()
