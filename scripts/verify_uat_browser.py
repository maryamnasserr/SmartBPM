"""Repeatable real-browser UAT. Local Streamlit :8504; hidden Edge CDP :9224."""
import base64
import json
from pathlib import Path
import time
from urllib.request import urlopen
from websockets.sync.client import connect

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'outputs/reports/browser_checks/uat'
PAGES={'Overview':'Time across the observed process','Activities & resources':'What happens, and who is recorded?',
       'Variants & repetition':'Paths and repeated work','Case boundaries':'First and last observed activities',
       'Case explorer':'Inspect the evidence','Process Mining':'Process Intelligence Workspace',
       'Performance Investigation':'Mean observed days','ML Preparation':'Unresolved eligible cases'}


class Browser:
    def __init__(self,socket):self.socket=socket;self.ident=0;self.events=[]
    def command(self,method,params=None):
        self.ident+=1
        self.socket.send(json.dumps({'id':self.ident,'method':method,'params':params or {}}))
        while True:
            message=json.loads(self.socket.recv(timeout=45))
            if message.get('id')==self.ident:
                if 'error' in message:raise RuntimeError(message['error'])
                return message.get('result',{})
            if 'method' in message:self.events.append(message)
    def js(self,expression):
        result=self.command('Runtime.evaluate',{'expression':expression,'returnByValue':True})
        if 'exceptionDetails' in result:raise RuntimeError(result['exceptionDetails'])
        return result.get('result',{}).get('value')
    def wait(self,expression,seconds=55):
        deadline=time.monotonic()+seconds
        while time.monotonic()<deadline:
            try:
                if self.js(expression):return
            except RuntimeError as exc:
                # Navigation can briefly destroy the JS context. Retry that CDP
                # condition only; genuine JS errors must still fail the check.
                if not any(message in str(exc) for message in ['Inspected target navigated','Cannot find context','Execution context was destroyed']):
                    raise
            time.sleep(.25)
        raise AssertionError(expression)
    def text(self):return self.js('document.body.innerText')
    def click(self,selector,text):
        self.js('Array.from(document.querySelectorAll('+json.dumps(selector)+')).find(x=>x.innerText.trim()==='+json.dumps(text)+').click()')
    def nav(self,name):
        self.click('[data-testid=stRadio] label',name)
        self.wait('document.body.innerText.includes('+json.dumps(PAGES[name])+')')
        self.wait("document.querySelector('[data-testid=stApp]')?.getAttribute('data-test-script-state')==='notRunning'")
        assert self.js("document.querySelectorAll('[data-testid=stException]').length")==0
    def key(self,key,code):
        for kind in ['keyDown','keyUp']:self.command('Input.dispatchKeyEvent',{'type':kind,'key':key,'windowsVirtualKeyCode':code})
    def select(self,label,value):
        selector="Array.from(document.querySelectorAll('[data-testid=stSelectbox]')).find(x=>x.innerText.includes("+json.dumps(label)+"))"
        self.wait('!!('+selector+")?.querySelector('input')")
        self.js(selector+".querySelector('input').focus()")
        self.command('Input.insertText',{'text':value})
        self.key('ArrowDown',40);self.key('Enter',13)
        self.wait("document.querySelector('[data-testid=stApp]')?.getAttribute('data-test-script-state')==='notRunning'")
    def screenshot(self,name):
        result=self.command('Page.captureScreenshot',{'format':'png'})
        (OUT/name).write_bytes(base64.b64decode(result['data']))
    def chart(self):
        self.wait("document.querySelector('[data-testid=stEChartsChart] svg')!==null")
        self.wait("(()=>{let e=document.querySelector('[data-testid=stEChartsChart]');for(let n=e;n;n=n.parentElement){let k=Object.keys(n).find(k=>k.startsWith('__reactFiber'));if(!k)continue;for(let f=n[k];f;f=f.return){for(let h=f.memoizedState;h;h=h.next){let c=h.memoizedState?.current;if(c&&typeof c.getOption==='function'&&c.getOption()?.series){window.uatChart=c;return true}}}}return false})()")


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    downloads=OUT/'downloads';downloads.mkdir(exist_ok=True)
    pages=json.load(urlopen('http://127.0.0.1:9224/json/list'))
    page=next((p for p in pages if p['url'].startswith('http://127.0.0.1:8504')),next(p for p in pages if p['type']=='page'))
    results={'pages':{},'interactions':{},'downloads':[]}
    with connect(page['webSocketDebuggerUrl'],max_size=30_000_000) as socket:
        b=Browser(socket)
        try:
            b.command('Page.enable');b.command('Runtime.enable');b.command('Log.enable')
            b.command('Browser.setDownloadBehavior',{'behavior':'allow','downloadPath':str(downloads.resolve()),'eventsEnabled':True})
            b.command('Emulation.setDeviceMetricsOverride',{'width':1440,'height':1100,'deviceScaleFactor':1,'mobile':False})
            b.command('Page.navigate',{'url':'http://127.0.0.1:8504'})
            b.wait("document.querySelectorAll('.js-plotly-plot').length===2")
            reference=json.loads((ROOT/'outputs/reports/uat_data_audit.json').read_text())
            def download_visible():
                buttons=b.js("Array.from(document.querySelectorAll('[data-testid=stDownloadButton] button')).filter(e=>e.getBoundingClientRect().height>0).map(x=>x.innerText)")
                for label in buttons:
                    b.click('[data-testid=stDownloadButton] button',label)
                    b.wait('true');time.sleep(.4)
                    results['downloads'].append(label)
            for name in PAGES:
                b.nav(name)
                metrics=b.js("Array.from(document.querySelectorAll('[data-testid=stMetric]')).map(x=>x.innerText)")
                results['pages'][name]={'metrics':metrics,'exceptions':b.js("document.querySelectorAll('[data-testid=stException]').length"),
                                        'plotly_charts':b.js("document.querySelectorAll('.js-plotly-plot').length")}
                b.screenshot(name.lower().replace(' ','_').replace('&','and')+'_desktop.png')
                if name=='Overview':
                    assert '10,500' in metrics[0] and '56,437' in metrics[1] and '17' in metrics[2]
                    assert b.js("document.querySelector('.js-plotly-plot')._fullData[0].x.length")==reference['cases']
                    b.js("window.uatPlot=document.querySelector('.js-plotly-plot');Plotly.relayout(uatPlot,{'xaxis.range':[0,30]})")
                    b.wait('uatPlot.layout.xaxis.range[1]===30')
                    b.js("Plotly.relayout(uatPlot,{'xaxis.autorange':true})")
                    results['interactions']['plotly_zoom_reset']=True
                if name=='Activities & resources':
                    actual=b.js("Array.from(document.querySelectorAll('.js-plotly-plot')).map(p=>Object.fromEntries(Array.from(p._fullData[0].y).map((v,i)=>[v,p._fullData[0].x[i]])))")
                    assert actual==[reference['activity_frequency'],reference['resource_frequency']]
                    results['interactions']['chart_frequencies_match_raw_records']=True
                if name=='Variants & repetition':assert any('99' in x for x in metrics) and any('1,019' in x for x in metrics)
                if name=='Case explorer':
                    b.select('Inspect a case',reference['walkthrough']['case_id'])
                    b.wait("document.querySelector('input[aria-label=\"Inspect a case\"]')?.value==="+json.dumps(reference['walkthrough']['case_id']))
                    results['interactions']['case_selected']=reference['walkthrough']['case_id']
                    b.wait("document.querySelector('[data-testid=stDownloadButton] button')!==null")
                if name=='Process Mining':
                    b.chart();b.wait('uatChart.getOption().series[0].links.length===7')
                    previous=b.js('uatChart.getOption().series[0].zoom')
                    b.js("document.querySelector('[data-testid=stEChartsChart]').scrollIntoView({block:'center'})")
                    bounds=b.js("(()=>{let r=document.querySelector('[data-testid=stEChartsChart]').getBoundingClientRect();return {x:r.x+r.width/2,y:r.y+r.height/2}})()")
                    b.command('Input.dispatchMouseEvent',{'type':'mouseWheel',**bounds,'deltaY':-160,'deltaX':0})
                    b.wait('uatChart.getOption().series[0].zoom!=='+json.dumps(previous))
                    center=b.js('JSON.stringify(uatChart.getOption().series[0].center)')
                    b.command('Input.dispatchMouseEvent',{'type':'mousePressed',**bounds,'button':'left','clickCount':1})
                    b.command('Input.dispatchMouseEvent',{'type':'mouseMoved','x':bounds['x']+40,'y':bounds['y']+20,'buttons':1})
                    b.command('Input.dispatchMouseEvent',{'type':'mouseReleased','x':bounds['x']+40,'y':bounds['y']+20,'button':'left','clickCount':1})
                    b.wait('JSON.stringify(uatChart.getOption().series[0].center)!=='+json.dumps(center))
                    results['interactions']['graph_wheel_zoom_and_drag_pan']=True
                    b.click('[data-testid=stRadio] label','Detailed Process');b.wait('uatChart.getOption().series[0].links.length===39')
                    links=b.js('uatChart.getOption().series[0].links.map(x=>({source:x.raw_source,target:x.raw_target,frequency:x.value}))')
                    import pandas as pd
                    expected=pd.read_csv(ROOT/'outputs/reports/day5_transitions.csv')
                    assert {(r['source'],r['target']):r['frequency'] for r in links}=={(r.source,r.target):r.frequency for r in expected.itertuples()}
                    assert sum(r['frequency'] for r in links)==reference['transition_occurrences']
                    results['interactions']['detailed_graph_exact_39_counts']=True
                    b.select('Inspect an activity','Declaration SAVED by EMPLOYEE')
                    b.wait("Array.from(document.querySelectorAll('[data-testid=stMetric]')).some(x=>x.innerText.includes('Activity occurrences')&&x.innerText.includes('135'))")
                    b.screenshot('detailed_graph_desktop.png')
                    b.select('Reading direction','Top to bottom')
                    results['interactions']['map_activity_and_direction']=True
                    download_visible()
                    for tab,heading in [('Variant performance','Paths and observed case duration'),('Repetition & duration','Repetition and elapsed-duration associations')]:
                        b.click('[role=tab]',tab);b.wait('document.body.innerText.includes('+json.dumps(heading)+')');download_visible()
                    b.click('[role=tab]','Variant performance')
                    b.select('Inspect a variant','V0002')
                    results['interactions']['variant_selection']=True
                elif name=='Performance Investigation':
                    for tab in ['Longer cases','Repeated activities','Alternative paths','ML research design']:
                        b.click('[role=tab]',tab);time.sleep(.3);download_visible()
                    assert str(reference['threshold_days']) in b.text()
                    results['interactions']['performance_all_tabs']=True
                else:download_visible()
                b.command('Emulation.setDeviceMetricsOverride',{'width':390,'height':844,'deviceScaleFactor':1,'mobile':True})
                b.js('window.scrollTo(0,0)');time.sleep(.5)
                width=b.js('({viewport:innerWidth,document:document.documentElement.scrollWidth})')
                results['pages'][name]['mobile_width']=width
                assert width=={'viewport':390,'document':390},(name,width)
                b.screenshot(name.lower().replace(' ','_').replace('&','and')+'_mobile.png')
                b.command('Emulation.setDeviceMetricsOverride',{'width':1440,'height':1100,'deviceScaleFactor':1,'mobile':False})
            # Actual widget interactions: deterministic single-case activity filter.
            b.nav('Overview')
            b.js("Array.from(document.querySelectorAll('[data-testid=stExpander] summary')).find(x=>x.innerText.includes('Activity selection')).click()")
            (OUT/'widget_dom.json').write_text(json.dumps(b.js("Array.from(document.querySelectorAll('[data-testid=stMultiSelect]')).map(x=>({text:x.innerText,html:x.innerHTML}))"),indent=2),encoding='utf-8')
            # BaseWeb's clear-all button leaves an empty selection; the input permits replacement.
            b.js("document.querySelector('[data-testid=stMultiSelect] [aria-label=\"Clear all\"]').click()")
            b.wait("document.body.innerText.includes('No cases match these filters')")
            results['interactions']['activity_empty_state']=True
            b.js("document.querySelector('[data-testid=stMultiSelect] input').focus()")
            b.command('Input.insertText',{'text':'Declaration FOR_APPROVAL by ADMINISTRATION'})
            b.key('ArrowDown',40);b.key('Enter',13);b.key('Escape',27)
            b.wait("Array.from(document.querySelectorAll('[data-testid=stMetric]'))[0]?.innerText.includes('Selected cases\\n\\n1')")
            b.nav('Case explorer');download_visible()
            results['interactions']['whole_case_filter']=b.js("Array.from(document.querySelectorAll('[data-testid=stMetric]')).slice(0,4).map(x=>x.innerText)")
            b.click('button','Reset filters')
            b.wait("Array.from(document.querySelectorAll('[data-testid=stMetric]'))[0]?.innerText.includes('10,500')")
            results['interactions']['reset_all_cases']=True
            b.command('Page.reload',{'ignoreCache':True})
            b.wait("document.body?.innerText.includes('Selected cases') && document.querySelectorAll('.js-plotly-plot').length===2")
            results['interactions']['browser_refresh']=True
            # Resource empty-state, global research independence, and reset.
            b.js("Array.from(document.querySelectorAll('[data-testid=stMultiSelect]')).find(x=>x.innerText.includes('Cases involving any resource')).querySelector('[aria-label=\"Clear all\"]').click()")
            b.wait("document.body?.innerText.includes('No cases match these filters')")
            b.nav('ML Preparation')
            assert '9,536' in b.text()
            results['interactions']['ml_frozen_with_empty_cohort']=True
            b.click('button','Reset filters')
            b.wait("Array.from(document.querySelectorAll('[data-testid=stMultiSelect]')).find(x=>x.innerText.includes('Cases involving any resource'))?.innerText.includes('SYSTEM')")
            b.nav('Overview')
            # Keyboard change to a real range-slider thumb, then restore.
            b.js("document.querySelector('[data-testid=stSlider] input[type=range]').focus()")
            b.key('ArrowRight',39);b.key('Tab',9)
            b.wait("Array.from(document.querySelectorAll('[data-testid=stMetric]'))[0]?.innerText.includes('10,500')===false")
            results['interactions']['duration_slider']=True
            b.click('button','Reset filters')
            b.wait("Array.from(document.querySelectorAll('[data-testid=stMetric]'))[0]?.innerText.includes('10,500')")
            # Select a complete one-day range through the actual calendar popup.
            b.js("document.querySelector('[data-testid=stDateInputCalendarButton]').click()")
            calendar_day="Array.from(document.querySelectorAll('[role=button][aria-label]')).find(x=>x.getAttribute('aria-label').includes('Wednesday, 11 January 2017'))"
            b.wait(calendar_day+'!==undefined');b.js(calendar_day+'.click()')
            time.sleep(.3);b.js(calendar_day+'.click()')
            b.wait("document.body?.innerText.includes('starts 2017-01-11 to 2017-01-11')")
            b.wait("Array.from(document.querySelectorAll('[data-testid=stMetric]'))[0]?.innerText==='Selected cases\\n\\n2'")
            results['interactions']['date_range_calendar']=True
            b.click('button','Reset filters')
            b.wait("Array.from(document.querySelectorAll('[data-testid=stMetric]'))[0]?.innerText.includes('10,500')")
            results['browser_console_errors']=[x for x in b.events if x['method']=='Runtime.exceptionThrown' or (x['method']=='Log.entryAdded' and x['params']['entry'].get('level')=='error')]
            results['download_events']=[x for x in b.events if x['method'].startswith('Browser.download')]
            results['download_files']=[{'name':p.name,'bytes':p.stat().st_size} for p in downloads.glob('*.csv')]
            results['download_content_checks']=verify_downloads(downloads,reference)
            results['passed']=True
        except Exception as exc:
            results['passed']=False;results['failure']=repr(exc)
            b.screenshot('failure.png')
            (OUT/'failure_dom.txt').write_text(b.text(),encoding='utf-8')
            raise
        finally:
            (OUT/'verification.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
            print(json.dumps({k:v for k,v in results.items() if k not in ['download_events']},indent=2))


def verify_downloads(directory,reference):
    import pandas as pd
    checked=[]
    for path in directory.glob('*.csv'):
        data=pd.read_csv(path)
        name=path.name
        if name.startswith('smartbpm_selected_cases'):
            assert len(data) in [reference['cases'],1]
            if len(data)==1:
                assert data.iloc[0]['case:concept:name']==reference['walkthrough']['case_id']
                assert data.iloc[0].event_count==reference['walkthrough']['events']
                assert abs(data.iloc[0].elapsed_days-reference['walkthrough']['elapsed_days'])<1e-10
        elif name.startswith(('smartbpm_all_transitions','smartbpm_displayed_transitions')):
            assert len(data)==reference['relationships'] and data.frequency.sum()==reference['transition_occurrences']
            assert not data[['source','target']].duplicated().any()
        elif name.startswith(('smartbpm_variant_performance','smartbpm_investigated_variants')):
            assert len(data)==reference['variants'] and data.case_count.sum()==reference['cases']
        elif name.startswith('smartbpm_case_repetition_flags'):
            assert len(data)==reference['cases'] and data['case:concept:name'].is_unique
        elif name.startswith('smartbpm_candidate_targets'):assert len(data)==3
        elif name.startswith('smartbpm_repetition_groups'):assert not data.empty
        else:raise AssertionError('Unexpected CSV '+name)
        checked.append({'file':name,'rows':len(data),'passed':True})
    assert checked
    return checked


if __name__=='__main__':main()
