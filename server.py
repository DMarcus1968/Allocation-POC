from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
from urllib.parse import urlparse
from market.scenario import baseline

ROOT = Path(__file__).parent
STATE = {"holds_released": 0, "second_show": False, "cleared": False, "requests": {}}

class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs): super().__init__(*args, directory=str(ROOT / "web"), **kwargs)
    def send_json(self, value, status=200):
        body=json.dumps(value).encode(); self.send_response(status); self.send_header("Content-Type","application/json"); self.send_header("Content-Length",str(len(body))); self.end_headers(); self.wfile.write(body)
    def do_GET(self):
        if urlparse(self.path).path == "/api/scenario":
            data=json.loads((ROOT/"data/baseline.json").read_text()) if (ROOT/"data/baseline.json").exists() else baseline(2026, 500_000)
            data["state"]=STATE; return self.send_json(data)
        return super().do_GET()
    def do_POST(self):
        path=urlparse(self.path).path; n=int(self.headers.get("Content-Length",0)); payload=json.loads(self.rfile.read(n) or b"{}")
        if path == "/api/request": STATE["requests"][payload.get("fan","Demo fan")]=payload; return self.send_json({"ok":True,"message":"Request saved. You may edit it until registration closes."})
        if path == "/api/action":
            action=payload.get("action")
            if action=="release": STATE["holds_released"]=min(3000, STATE["holds_released"]+3000)
            elif action=="second": STATE["second_show"]=True
            elif action=="clear": STATE["cleared"]=True
            return self.send_json({"ok":True,"state":STATE})
        self.send_json({"error":"not found"},404)

if __name__ == "__main__":
    print("DemandMatch running at http://127.0.0.1:8000")
    ThreadingHTTPServer(("127.0.0.1",8000),Handler).serve_forever()
