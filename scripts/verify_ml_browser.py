"""Real Edge DOM smoke checks; start Streamlit :8503 and Edge CDP :9223."""
import base64
import json
from pathlib import Path
import time
from urllib.request import urlopen
from websockets.sync.client import connect

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'outputs/reports/browser_checks/day7_8'


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    pages=json.load(urlopen('http://127.0.0.1:9223/json/list'))
    page=next(p for p in pages if p['type']=='page')
    results={}
    with connect(page['webSocketDebuggerUrl'],max_size=20_000_000) as socket:
        ident=0
        def command(method,params=None):
            nonlocal ident
            ident+=1
            socket.send(json.dumps({'id':ident,'method':method,'params':params or {}}))
            while True:
                message=json.loads(socket.recv(timeout=30))
                if message.get('id')==ident:
                    if 'error' in message:raise RuntimeError(message['error'])
                    return message.get('result',{})
        def js(expression):
            result=command('Runtime.evaluate',{'expression':expression,'returnByValue':True})
            if 'exceptionDetails' in result:raise RuntimeError(result['exceptionDetails'])
            return result.get('result',{}).get('value')
        def wait(expression):
            deadline=time.monotonic()+55
            while time.monotonic()<deadline:
                if js(expression):return
                time.sleep(.3)
            raise AssertionError(expression)
        def navigate(label,expression):
            js("Array.from(document.querySelectorAll('[data-testid=stRadio] label')).find(x=>x.innerText==="+json.dumps(label)+").click()")
            wait(expression)
            assert js("document.querySelectorAll('[data-testid=stException]').length")==0
        command('Page.enable')
        command('Emulation.setDeviceMetricsOverride',{'width':1440,'height':1100,'deviceScaleFactor':1,'mobile':False})
        command('Page.navigate',{'url':'http://127.0.0.1:8503'})
        wait("document.querySelectorAll('.js-plotly-plot').length===2")
        results['overview_plotly_charts']=js("document.querySelectorAll('.js-plotly-plot').length")
        tick=time.perf_counter()
        navigate('ML Preparation',"document.body.innerText.includes('Unresolved eligible cases') && document.body.innerText.includes('9,536')")
        results['ml_navigation_seconds']=time.perf_counter()-tick
        results['ml_text']=js('document.body.innerText')
        assert 'historical labels and preparation statistics, not predictions' in results['ml_text']
        assert '11.105428240741' in results['ml_text']
        assert '333' in results['ml_text']
        results['ml_metrics']=js("Array.from(document.querySelectorAll('[data-testid=stMetric]')).map(x=>x.innerText)")
        results['ml_tables']=js("document.querySelectorAll('[data-testid=stDataFrame]').length")
        assert results['ml_tables']==3
        shot=command('Page.captureScreenshot',{'format':'png'})
        (OUT/'ml_desktop.png').write_bytes(base64.b64decode(shot['data']))
        command('Emulation.setDeviceMetricsOverride',{'width':390,'height':844,'deviceScaleFactor':1,'mobile':True})
        time.sleep(.8)
        results['mobile_width']=js('({viewport:innerWidth,document:document.documentElement.scrollWidth})')
        assert results['mobile_width']=={'viewport':390,'document':390}
        shot=command('Page.captureScreenshot',{'format':'png'})
        (OUT/'ml_mobile.png').write_bytes(base64.b64decode(shot['data']))
        command('Emulation.setDeviceMetricsOverride',{'width':1440,'height':1100,'deviceScaleFactor':1,'mobile':False})
        navigate('Process Mining',"document.querySelector('[data-testid=stEChartsChart] svg')!==null")
        results['process_mining_svg']=True
        navigate('Performance Investigation',"document.body.innerText.includes('Mean observed days')")
        results['performance_page']=True
        navigate('Activities & resources',"document.querySelectorAll('.js-plotly-plot').length===2 && document.body.innerText.includes('What happens, and who is recorded?')")
        results['activities_page']=True
        navigate('Variants & repetition',"document.body.innerText.includes('Paths and repeated work') && document.querySelectorAll('.js-plotly-plot').length===2")
        results['variants_page']=True
        navigate('Case boundaries',"document.body.innerText.includes('First and last observed activities') && document.querySelectorAll('.js-plotly-plot').length===2")
        results['boundaries_page']=True
        navigate('Case explorer',"document.body.innerText.includes('Inspect the evidence')")
        results['case_explorer_page']=True
        navigate('ML Preparation',"document.body.innerText.includes('Unresolved eligible cases')")
        results['rendered_exceptions']=js("document.querySelectorAll('[data-testid=stException]').length")
    (OUT/'verification.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in results.items() if k!='ml_text'},indent=2))


if __name__=='__main__':main()
