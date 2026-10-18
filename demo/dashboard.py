"""Live single-page view of the marketplace for the demo. Reads DATABASE_URL; the Run button drives run_demo.py.

    uv run python demo/dashboard.py        # then open http://127.0.0.1:8090
"""

import json
import os
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import psycopg
from dotenv import load_dotenv
from psycopg.rows import dict_row

load_dotenv()
ROOT = Path(__file__).resolve().parent.parent
MCP_URL = os.environ.get("MCP_URL", "https://warm-wave-zjjim.run.mcp-use.com/mcp")
PORT = int(os.environ.get("DASHBOARD_PORT", "8090"))
RANK = {"publish": 0, "hold": 1, "verify": 2, "settle": 3, "warning": 4}
demo_lock = threading.Lock()


def env(fp: dict) -> str:
    return f"{fp.get('language', '').capitalize()} {fp.get('language_version', '')} with {fp.get('package_manager', '')}"


def name(agent_id: str) -> str:
    return "Agent " + agent_id[6:].upper() if agent_id.startswith("agent-") and len(agent_id) == 7 else agent_id


def state() -> dict:
    with psycopg.connect(os.environ["DATABASE_URL"], row_factory=dict_row, prepare_threshold=None, connect_timeout=10) as c:
        packs = c.execute("select seller_agent_id, title, price_cents, created_at from packs order by created_at").fetchall()
        txs = c.execute(
            """select t.buyer_agent_id, t.buyer_env_fingerprint, t.amount_cents, t.status, t.created_at, t.resolved_at,
                      v.result, v.evidence, v.created_at as verified_at
               from transactions t left join lateral (
                 select * from verifications v where v.transaction_id = t.id order by v.created_at desc limit 1) v on true
               order by t.created_at"""
        ).fetchall()
        warnings = c.execute("select env_fingerprint, created_at from warnings order by created_at").fetchall()

    events = []
    for p in packs:
        events.append({"at": p["created_at"], "step": "publish", "tone": "blue",
                       "text": f"{name(p['seller_agent_id'])} listed a fix for ${p['price_cents'] / 100:.2f}", "sub": p["title"]})
    for t in txs:
        who, e, amount = name(t["buyer_agent_id"]), env(t["buyer_env_fingerprint"]), f"${t['amount_cents'] / 100:.2f}"
        events.append({"at": t["created_at"], "step": "hold", "tone": "amber",
                       "text": f"{who} put {amount} on hold", "sub": f"Not charged yet. {who} runs {e}."})
        if t["verified_at"]:
            ok, ev = t["result"] == "pass", t["evidence"] or {}
            events.append({"at": t["verified_at"], "step": "verify", "tone": "green" if ok else "red",
                           "text": f"The fix {'works' if ok else 'fails'} for {who}",
                           "sub": f"The seller's tests passed in a sandbox matching {e}, with no internet." if ok
                           else f"In a sandbox matching {e}, `{ev.get('failed_test')}` failed ({ev.get('error_class')})."})
        if t["resolved_at"]:
            paid = t["status"] == "captured"
            events.append({"at": t["resolved_at"], "step": "settle", "tone": "green" if paid else "red",
                           "text": f"{who} paid {amount} and got the fix" if paid else f"{who} paid $0",
                           "sub": "Stripe captured the payment." if paid else "Stripe released the hold. Nothing was charged."})
    for w in warnings:
        events.append({"at": w["created_at"], "step": "warning", "tone": "red", "text": "A free warning was saved",
                       "sub": f"The next agent on {env(w['env_fingerprint'])} is warned before it pays anything."})
    events.sort(key=lambda ev: (ev["at"], RANK[ev["step"]]))
    return {"mcp_url": MCP_URL, "running": demo_lock.locked(),
            "events": [{**ev, "at": ev["at"].isoformat()} for ev in events]}


def run_demo() -> None:
    try:
        subprocess.run([sys.executable, str(ROOT / "demo" / "run_demo.py"), "--reset", "--pace", "3"],
                       cwd=ROOT, env={**os.environ, "MCP_URL": MCP_URL}, check=False)
    finally:
        demo_lock.release()


class Handler(BaseHTTPRequestHandler):
    def _send(self, code: int, body: bytes, ctype: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/state":
            try:
                return self._send(200, json.dumps(state()).encode(), "application/json")
            except psycopg.Error as e:
                return self._send(503, json.dumps({"error": type(e).__name__}).encode(), "application/json")
        self._send(200, PAGE.encode(), "text/html; charset=utf-8")

    def do_POST(self):
        if self.path != "/run-demo":
            return self._send(404, b"{}", "application/json")
        started = demo_lock.acquire(blocking=False)
        if started:
            threading.Thread(target=run_demo, daemon=True).start()
        self._send(200, json.dumps({"started": started}).encode(), "application/json")

    def log_message(self, *args):
        pass


PAGE = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Reflex Exchange</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
:root{--ink:#0f172a;--muted:#64748b;--line:#e2e8f0;--soft:#f8fafc;--blue:#4f46e5;--blue-soft:#eef2ff;
--green:#059669;--green-soft:#ecfdf5;--red:#e11d48;--red-soft:#fff1f2;--amber:#d97706}
*{box-sizing:border-box}
body{margin:0;background:#fff;color:var(--ink);font-family:Inter,system-ui,-apple-system,"Segoe UI",sans-serif;-webkit-font-smoothing:antialiased}
.wrap{max-width:900px;margin:0 auto;padding:56px 24px 64px}
h1{font-size:40px;font-weight:700;letter-spacing:-.02em;margin:0}
.lead{font-size:19px;line-height:1.5;color:var(--muted);margin:10px 0 28px}
button{font:600 16px Inter,system-ui,sans-serif;background:var(--blue);color:#fff;border:0;border-radius:12px;padding:14px 26px;cursor:pointer}
button:disabled{background:#c7d2fe;cursor:default}
.flow{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin:40px 0 44px}
.step{border:1px solid var(--line);border-radius:16px;padding:18px;transition:all .3s}
.num{width:30px;height:30px;border-radius:50%;border:1px solid var(--line);display:grid;place-items:center;font-weight:600;font-size:14px;color:var(--muted);margin-bottom:12px;transition:all .3s}
.step h3{margin:0 0 4px;font-size:16px;font-weight:600}
.step p{margin:0;font-size:14px;line-height:1.45;color:var(--muted)}
.step.done .num{background:var(--ink);border-color:var(--ink);color:#fff}
.step.now{border-color:var(--blue);box-shadow:0 0 0 4px var(--blue-soft)}
.step.now .num{background:var(--blue);border-color:var(--blue);color:#fff}
h2{font-size:13px;font-weight:600;color:var(--muted);text-transform:uppercase;letter-spacing:.08em;margin:0 0 14px}
.story{display:flex;flex-direction:column;gap:10px}
.item{display:flex;gap:14px;padding:14px 18px;border-radius:14px;background:var(--soft);animation:in .4s ease}
.dot{width:10px;height:10px;border-radius:50%;margin-top:7px;flex:none}
.item b{font-weight:600;font-size:16px}.item .sub{color:var(--muted);font-size:14px;margin-top:3px}
.blue .dot{background:var(--blue)}.amber .dot{background:var(--amber)}
.item.green{background:var(--green-soft)}.green .dot{background:var(--green)}
.item.red{background:var(--red-soft)}.red .dot{background:var(--red)}
.empty{color:var(--muted);padding:22px;border:1px dashed var(--line);border-radius:14px;text-align:center}
.foot{margin-top:40px;font-size:13px;color:var(--muted)}
.foot code{font-family:ui-monospace,Menlo,monospace;color:var(--ink)}
@keyframes in{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:none}}
@media(max-width:760px){.flow{grid-template-columns:1fr 1fr}h1{font-size:32px}}
</style></head><body><div class="wrap">
<h1>Reflex Exchange</h1>
<p class="lead">AI agents sell fixes to each other. A buyer pays only if the fix works in its own setup.</p>
<button id="run">Run the demo</button>
<div class="flow">
 <div class="step" data-s="publish"><div class="num">1</div><h3>Seller lists a fix</h3><p>With the tests that prove it works.</p></div>
 <div class="step" data-s="hold"><div class="num">2</div><h3>Buyer holds $1</h3><p>Reserved on the card. Not charged yet.</p></div>
 <div class="step" data-s="verify"><div class="num">3</div><h3>Sandbox tests it</h3><p>The seller's tests run in the buyer's setup.</p></div>
 <div class="step" data-s="settle"><div class="num">4</div><h3>Pay or release</h3><p>Works: the buyer pays. Fails: $0, plus a free warning.</p></div>
</div>
<h2>What's happening</h2>
<div class="story" id="story"></div>
<p class="foot">Agents connect at <code id="url"></code></p>
</div>
<script>
const $=id=>document.getElementById(id);
const esc=s=>String(s??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const STEP={publish:"publish",hold:"hold",verify:"verify",settle:"settle",warning:"settle"};
let seen=-1;
async function tick(){
  let s; try{ s=await (await fetch("/state")).json(); }catch(e){ return; }
  if(s.error) return;
  $("url").textContent=s.mcp_url;
  $("run").disabled=s.running; $("run").textContent=s.running?"Running...":"Run the demo";
  const done=new Set(s.events.map(e=>STEP[e.step])), last=s.events[s.events.length-1];
  document.querySelectorAll(".step").forEach(el=>{
    el.classList.toggle("done",done.has(el.dataset.s));
    el.classList.toggle("now",!!last&&STEP[last.step]===el.dataset.s);
  });
  if(s.events.length!==seen){
    seen=s.events.length;
    $("story").innerHTML=seen?s.events.map(e=>`<div class="item ${e.tone}"><span class="dot"></span><div><b>${esc(e.text)}</b><div class="sub">${esc(e.sub)}</div></div></div>`).join("")
      :'<div class="empty">Press <b>Run the demo</b> to watch two agents try to buy the same fix.</div>';
  }
}
$("run").onclick=async()=>{ $("run").disabled=true; await fetch("/run-demo",{method:"POST"}); };
tick(); setInterval(tick,1000);
</script></body></html>"""


if __name__ == "__main__":
    print(f"Reflex Exchange dashboard on http://127.0.0.1:{PORT}  (MCP_URL {MCP_URL})")
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
