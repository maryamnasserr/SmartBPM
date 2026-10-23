"""Actual Edge verification of directed SVG layout, counts and activity controls."""
import base64,json,time
from pathlib import Path
from urllib.request import urlopen
from websockets.sync.client import connect
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'outputs/reports/browser_checks/process_map'


def main():
 OUT.mkdir(parents=True,exist_ok=True)
 pages=json.load(urlopen('http://127.0.0.1:9222/json/list'))
 page=next((p for p in pages if p['url'].startswith('http://127.0.0.1:8501')),next(p for p in pages if p['type']=='page'))
 results={}
 with connect(page['webSocketDebuggerUrl'],max_size=20_000_000) as socket:
  ident=0
  def command(method,params=None):
   nonlocal ident
   ident+=1;request=ident
   socket.send(json.dumps({'id':request,'method':method,'params':params or {}}))
   while True:
    message=json.loads(socket.recv(timeout=60))
    if message.get('id')==request:
     if 'error' in message:raise RuntimeError(message['error'])
     return message.get('result',{})
  def js(expression):
   result=command('Runtime.evaluate',{'expression':expression,'returnByValue':True})
   if 'exceptionDetails' in result:raise RuntimeError(result['exceptionDetails'])
   return result.get('result',{}).get('value')
  def wait(expression,timeout=60):
   deadline=time.monotonic()+timeout
   while time.monotonic()<deadline:
    if js(expression):return
    time.sleep(.3)
   raise AssertionError(expression)
  def photo(name):
   payload=command('Page.captureScreenshot',{'format':'png','captureBeyondViewport':False})
   (OUT/name).write_bytes(base64.b64decode(payload['data']))
  def click_label(text):
   js("Array.from(document.querySelectorAll('label')).find(x=>x.innerText.includes("+json.dumps(text)+")).click()")
  command('Page.enable')
  command('Emulation.setDeviceMetricsOverride',{'width':1440,'height':1100,'deviceScaleFactor':1,'mobile':False})
  command('Page.navigate',{'url':'http://127.0.0.1:8501'})
  wait("document.body?.innerText.includes('Selected cases') && document.querySelectorAll('.js-plotly-plot').length===2")
  js("Array.from(document.querySelectorAll('[data-testid=stRadio] label')).find(x=>x.innerText.includes('Process Mining')).click()")
  started=time.perf_counter()
  wait("document.querySelector('[data-testid=stEChartsChart] svg')!==null")
  js("(()=>{let e=document.querySelector('[data-testid=stEChartsChart]');for(let n=e;n;n=n.parentElement){let k=Object.keys(n).find(k=>k.startsWith('__reactFiber'));if(!k)continue;for(let f=n[k];f;f=f.return){for(let h=f.memoizedState;h;h=h.next){let c=h.memoizedState?.current;if(c&&typeof c.getOption==='function'){window.__verifiedChart=c;return true}}}}return false})()")
  wait("window.__verifiedChart?.getOption().series[0].links.length===7")
  results['first_graph_ready_seconds']=time.perf_counter()-started
  results['main_nodes']=js("window.__verifiedChart.getOption().series[0].data.map(x=>({id:x.id,label:x.name,raw:x.raw_activity}))")
  results['main_edges']=js("window.__verifiedChart.getOption().series[0].links.length")
  results['metrics']=js("Array.from(document.querySelectorAll('[data-testid=stMetricValue]')).map(x=>x.innerText)")
  js("document.querySelector('[data-testid=stEChartsChart]').scrollIntoView({block:'center'})")
  time.sleep(1);photo('main_path.png')
  bounds=js("(()=>{let r=document.querySelector('[data-testid=stEChartsChart]').getBoundingClientRect();return {x:r.x,y:r.y,width:r.width,height:r.height}})()")
  previous=js("window.__verifiedChart.getOption().series[0].zoom")
  command('Input.dispatchMouseEvent',{'type':'mouseWheel','x':bounds['x']+bounds['width']/2,'y':bounds['y']+200,'deltaY':-160,'deltaX':0})
  wait("window.__verifiedChart.getOption().series[0].zoom!=="+json.dumps(previous))
  results['wheel_zoom_verified']=True
  before=js("JSON.stringify(window.__verifiedChart.getOption().series[0].center)")
  x,y=bounds['x']+bounds['width']/2,bounds['y']+220
  command('Input.dispatchMouseEvent',{'type':'mouseMoved','x':x,'y':y})
  command('Input.dispatchMouseEvent',{'type':'mousePressed','x':x,'y':y,'button':'left','clickCount':1})
  command('Input.dispatchMouseEvent',{'type':'mouseMoved','x':x+40,'y':y+30,'buttons':1,'button':'left'})
  command('Input.dispatchMouseEvent',{'type':'mouseReleased','x':x+40,'y':y+30,'button':'left','clickCount':1})
  wait("JSON.stringify(window.__verifiedChart.getOption().series[0].center)!=="+json.dumps(before))
  results['drag_pan_verified']=True
  # Restore before changing the displayed graph.
  js("window.__verifiedChart.dispatchAction({type:'restore'})")
  click_label('All observed transitions')
  wait("window.__verifiedChart.getOption().series[0].links.length===39")
  results['all_edges']=js("window.__verifiedChart.getOption().series[0].links.length")
  results['all_nodes']=js("window.__verifiedChart.getOption().series[0].data.length")
  rects=js("(()=>{let d=window.__verifiedChart.getModel().getSeriesByIndex(0).getData();let a=[];for(let i=0;i<d.count();i++){let g=d.getItemGraphicEl(i),r=g.getBoundingRect().clone();r.applyTransform(g.getComputedTransform());a.push({x:r.x,y:r.y,width:r.width,height:r.height})}return a})()")
  overlaps=[]
  for i,a in enumerate(rects):
   for j,b in enumerate(rects[i+1:],i+1):
    w=min(a['x']+a['width'],b['x']+b['width'])-max(a['x'],b['x'])
    h=min(a['y']+a['height'],b['y']+b['height'])-max(a['y'],b['y'])
    if w>3 and h>3:overlaps.append([i,j,w,h])
  assert not overlaps,overlaps
  results['full_graph_node_overlaps']=overlaps
  results['all_link_counts']=js("window.__verifiedChart.getOption().series[0].links.map(x=>({source:x.raw_source,target:x.raw_target,frequency:x.value}))")
  js("document.querySelector('[data-testid=stEChartsChart]').scrollIntoView({block:'center'})")
  time.sleep(.5);photo('all_transitions.png')
  click_label('Main path (frequent transitions)')
  wait("window.__verifiedChart.getOption().series[0].links.length===7")
  js("Array.from(document.querySelectorAll('[data-testid=stSelectbox]')).find(x=>x.innerText.includes('Inspect an activity')).querySelector('input').focus()")
  command('Input.insertText',{'text':'Declaration SAVED by EMPLOYEE'})
  for key,code in [('ArrowDown',40),('Enter',13)]:
   command('Input.dispatchKeyEvent',{'type':'keyDown','key':key,'windowsVirtualKeyCode':code})
   command('Input.dispatchKeyEvent',{'type':'keyUp','key':key,'windowsVirtualKeyCode':code})
  wait("Array.from(document.querySelectorAll('[data-testid=stMetric]')).some(x=>x.innerText.includes('Activity occurrences')&&x.innerText.includes('135'))")
  results['saved_activity_occurrences']=135
  results['saved_single_case_explanation_visible']=js("document.body.innerText.includes('134 single-event cases')")
  results['inspected_isolate_visible']=js("window.__verifiedChart.getOption().series[0].data.some(x=>x.raw_activity==='Declaration SAVED by EMPLOYEE'&&x.name.includes('No visible edges'))")
  results['exceptions']=js("document.querySelectorAll('[data-testid=stException]').length")
  command('Emulation.setDeviceMetricsOverride',{'width':390,'height':844,'deviceScaleFactor':1,'mobile':True})
  time.sleep(1)
  js("document.querySelector('[data-testid=stEChartsChart]').scrollIntoView({block:'center'})")
  time.sleep(.5);photo('mobile_map.png')
  results['mobile_width']=js("({viewport:innerWidth,document:document.documentElement.scrollWidth})")
 (OUT/'verification.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
 print(json.dumps(results,indent=2))

if __name__=='__main__':main()

