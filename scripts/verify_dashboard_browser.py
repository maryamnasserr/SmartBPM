"""Optional real-browser smoke check using Edge CDP and Streamlit's websockets dependency.
Start a headless browser on port 9222 and SmartBPM on port 8501 first.
This checks rendered DOM/Plotly charts and saves screenshots, never changes source data.
"""
import base64
import json
from pathlib import Path
import time
from urllib.request import urlopen
from websockets.sync.client import connect

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/reports"


def main():
    pages = json.load(urlopen("http://127.0.0.1:9222/json/list"))
    target = next(page for page in pages if page["type"] == "page")
    results = {}
    with connect(target["webSocketDebuggerUrl"], max_size=20_000_000) as socket:
        counter = 0
        def command(method, params=None):
            nonlocal counter
            counter += 1
            message_id = counter
            socket.send(json.dumps({"id": message_id, "method": method, "params": params or {}}))
            while True:
                reply = json.loads(socket.recv(timeout=60))
                if reply.get("id") == message_id:
                    if "error" in reply:
                        raise RuntimeError(reply["error"])
                    return reply.get("result", {})
        def evaluate(expression):
            result = command("Runtime.evaluate", {"expression": expression, "returnByValue": True})
            if "exceptionDetails" in result:
                raise RuntimeError(result["exceptionDetails"])
            return result.get("result", {}).get("value")
        def wait_for(expression, timeout=50):
            deadline = time.monotonic() + timeout
            while time.monotonic() < deadline:
                if evaluate(expression):
                    return
                time.sleep(.4)
            raise AssertionError(f"Browser condition timed out: {expression}")
        def screenshot(name):
            shot = command("Page.captureScreenshot", {"format": "png", "captureBeyondViewport": False})
            (OUT / name).write_bytes(base64.b64decode(shot["data"]))
        def navigate(label):
            expression = "Array.from(document.querySelectorAll('[data-testid=stRadio] label')).find(x=>x.innerText.includes(" + json.dumps(label) + ")).click()"
            evaluate(expression)
        command("Page.enable")
        command("Emulation.setDeviceMetricsOverride", {"width": 1440, "height": 1100, "deviceScaleFactor": 1, "mobile": False})
        command("Page.navigate", {"url": "http://127.0.0.1:8501"})
        wait_for("document.body?.innerText.includes('Selected cases') && document.querySelectorAll('.js-plotly-plot').length===2")
        wait_for("Array.from(document.querySelectorAll('[data-testid=stMetricValue]')).some(x=>x.innerText==='10,500')")
        results["overview_metrics"] = evaluate("Array.from(document.querySelectorAll('[data-testid=stMetricValue]')).map(x=>x.innerText)")
        results["overview_plotly_traces"] = evaluate("Array.from(document.querySelectorAll('.js-plotly-plot')).map(x=>({traces:x.data.length,type:x.data[0].type}))")
        screenshot("dashboard_desktop.png")
        bounds = evaluate("(()=>{let r=document.querySelector('.js-plotly-plot .nsewdrag').getBoundingClientRect();return {x:r.x,y:r.y,width:r.width,height:r.height}})()")
        previous = evaluate("document.querySelector('.js-plotly-plot')._fullLayout.xaxis.range")
        x1, x2 = bounds["x"] + bounds["width"] * .15, bounds["x"] + bounds["width"] * .65
        y1, y2 = bounds["y"] + 30, bounds["y"] + 180
        command("Input.dispatchMouseEvent", {"type": "mouseMoved", "x": x1, "y": y1})
        command("Input.dispatchMouseEvent", {"type": "mousePressed", "x": x1, "y": y1, "button": "left", "clickCount": 1})
        command("Input.dispatchMouseEvent", {"type": "mouseMoved", "x": x2, "y": y2, "button": "left", "buttons": 1})
        command("Input.dispatchMouseEvent", {"type": "mouseReleased", "x": x2, "y": y2, "button": "left", "clickCount": 1})
        wait_for("JSON.stringify(document.querySelector('.js-plotly-plot')._fullLayout.xaxis.range)!==" + json.dumps(json.dumps(previous, separators=(",", ":"))))
        results["plotly_drag_zoom_changed_axis_range"] = True
        navigate("Activities & resources")
        wait_for("document.body?.innerText.includes('What happens, and who is recorded?') && document.querySelectorAll('.js-plotly-plot').length===2")
        results["activity_bar_count"] = evaluate("document.querySelector('.js-plotly-plot').data[0].y.length")
        screenshot("dashboard_activities.png")
        navigate("Variants & repetition")
        wait_for("document.body?.innerText.includes('Paths and repeated work') && document.querySelectorAll('.js-plotly-plot').length===2")
        screenshot("dashboard_variants.png")
        navigate("Case boundaries")
        wait_for("document.body?.innerText.includes('First and last observed activities') && document.querySelectorAll('.js-plotly-plot').length===2")
        results["boundaries_rendered"] = True
        navigate("Overview")
        wait_for("document.body?.innerText.includes('Time across the observed process') && document.querySelectorAll('.js-plotly-plot').length===2")
        evaluate("document.querySelector('input[type=range]').focus()")
        command("Input.dispatchKeyEvent", {"type": "keyDown", "key": "ArrowRight", "code": "ArrowRight", "windowsVirtualKeyCode": 39})
        command("Input.dispatchKeyEvent", {"type": "keyUp", "key": "ArrowRight", "code": "ArrowRight", "windowsVirtualKeyCode": 39})
        wait_for("document.querySelector('[data-testid=stMetricValue]').innerText!=='10,500'")
        results["duration_filter_metrics"] = evaluate("Array.from(document.querySelectorAll('[data-testid=stMetricValue]')).map(x=>x.innerText)")
        evaluate("Array.from(document.querySelectorAll('button')).find(x=>x.innerText==='Reset filters').click()")
        wait_for("document.querySelector('[data-testid=stMetricValue]').innerText==='10,500'")
        results["reset_restored_cases"] = True
        command("Emulation.setDeviceMetricsOverride", {"width": 390, "height": 844, "deviceScaleFactor": 1, "mobile": True})
        time.sleep(2)
        screenshot("dashboard_mobile.png")
        results["mobile_document_width"] = evaluate("({viewport:innerWidth,document:document.documentElement.scrollWidth})")
        results["browser_exceptions_visible"] = evaluate("document.querySelectorAll('[data-testid=stException]').length")
        assert results["browser_exceptions_visible"] == 0
    (OUT / "dashboard_browser_verification.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()


