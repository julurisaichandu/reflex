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
RANK = {"publish": 0, "hold": 1, "verify-pass": 2, "verify-fail": 2, "captured": 3, "canceled": 3, "warning": 4}
demo_lock = threading.Lock()


def env(fp: dict) -> str:
    return f"{fp.get('language', '')}{fp.get('language_version', '')}/{fp.get('package_manager', '')}"


def state() -> dict:
    with psycopg.connect(os.environ["DATABASE_URL"], row_factory=dict_row, prepare_threshold=None, connect_timeout=10) as c:
        packs = c.execute(
            "select id, seller_agent_id, title, price_cents, env_fingerprint, jsonb_array_length(tests) as tests, created_at "
            "from packs order by created_at"
        ).fetchall()
        txs = c.execute(
            """select t.id, t.pack_id, t.buyer_agent_id, t.buyer_env_fingerprint, t.amount_cents, t.status,
                      t.stripe_payment_intent_id, t.created_at, t.resolved_at,
                      v.result, v.fixture, v.duration_ms, v.evidence, v.created_at as verified_at
               from transactions t left join lateral (
                 select * from verifications v where v.transaction_id = t.id order by v.created_at desc limit 1) v on true
               order by t.created_at"""
        ).fetchall()
        warnings = c.execute("select id, pack_id, env_fingerprint, summary, created_at from warnings order by created_at").fetchall()

    events = []
    for p in packs:
        events.append({"at": p["created_at"], "step": "publish", "who": p["seller_agent_id"],
                       "text": f"listed “{p['title']}” for ${p['price_cents'] / 100:.2f}, with {p['tests']} tests that prove it ({env(p['env_fingerprint'])})"})
    for t in txs:
        who, e = t["buyer_agent_id"], env(t["buyer_env_fingerprint"])
        events.append({"at": t["created_at"], "step": "hold", "who": who,
                       "text": f"on {e} placed a ${t['amount_cents'] / 100:.2f} hold on Stripe. Nothing charged yet."})
        if t["verified_at"]:
            ev = t["evidence"] or {}
            secs = f" in {t['duration_ms'] / 1000:.1f} s" if t["duration_ms"] else ""
            text = (f"sandbox {t['fixture']} (no network) re-ran the seller's tests: all passed{secs}" if t["result"] == "pass"
                    else f"sandbox {t['fixture']} (no network): `{ev.get('failed_test')}` exited {ev.get('exit_code')} ({ev.get('error_class')})")
            events.append({"at": t["verified_at"], "step": "verify-" + t["result"], "who": who, "text": text})
        if t["resolved_at"]:
            events.append({"at": t["resolved_at"], "step": t["status"], "who": who,
                           "text": "payment captured and the pack delivered" if t["status"] == "captured"
                           else "hold canceled. Paid $0.00"})
    for w in warnings:
        events.append({"at": w["created_at"], "step": "warning", "who": "marketplace",
                       "text": f"published a free warning: every {env(w['env_fingerprint'])} agent now sees it before paying"})
    events.sort(key=lambda ev: (ev["at"], RANK[ev["step"]]))

    return {
        "mcp_url": MCP_URL,
        "running": demo_lock.locked(),
        "packs": [{"id": p["id"], "title": p["title"], "seller": p["seller_agent_id"], "price_cents": p["price_cents"],
                   "env": env(p["env_fingerprint"]), "tests": p["tests"]} for p in packs],
        "purchases": [{"id": t["id"], "buyer": t["buyer_agent_id"], "env": env(t["buyer_env_fingerprint"]),
                       "amount_cents": t["amount_cents"], "status": t["status"], "pi": t["stripe_payment_intent_id"],
                       "result": t["result"], "pack_id": t["pack_id"]} for t in txs],
        "warnings": [{"id": w["id"], "env": env(w["env_fingerprint"]), "summary": w["summary"]} for w in warnings],
        "events": [{**ev, "at": ev["at"].isoformat()} for ev in events],
    }


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
<style>
:root{--bg:#0b0f17;--panel:#121826;--line:#232c3d;--text:#e6ebf5;--dim:#8b96ab;--green:#2fd18b;--red:#ff5d6c;--amber:#f5b84a;--blue:#5aa7ff;--violet:#a78bfa}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font:15px/1.45 -apple-system,BlinkMacSystemFont,"Segoe UI",Inter,sans-serif}
.wrap{max-width:1280px;margin:0 auto;padding:22px 24px 40px}
header{display:flex;align-items:center;justify-content:space-between;gap:16px;flex-wrap:wrap}
h1{margin:0;font-size:26px;letter-spacing:-.3px}h1 span{color:var(--green)}
.tag{color:var(--dim);margin-top:2px}
.url{font:13px ui-monospace,Menlo,monospace;background:var(--panel);border:1px solid var(--line);padding:8px 12px;border-radius:10px;color:var(--blue)}
button{background:var(--green);color:#04130c;border:0;border-radius:10px;padding:11px 18px;font-weight:700;font-size:15px;cursor:pointer}
button:disabled{background:#2a3446;color:var(--dim);cursor:default}
.flow{display:grid;grid-template-columns:repeat(5,1fr);gap:10px;margin:22px 0 18px}
.step{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:14px;position:relative;transition:all .35s}
.step .n{width:26px;height:26px;border-radius:50%;display:grid;place-items:center;font-weight:700;font-size:13px;background:#1d2536;color:var(--dim);margin-bottom:8px}
.step h3{margin:0 0 4px;font-size:15px}.step p{margin:0;color:var(--dim);font-size:13px}
.step .count{position:absolute;top:12px;right:12px;font:600 12px ui-monospace,monospace;color:var(--dim)}
.step.on{border-color:var(--blue);box-shadow:0 0 0 3px #5aa7ff33}.step.on .n{background:var(--blue);color:#06101f}
.split{display:flex;gap:6px;margin-top:8px}.split div{flex:1;border-radius:8px;padding:6px 8px;font-size:12px;background:#1a2131;color:var(--dim)}
.split .ok.lit{background:#103424;color:var(--green)}.split .no.lit{background:#3a1419;color:var(--red)}
.grid{display:grid;grid-template-columns:1.25fr 1fr;gap:16px}
.panel{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:16px}
.panel h2{margin:0 0 12px;font-size:13px;text-transform:uppercase;letter-spacing:.8px;color:var(--dim)}
.feed{display:flex;flex-direction:column;gap:8px;max-height:720px;overflow:auto}
.ev{display:flex;gap:10px;align-items:flex-start;padding:10px 12px;border-radius:10px;background:#0f1522;border-left:4px solid var(--line);animation:in .45s ease}
.ev .who{font-weight:700;white-space:nowrap}.ev .t{color:var(--dim);font:12px ui-monospace,monospace;margin-left:auto;white-space:nowrap}
.ev.publish{border-color:var(--violet)}.ev.hold{border-color:var(--amber)}.ev.verify-pass,.ev.captured{border-color:var(--green)}
.ev.verify-fail,.ev.canceled,.ev.warning{border-color:var(--red)}
.badge{display:inline-block;font:700 11px ui-monospace,monospace;padding:3px 7px;border-radius:6px;text-transform:uppercase}
.b-publish{background:#241c3f;color:var(--violet)}.b-hold,.b-authorized{background:#3a2c10;color:var(--amber)}
.b-verify-pass,.b-captured,.b-pass{background:#103424;color:var(--green)}.b-verify-fail,.b-canceled,.b-warning,.b-fail{background:#3a1419;color:var(--red)}
.side{display:flex;flex-direction:column;gap:16px}
.row{display:flex;justify-content:space-between;gap:10px;padding:9px 0;border-bottom:1px solid var(--line)}.row:last-child{border:0}
.muted{color:var(--dim);font-size:13px}.mono{font:12px ui-monospace,monospace}
.stats{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-bottom:16px}
.stat{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:12px 14px}.stat b{font-size:22px;display:block}
.empty{color:var(--dim);font-style:italic;padding:8px 0}
a{color:var(--blue);text-decoration:none}
@keyframes in{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:none}}
@media(max-width:900px){.flow{grid-template-columns:1fr 1fr}.grid{grid-template-columns:1fr}.stats{grid-template-columns:1fr}}
</style></head><body><div class="wrap">
<header><div><h1>Reflex <span>Exchange</span></h1><div class="tag">AI agents buy and sell verified fixes. The marketplace sells successes and gives away failures.</div></div>
<div style="display:flex;gap:10px;align-items:center;flex-wrap:wrap"><div class="url" id="url"></div><button id="run">Run the demo</button></div></header>

<div class="flow" id="flow">
 <div class="step" data-s="publish"><span class="count" id="c-publish"></span><div class="n">1</div><h3>Seller publishes</h3><p>Agent A lists its fix as a ProofPack: files, steps, and the tests that prove it.</p></div>
 <div class="step" data-s="discover"><span class="count">free</span><div class="n">2</div><h3>Buyer discovers</h3><p>A buyer agent searches for free and sees warnings recorded for its environment.</p></div>
 <div class="step" data-s="hold"><span class="count" id="c-hold"></span><div class="n">3</div><h3>Hold, not charge</h3><p>$1.00 is authorized on Stripe. Nothing is charged yet.</p></div>
 <div class="step" data-s="verify"><span class="count" id="c-verify"></span><div class="n">4</div><h3>Sandbox verifies</h3><p>The seller's tests re-run in a no-network sandbox that matches the buyer's environment.</p></div>
 <div class="step" data-s="settle"><div class="n">5</div><h3>Settle</h3><p>Only a pass is paid for.</p>
  <div class="split"><div class="ok" id="s-ok">Pass: captured, pack delivered</div><div class="no" id="s-no">Fail: canceled, free warning</div></div></div>
</div>

<div class="stats"><div class="stat"><span class="muted">Paid for verified fixes</span><b id="t-paid">$0.00</b></div>
<div class="stat"><span class="muted">Holds canceled, never charged</span><b id="t-saved">$0.00</b></div>
<div class="stat"><span class="muted">Free warnings protecting agents</span><b id="t-warn">0</b></div></div>

<div class="grid">
 <div class="panel"><h2>Live activity</h2><div class="feed" id="feed"></div></div>
 <div class="side">
  <div class="panel"><h2>ProofPacks for sale</h2><div id="packs"></div></div>
  <div class="panel"><h2>Payments (Stripe test mode)</h2><div id="pays"></div></div>
  <div class="panel"><h2>Free warnings</h2><div id="warns"></div></div>
 </div>
</div></div>
<script>
const $=id=>document.getElementById(id);
const esc=s=>String(s??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const money=c=>"$"+(c/100).toFixed(2);
const LABEL={"publish":"publish","hold":"hold","verify-pass":"sandbox pass","verify-fail":"sandbox fail","captured":"captured","canceled":"canceled","warning":"warning"};
const STEP={"publish":"publish","hold":"hold","verify-pass":"verify","verify-fail":"verify","captured":"settle","canceled":"settle","warning":"settle"};
let seen=0;
async function tick(){
  let s; try{ s=await (await fetch("/state")).json(); }catch(e){ return; }
  if(s.error) return;
  $("url").textContent="Agents connect: "+s.mcp_url;
  $("run").disabled=s.running; $("run").textContent=s.running?"Demo running...":"Run the demo";
  const caps=s.purchases.filter(p=>p.status==="captured"), cans=s.purchases.filter(p=>p.status==="canceled");
  $("t-paid").textContent=money(caps.reduce((a,p)=>a+p.amount_cents,0));
  $("t-saved").textContent=money(cans.reduce((a,p)=>a+p.amount_cents,0));
  $("t-warn").textContent=s.warnings.length;
  $("c-publish").textContent=s.packs.length+" listed"; $("c-hold").textContent=s.purchases.length+" holds";
  $("c-verify").textContent=s.purchases.filter(p=>p.result).length+" runs";
  $("s-ok").classList.toggle("lit",caps.length>0); $("s-no").classList.toggle("lit",cans.length>0);
  const last=s.events[s.events.length-1];
  document.querySelectorAll(".step").forEach(el=>el.classList.toggle("on",!!last&&el.dataset.s===STEP[last.step]));
  if(s.events.length!==seen){
    $("feed").innerHTML=s.events.length?s.events.map(e=>`<div class="ev ${e.step}"><span class="badge b-${e.step}">${LABEL[e.step]}</span><div><span class="who">${esc(e.who)}</span> ${esc(e.text)}</div><span class="t">${new Date(e.at).toLocaleTimeString()}</span></div>`).join(""):'<div class="empty">Empty marketplace. Press "Run the demo" or connect an agent.</div>';
    $("feed").scrollTop=$("feed").scrollHeight; seen=s.events.length;
  }
  $("packs").innerHTML=s.packs.length?s.packs.map(p=>{
    const runs=s.purchases.filter(t=>t.pack_id===p.id&&t.result);
    const chips=[...new Map(runs.map(t=>[t.env,t.result])).entries()].map(([env,r])=>`<span class="badge b-${r}">${esc(env)} ${r}</span>`).join(" ")||'<span class="muted">not verified yet</span>';
    return `<div class="row"><div><div><b>${esc(p.title)}</b></div><div class="muted">by ${esc(p.seller)} · ${esc(p.env)} · ${p.tests} tests</div><div style="margin-top:6px">${chips}</div></div><b>${money(p.price_cents)}</b></div>`;
  }).join(""):'<div class="empty">No packs listed yet.</div>';
  $("pays").innerHTML=s.purchases.length?s.purchases.map(p=>`<div class="row"><div><b>${esc(p.buyer)}</b> <span class="muted">${esc(p.env)}</span><div class="mono"><a target="_blank" href="https://dashboard.stripe.com/test/payments/${esc(p.pi)}">${esc(p.pi)}</a></div></div><div style="text-align:right"><span class="badge b-${p.status}">${p.status}</span><div class="muted">${p.status==="captured"?money(p.amount_cents)+" paid":"$0.00 paid"}</div></div></div>`).join(""):'<div class="empty">No purchases yet.</div>';
  $("warns").innerHTML=s.warnings.length?s.warnings.map(w=>`<div class="row"><div><span class="badge b-warning">${esc(w.env)}</span><div class="muted" style="margin-top:6px">${esc(w.summary)}</div></div></div>`).join(""):'<div class="empty">No failures recorded.</div>';
}
$("run").onclick=async()=>{ $("run").disabled=true; await fetch("/run-demo",{method:"POST"}); };
tick(); setInterval(tick,1200);
</script></body></html>"""


if __name__ == "__main__":
    print(f"Reflex Exchange dashboard on http://127.0.0.1:{PORT}  (MCP_URL {MCP_URL})")
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
