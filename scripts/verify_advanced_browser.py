"""Real Edge verification of advanced ML, grouped XAI and evidence download.

Start Streamlit on 8506 and the dedicated hidden Edge CDP endpoint on 9226.
"""
import json
from pathlib import Path
import time
from urllib.request import urlopen
import pandas as pd
from websockets.sync.client import connect
import verify_uat_browser as base

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'outputs/reports/browser_checks/day11_12'


def main():
    OUT.mkdir(parents=True,exist_ok=True);base.OUT=OUT
    base.PAGES['Predictive Analytics']='HISTORICAL VALIDATION WORKBENCH'
    pages=json.load(urlopen('http://127.0.0.1:9226/json/list'))
    page=next((p for p in pages if p['url'].startswith('http://127.0.0.1:8506')),next(p for p in pages if p['type']=='page'))
    directory=ROOT/'outputs/models/day11_12'
    report=json.loads((directory/'validation_report.json').read_text())
    manifest=json.loads((directory/'manifest.json').read_text())
    predictions=pd.read_parquet(directory/'validation_predictions.parquet')
    family=report['preferred_model'];selected=next(r for r in report['comparison'] if r['family']==family)
    results={}
    with connect(page['webSocketDebuggerUrl'],max_size=30_000_000) as socket:
        b=base.Browser(socket)
        try:
            b.command('Page.enable');b.command('Runtime.enable');b.command('Log.enable');b.command('Log.clear');b.events.clear()
            b.command('Emulation.setDeviceMetricsOverride',{'width':1440,'height':1100,'deviceScaleFactor':1,'mobile':False})
            b.command('Page.navigate',{'url':'http://127.0.0.1:8506'})
            b.wait("document.body?.innerText.includes('Time across the observed process')")
            started=time.perf_counter();b.nav('Predictive Analytics')
            b.wait("document.body?.innerText.includes('Explainable AI') && document.querySelector('input[aria-label=\"Choose a validation case\"]')!==null")
            results['first_navigation_seconds']=time.perf_counter()-started
            metrics=b.js("Array.from(document.querySelectorAll('[data-testid=stMetric]')).map(x=>x.innerText)")
            assert '5,783' in metrics[0] and '1,752' in metrics[1]
            assert f"{selected['average_precision']:.3f}" in metrics[3]
            results['overview_metrics']=metrics[:4]
            b.screenshot('overview_desktop.png')
            b.select('Comparison metric','Average precision (PR-AUC)')
            plot=b.js("Array.from(document.querySelectorAll('.js-plotly-plot')).find(p=>p._fullData.length===6)._fullData.map(t=>({name:t.name,value:t.x[0]}))")
            assert {p['name']:p['value'] for p in plot}=={r['model']:r['average_precision'] for r in report['comparison']}
            results['all_six_comparison_probabilities_verified']=True
            b.select('Comparison threshold policy','Validation-F1 thresholds')
            b.wait("document.querySelector('input[aria-label=\"Comparison threshold policy\"]')?.value==='Validation-F1 thresholds'")
            b.select('Comparison threshold policy','Common 0.50')
            b.click('[role=tab]','Validation evaluation')
            b.wait("document.body?.innerText.includes('Reliability curve')")
            results['evaluation_charts']=b.js("Array.from(document.querySelectorAll('.js-plotly-plot')).filter(p=>p.getBoundingClientRect().height>0).map(p=>p._fullLayout.title.text)")
            assert len(results['evaluation_charts'])==5
            b.screenshot('evaluation_desktop.png')
            b.click('[role=tab]','Case prediction explorer')
            b.wait("document.body?.innerText.includes('Information recorded at Event 2')")
            for row in report['comparison']:
                b.select('Inspect model',row['model'])
                probability=predictions.iloc[0][row['family']+'_probability']
                b.wait('document.body?.innerText.includes('+json.dumps(f'{probability:.1%}')+')')
                b.wait("document.querySelector('[data-testid=stApp]')?.getAttribute('data-test-script-state')==='notRunning'")
                assert b.js("document.querySelectorAll('[data-testid=stException]').length")==0
            results['all_six_models_selected']=True
            b.select('Inspect model',selected['model'])
            selected_risk=float(predictions.iloc[0][family+'_probability'])
            b.wait('document.body?.innerText.includes('+json.dumps(f'{selected_risk:.1%}')+')')
            b.click('[role=tab]','Decision threshold explorer')
            b.wait("document.body?.innerText.includes('Precision at current threshold')")
            slider="Array.from(document.querySelectorAll('[data-testid=stSlider]')).find(x=>x.innerText.includes('Probability decision threshold')).querySelector('input[type=range]')"
            b.wait("document.querySelector('[data-testid=stApp]')?.getAttribute('data-test-script-state')==='notRunning'")
            b.js(slider+".closest('[data-testid=stSlider]').scrollIntoView({block:'center'})")
            # Use a real pointer click on the track. Keyboard focus can be
            # replaced by Streamlit's pending model-selection rerender.
            track=b.js(slider+".closest('[data-orientation=horizontal]').getBoundingClientRect().toJSON()")
            for event in ['mousePressed','mouseReleased']:
                b.command('Input.dispatchMouseEvent',{'type':event,'x':track['right']-1,
                    'y':track['top']+track['height']/2,'button':'left','clickCount':1})
            b.wait("document.body?.innerText.includes('Current threshold: 0.99')")
            results['threshold_explorer']=True
            b.screenshot('threshold_desktop.png')
            b.click('[role=tab]','Explainable AI')
            b.wait("document.body?.innerText.includes('Global explanations')")
            b.wait("document.querySelector('[data-testid=stApp]')?.getAttribute('data-test-script-state')==='notRunning'")
            b.screenshot('global_xai_desktop.png')
            b.click('[data-testid=stRadio] label','Local explanations')
            b.wait("document.body?.innerText.includes('Training-background mean risk')")
            b.select('Explain a validation declaration',predictions.iloc[-1]['case:concept:name'])
            expected=float(predictions.iloc[-1][family+'_probability'])
            b.wait('document.body?.innerText.includes('+json.dumps(f'{expected:.1%}')+')')
            b.screenshot('local_xai_desktop.png')
            results['local_case_id']=predictions.iloc[-1]['case:concept:name']
            results['local_probability']=expected
            b.click('[data-testid=stRadio] label','Analytical evidence')
            b.wait("document.querySelector('[data-testid=stDownloadButton] button')!==null")
            downloads=OUT/'downloads';downloads.mkdir(exist_ok=True)
            path=downloads/'smartbpm_analytical_evidence.json'
            path.unlink(missing_ok=True)
            b.command('Browser.setDownloadBehavior',{'behavior':'allow','downloadPath':str(downloads.resolve())})
            b.click('[data-testid=stDownloadButton] button','Download analytical evidence JSON')
            deadline=time.monotonic()+30
            while not path.exists() and time.monotonic()<deadline:time.sleep(.2)
            evidence=json.loads(path.read_text())
            assert evidence['facts']['model']['selected_model_sha256']==manifest['file_sha256']['selected_model.joblib']
            assert evidence['facts']['case']['case_id_display_only']==results['local_case_id']
            assert evidence['facts']['case']['predicted_probability']==expected
            assert evidence['provenance']['test_evaluated'] is False
            results['evidence_download_verified']=True
            b.screenshot('evidence_desktop.png')
            b.click('[data-testid=stRadio] label','Global explanations')
            b.command('Emulation.setDeviceMetricsOverride',{'width':390,'height':844,'deviceScaleFactor':1,'mobile':True})
            for tab in ['Model comparison','Validation evaluation','Case prediction explorer','Decision threshold explorer','Explainable AI','Research interpretation']:
                b.click('[role=tab]',tab);time.sleep(.4)
                width=b.js('({viewport:innerWidth,document:document.documentElement.scrollWidth})')
                assert width=={'viewport':390,'document':390},(tab,width)
                results.setdefault('mobile_widths',{})[tab]=width
            b.click('[role=tab]','Explainable AI');b.js('window.scrollTo(0,0)');b.screenshot('overview_mobile.png')
            b.js("Array.from(document.querySelectorAll('h4')).find(x=>x.innerText.includes('Explainable AI')).scrollIntoView({block:'start'})")
            b.screenshot('global_xai_mobile.png')
            b.command('Emulation.setDeviceMetricsOverride',{'width':1440,'height':1100,'deviceScaleFactor':1,'mobile':False})
            for name in base.PAGES:
                if name=='Predictive Analytics':continue
                b.nav(name);results.setdefault('existing_pages',{})[name]=True
            b.nav('Predictive Analytics')
            results['exceptions']=b.js("document.querySelectorAll('[data-testid=stException]').length")
            results['console_errors']=[e for e in b.events if e['method']=='Runtime.exceptionThrown' or (e['method']=='Log.entryAdded' and e['params']['entry'].get('level')=='error')]
            assert not results['console_errors'] and results['exceptions']==0
            results['passed']=True
        except Exception as exc:
            results['passed']=False;results['failure']=repr(exc)
            b.screenshot('failure.png');(OUT/'failure_dom.txt').write_text(b.text(),encoding='utf-8')
            raise
        finally:
            (OUT/'verification.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
            print(json.dumps(results,indent=2))


if __name__=='__main__':main()
