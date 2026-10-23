"""Additional real Edge UAT for map visibility, comparisons and mobile navigation."""
import json
import time
from urllib.request import urlopen
from websockets.sync.client import connect
from verify_uat_browser import Browser,OUT


def main():
    page=next(p for p in json.load(urlopen('http://127.0.0.1:9224/json/list')) if p['url'].startswith('http://127.0.0.1:8504'))
    results={}
    with connect(page['webSocketDebuggerUrl'],max_size=30_000_000) as socket:
        b=Browser(socket)
        def number(label,value):
            b.wait("document.querySelector('input[aria-label="+json.dumps(label)+"]')?.disabled===false")
            b.js("document.querySelector('input[aria-label="+json.dumps(label)+"]').select()")
            b.command('Input.insertText',{'text':str(value)})
            b.key('Enter',13);b.key('Tab',9)
            time.sleep(.3)
            b.wait("document.querySelector('[data-testid=stApp]')?.getAttribute('data-test-script-state')==='notRunning'")
            b.chart()
        try:
            b.command('Page.enable');b.command('Runtime.enable')
            b.command('Emulation.setDeviceMetricsOverride',{'width':1440,'height':1100,'deviceScaleFactor':1,'mobile':False})
            b.command('Page.reload',{'ignoreCache':True})
            time.sleep(.5)
            b.wait("document.body?.innerText.includes('Time across the observed process') && document.querySelector('[data-testid=stApp]')?.getAttribute('data-test-script-state')==='notRunning'")
            b.nav('Process Mining');b.chart()
            b.click('[data-testid=stRadio] label','Main Process')
            number('Minimum transition frequency',100000)
            b.wait("document.body?.innerText.includes('No edges meet these display controls')")
            assert '45,937' in b.text()
            results['map_empty_visibility_keeps_data']=True
            number('Minimum transition frequency',1)
            number('Maximum displayed edges',3)
            b.wait('uatChart.getOption()?.series[0].links.length===3')
            results['map_edge_limit']=True
            b.js("document.querySelector('input[aria-label=\"Focus on activities (optional)\"]').focus()")
            b.command('Input.insertText',{'text':'Declaration SAVED by EMPLOYEE'})
            b.key('ArrowDown',40);b.key('Enter',13);b.key('Escape',27)
            b.chart()
            b.wait("uatChart.getOption()?.series[0].links.every(x=>x.raw_source==='Declaration SAVED by EMPLOYEE'||x.raw_target==='Declaration SAVED by EMPLOYEE')")
            results['map_activity_focus']=True
            b.click('[data-testid=stRadio] label','Detailed Process')
            b.chart()
            b.wait('uatChart.getOption()?.series[0].links.length===39')
            results['detailed_bypasses_display_filters']=True
            b.js("if(!document.querySelector('[data-testid=stCheckbox] input').checked)document.querySelector('[data-testid=stCheckbox] input').click()")
            b.wait("document.querySelector('[data-testid=stCheckbox] input')?.checked===true")
            time.sleep(.3)
            b.wait("document.querySelector('[data-testid=stApp]')?.getAttribute('data-test-script-state')==='notRunning'")
            b.chart()
            b.wait('uatChart.getOption()?.series[0].edgeLabel.show===true')
            b.js("document.querySelector('[data-testid=stEChartsChart]').scrollIntoView({block:'center'})")
            b.screenshot('graph_frequency_labels.png')
            results['edge_frequency_labels']=True
            b.click('[role=tab]','Variant performance')
            b.wait("document.querySelector('input[aria-label=\"Compare variant duration distributions\"]')!==null")
            b.js("Array.from(document.querySelectorAll('[data-testid=stMultiSelect]')).find(x=>x.innerText.includes('Compare variant duration distributions')).querySelector('[aria-label=\"Clear all\"]').click()")
            b.wait("document.body?.innerText.includes('Choose at least one variant for a duration comparison')")
            results['variant_comparison_empty_state']=True
            b.js("document.querySelector('input[aria-label=\"Compare variant duration distributions\"]').focus()")
            b.command('Input.insertText',{'text':'V0001'});b.key('ArrowDown',40);b.key('Enter',13);b.key('Escape',27)
            b.wait("!document.body?.innerText.includes('Choose at least one variant for a duration comparison')")
            results['variant_comparison_reselect']=True
            b.click('[role=tab]','Process map & transitions')
            b.command('Emulation.setDeviceMetricsOverride',{'width':390,'height':844,'deviceScaleFactor':1,'mobile':True})
            b.js("document.querySelector('[data-testid=stEChartsChart]').scrollIntoView({block:'center'})")
            b.screenshot('graph_mobile.png')
            b.js('window.scrollTo(0,0)')
            toggle="document.querySelector('[data-testid=stExpandSidebarButton]')"
            b.wait(toggle+'!==null');b.js(toggle+'.click()')
            b.nav('ML Preparation')
            b.wait("document.body?.innerText.includes('9,536')")
            results['mobile_sidebar_navigation']=True
            b.command('Emulation.setDeviceMetricsOverride',{'width':1440,'height':1100,'deviceScaleFactor':1,'mobile':False})
            b.nav('Case explorer')
            downloads=OUT/'control_downloads';downloads.mkdir(exist_ok=True)
            b.command('Browser.setDownloadBehavior',{'behavior':'allow','downloadPath':str(downloads.resolve())})
            b.wait("document.querySelector('[data-testid=stDownloadButton] button')!==null")
            b.click('[data-testid=stDownloadButton] button','Download selected case summary')
            deadline=time.monotonic()+30
            path=downloads/'smartbpm_selected_cases.csv'
            while not path.exists() and time.monotonic()<deadline:time.sleep(.2)
            import pandas as pd
            data=pd.read_csv(path)
            assert len(data)==10500 and data['case:concept:name'].is_unique and data.event_count.sum()==56437
            results['full_cohort_download_readback']={'rows':len(data),'events':int(data.event_count.sum())}
            b.nav('Overview')
            results['exceptions']=b.js("document.querySelectorAll('[data-testid=stException]').length")
            assert results['exceptions']==0
            results['passed']=True
        except Exception as exc:
            results['passed']=False;results['failure']=repr(exc)
            b.screenshot('controls_failure.png')
            raise
        finally:
            (OUT/'controls_verification.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
            print(json.dumps(results,indent=2))


if __name__=='__main__':main()
