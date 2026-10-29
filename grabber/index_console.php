<?php
// osint/grabber/index_console.php  (served as the one dashboard)
// Single-page OSINT Console: Phone OSINT (auto-resolve) + Tools.
?>
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>OSINT Console</title>
<style>
  /* ===== TERMINAL RETRO — AMBER CRT ===== */
  :root{
    --bg:#0a0600; --card:#120c02; --line:#3a2a08;
    --amber:#ffb000; --amber-dim:#b87900; --amber-bright:#ffd066;
    --green:#39ff88; --red:#ff5b3d; --warn:#ffb000;
    --txt:#ffb000; --mut:#8a6410; --ok:#39ff88;
    --glow:0 0 2px #ffb00099, 0 0 8px #ffb00040;
  }
  *{box-sizing:border-box}
  html,body{height:100%}
  body{
    margin:0;color:var(--amber);background:#000;
    font-family:"VT323","Share Tech Mono",ui-monospace,"Courier New",Consolas,monospace;
    font-size:16px;letter-spacing:.4px;text-shadow:var(--glow);
    image-rendering:pixelated;
  }
  /* CRT overlay: scanlines + vignette + subtle flicker */
  body::before{
    content:"";position:fixed;inset:0;pointer-events:none;z-index:9999;
    background:
      repeating-linear-gradient(0deg, rgba(0,0,0,.28) 0px, rgba(0,0,0,.28) 1px, transparent 1px, transparent 3px),
      radial-gradient(ellipse at center, transparent 55%, rgba(0,0,0,.72) 100%);
    mix-blend-mode:multiply;
  }
  body::after{
    content:"";position:fixed;inset:0;pointer-events:none;z-index:9998;
    background:linear-gradient(rgba(255,176,0,.03), rgba(255,176,0,.03));
    animation:flicker 4s infinite steps(60);
  }
  @keyframes flicker{0%,96%{opacity:.35}97%{opacity:.55}98%{opacity:.3}100%{opacity:.35}}
  ::selection{background:var(--amber);color:#000;text-shadow:none}
  ::-webkit-scrollbar{width:10px;height:10px}
  ::-webkit-scrollbar-track{background:#0a0600}
  ::-webkit-scrollbar-thumb{background:var(--line);border:1px solid var(--amber-dim)}

  header{
    padding:12px 20px;border-bottom:1px solid var(--line);display:flex;align-items:center;gap:12px;
    flex-wrap:wrap;position:sticky;top:0;background:rgba(10,6,0,.96);z-index:100;
    box-shadow:0 0 12px #ffb00022;
  }
  header h1{font-size:20px;margin:0;letter-spacing:2px;color:var(--amber-bright);
    text-shadow:0 0 6px #ffb000, 0 0 16px #ffb00066}
  header h1::before{content:"> "}
  header h1::after{content:"_";animation:blink 1.1s steps(2) infinite}
  @keyframes blink{50%{opacity:0}}
  .tabs{display:flex;gap:6px;margin-left:14px;flex-wrap:wrap}
  .tab{padding:6px 14px;background:transparent;border:1px solid var(--line);cursor:pointer;
    font-size:15px;color:var(--mut);letter-spacing:1px}
  .tab::before{content:"["}.tab::after{content:"]"}
  .tab.active{background:#2a1c00;border-color:var(--amber);color:var(--amber-bright);box-shadow:0 0 8px #ffb00055 inset}
  .tab:hover{color:var(--amber)}
  .badge{font-size:12px;padding:2px 8px;border:1px solid var(--line);color:var(--mut);text-transform:uppercase}
  .badge.loc{border-color:#7a2a00;color:#ff8a3d}
  .badge.hit{border-color:#2a4a00;color:#9fd000}
  .badge.fp{border-color:#5a4a1f;color:var(--warn)}
  .badge.ok{border-color:#1f6b4f;color:var(--green)}
  .spacer{flex:1}
  button.btn{background:#1a1200;color:var(--amber);border:1px solid var(--line);padding:6px 14px;
    cursor:pointer;font-family:inherit;font-size:15px;letter-spacing:1px;text-shadow:var(--glow)}
  button.btn:hover{background:#2a1c00;border-color:var(--amber);box-shadow:0 0 8px #ffb00044}
  button.btn.acc{background:var(--amber);border:1px solid var(--amber-bright);color:#0a0600;
    font-weight:700;text-shadow:none}
  button.btn.acc:hover{box-shadow:0 0 14px #ffb000aa}
  .view{display:none}.view.active{display:block}
  .wrap{display:grid;grid-template-columns:1fr 430px;height:calc(100vh - 54px)}
  @media(max-width:900px){.wrap{grid-template-columns:1fr;height:auto}}
  .table{overflow:auto;padding:12px}
  table{width:100%;border-collapse:collapse;font-size:14px}
  th,td{text-align:left;padding:7px 10px;border-bottom:1px solid #241a06;vertical-align:top}
  th{position:sticky;top:0;background:#0e0901;color:var(--amber-bright);font-weight:400;z-index:2;
    text-transform:uppercase;letter-spacing:1px;border-bottom:1px solid var(--line)}
  tr.row{cursor:pointer}
  tr.row:hover{background:#1a1200}
  tr.row.sel{background:#2a1c00;box-shadow:0 0 8px #ffb00033 inset}
  td.ip{color:var(--amber-bright)}
  td.ts{color:var(--mut);white-space:nowrap}
  #map{height:100%;min-height:320px;filter:sepia(.6) hue-rotate(-15deg) saturate(1.4) contrast(1.05) brightness(.85)}
  .side{border-left:1px solid var(--line);display:flex;flex-direction:column}
  .side .pad{padding:16px;overflow:auto}
  .detail h2{font-size:15px;color:var(--amber-bright);margin:0 0 10px;text-transform:uppercase;letter-spacing:2px}
  .detail h2::before{content:":: "}
  .kv{font-size:14px;margin:0 0 7px;display:flex;gap:8px}
  .kv b{color:var(--mut);font-weight:400;min-width:92px;flex-shrink:0}
  .empty{color:var(--mut);font-size:14px;padding:20px;text-align:center}
  .flag{font-size:11px;padding:1px 6px;border:1px solid #1f6b4f;color:var(--green);margin-left:6px}
  .gps{color:var(--green)}
  .pane{height:calc(100vh - 54px);overflow:auto;padding:22px}
  @media(max-width:900px){.pane{height:auto}}
  .search{display:flex;gap:10px;max-width:820px;flex-wrap:wrap}
  input,select{padding:9px 12px;border:1px solid var(--line);background:#0e0901;color:var(--amber);
    font-size:15px;font-family:inherit;letter-spacing:1px;text-shadow:var(--glow)}
  input:focus,select:focus{outline:none;border-color:var(--amber);box-shadow:0 0 10px #ffb00055}
  input.grow{flex:1;min-width:220px}
  .card{background:var(--card);border:1px solid var(--line);padding:16px;margin-top:14px;max-width:1020px;
    box-shadow:0 0 16px #ffb00018, 0 0 40px #00000080 inset}
  .card h3{margin:0 0 12px;font-size:15px;color:var(--amber-bright);text-transform:uppercase;letter-spacing:2px}
  .card h3::before{content:"# "}
  .card h3:not(:first-child){margin-top:22px}
  .grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:8px}
  .field{background:#0e0901;border:1px solid var(--line);padding:9px 11px}
  .field .k{font-size:12px;color:var(--mut);margin-bottom:2px;text-transform:uppercase;letter-spacing:1px}
  .field .v{font-size:15px;word-break:break-word;color:var(--amber-bright)}
  .links a,.chip{display:inline-block;margin:4px 8px 4px 0;padding:5px 11px;background:#0e0901;
    border:1px solid var(--line);color:var(--amber);text-decoration:none;font-size:14px;
    text-shadow:var(--glow)}
  .links a::before{content:"▸ "}
  .links a:hover{border-color:var(--amber);background:#1a1200;box-shadow:0 0 8px #ffb00044}
  .chip.found{background:#0d1f0d;border-color:#1f6b4f;color:var(--green)}
  .chip.found::before{content:"● "}
  .chip.notfound{opacity:.4}
  .chip.maybe{background:#221800;border-color:#7a5a00;color:var(--warn)}
  .chip.inc{background:#1a1200;border-color:#5a4a1f;color:var(--amber-dim)}
  .result-item{background:#0e0901;border:1px solid var(--line);padding:8px 12px;margin:5px 0;
    display:flex;justify-content:space-between;gap:12px;align-items:flex-start}
  .result-item .tt{font-size:15px;color:var(--amber-bright)}
  .result-item .uu{font-size:12.5px;color:var(--amber-dim);word-break:break-all}
  .result-item .ss{font-size:13px;color:var(--mut);margin-top:2px}
  .result-item a.go{color:#0a0600;background:var(--amber);text-decoration:none;font-size:13px;
    white-space:nowrap;padding:3px 10px;font-weight:700;text-shadow:none}
  .result-item a.go:hover{box-shadow:0 0 10px #ffb000aa}
  .tgcard{display:flex;gap:14px;align-items:center;background:#0e0901;border:1px solid var(--line);padding:13px}
  .tgcard img{width:64px;height:64px;object-fit:cover;background:#1a1200;border:1px solid var(--line);
    filter:sepia(.7) hue-rotate(-12deg) saturate(1.3)}
  .tgcard .n{font-size:18px;color:var(--amber-bright)}
  .tgcard .b{font-size:13px;color:var(--mut);margin-top:2px}
  pre{background:#0e0901;border:1px solid var(--line);padding:12px;overflow:auto;font-size:13px;
    max-height:480px;white-space:pre-wrap;word-break:break-word;color:var(--amber-dim);font-family:inherit}
  .spin{width:13px;height:13px;border:2px solid #ffb00033;border-top-color:var(--amber);
    border-radius:50%;display:inline-block;animation:s .7s linear infinite;vertical-align:-2px;margin-right:7px}
  @keyframes s{to{transform:rotate(360deg)}}
  .conf{display:flex;align-items:center;gap:14px}
  .conf .bar{flex:1;height:12px;background:#1a1200;border:1px solid var(--line);overflow:hidden}
  .conf .fill{height:100%;background:repeating-linear-gradient(90deg,var(--amber) 0,var(--amber) 4px,#7a5200 4px,#7a5200 6px)}
  .conf .num{font-size:28px;color:var(--amber-bright)}
  .toolgrid{display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:8px;max-width:1020px;margin-top:14px}
  .toolcard{background:var(--card);border:1px solid var(--line);padding:12px;cursor:pointer;
    box-shadow:0 0 12px #ffb00012}
  .toolcard:hover{border-color:var(--amber);box-shadow:0 0 14px #ffb00044}
  .toolcard .t{font-size:15px;color:var(--amber-bright);margin-bottom:2px}
  .toolcard .t::before{content:"$ "}
  .toolcard .d{font-size:12.5px;color:var(--mut)}
  .note{font-size:13px;color:var(--warn);background:#1a1200;border:1px solid #5a4a1f;padding:9px 12px;margin-top:12px}
  .sec-label{font-size:13px;color:var(--mut);text-transform:uppercase;letter-spacing:2px;margin:22px 0 8px}
  .sec-label::before{content:"── "}
</style>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=VT323&family=Share+Tech+Mono&display=swap" rel="stylesheet">
</head>
<body>
<header>
  <h1>OSINT CONSOLE</h1>
  <div class="tabs">
    <div class="tab active" data-view="phone">Phone OSINT</div>
    <div class="tab" data-view="tools">Tools</div>
  </div>
  <div class="spacer"></div>
  <button class="btn" id="btn-phosphor" title="switch phosphor color">◧ GREEN</button>
  <button class="btn" id="btn-sound" title="beep on/off">♪ SOUND</button>
  <button class="btn" id="btn-settings" title="API keys">⚙ KEYS</button>
  <button class="btn" onclick="location.reload()">⟳ REFRESH</button>
</header>

<!-- ===== SETTINGS MODAL ===== -->
<div id="settings-modal" style="display:none;position:fixed;inset:0;z-index:10000;background:rgba(0,0,0,.85);overflow:auto">
  <div class="card" style="max-width:640px;margin:60px auto;position:relative">
    <h3>API Keys / Settings</h3>
    <p style="color:var(--mut);font-size:13px;margin:0 0 14px">
      Leave empty = no change. Fill in then SAVE. Stored in <code>config_keys.json</code>.
    </p>
    <div id="settings-fields"></div>
    <div style="margin-top:16px;display:flex;gap:10px;flex-wrap:wrap">
      <button class="btn acc" id="btn-save-keys">SAVE</button>
      <button class="btn" id="btn-close-settings">CLOSE</button>
      <span id="settings-msg" style="align-self:center;font-size:14px"></span>
    </div>
  </div>
</div>

<!-- ===== PHONE OSINT ===== -->
<div class="view active" id="view-phone">
  <div class="pane">
    <div class="search">
      <input type="tel" id="num" class="grow" placeholder="08xxxxxxxxxx" value="">
      <button class="btn acc" id="go">Resolve Number</button>
    </div>
    <div class="note" id="cfg-note" style="display:none"></div>
    <div class="card" id="osint-result" style="display:none"></div>
  </div>
</div>

<!-- ===== TOOLS ===== -->
<div class="view" id="view-tools">
  <div class="pane">
    <div class="search">
      <select id="toolsel">
        <option value="ip">IP Geolocation</option>
        <option value="ipintel">IP Intel (Shodan InternetDB/IPinfo/GreyNoise)</option>
        <option value="dev">Dev Profiles (GitHub/GitLab/PyPI/npm/SO/Keybase/HN/Mastodon/DockerHub)</option>
        <option value="social">Social Profiles via Jina (IG/FB/X/TikTok/LinkedIn/Threads/Snap/YT/Pinterest/Reddit/Twitch/Medium/GitHub)</option>
        <option value="username">Username Check (multi-platform)</option>
        <option value="github">GitHub Lookup (repos + commit emails)</option>
        <option value="emailintel">Email Intel (Gravatar/PGP/Hudson Rock/HIBP)</option>
        <option value="leakcheck">Breach/Leak (LeakCheck public + HIBP)</option>
        <option value="business">Business Registry (GLEIF/SEC EDGAR/AHU)</option>
        <option value="email">Email Lookup (gravatar/domain)</option>
        <option value="whois">Domain WHOIS</option>
        <option value="dns">DNS Records</option>
        <option value="subdomain">Subdomain Enum</option>
        <option value="revimg">Reverse Image Links</option>
      </select>
      <input type="text" id="toolval" class="grow" placeholder="value (IP / username / domain / email / name)">
      <button class="btn acc" id="toolgo">Run</button>
    </div>
    <div class="card" id="tool-result" style="display:none"></div>
    <div class="sec-label">Quick Examples</div>
    <div class="toolgrid">
      <div class="toolcard" data-tool="ipintel" data-v="1.1.1.1"><div class="t">IP Intel 1.1.1.1</div><div class="d">shodan+greynoise</div></div>
      <div class="toolcard" data-tool="dev" data-v="torvalds"><div class="t">Dev: torvalds</div><div class="d">12 source</div></div>
      <div class="toolcard" data-tool="social" data-v="nasa"><div class="t">Social: nasa</div><div class="d">Jina scrape</div></div>
      <div class="toolcard" data-tool="username" data-v="torvalds"><div class="t">Username torvalds</div><div class="d">multi-platform</div></div>
      <div class="toolcard" data-tool="emailintel" data-v="test@gmail.com"><div class="t">Email Intel</div><div class="d">breach + gravatar</div></div>
      <div class="toolcard" data-tool="leakcheck" data-v="torvalds"><div class="t">Leak: torvalds</div><div class="d">breach lookup</div></div>
      <div class="toolcard" data-tool="business" data-v="tesla"><div class="t">Business: tesla</div><div class="d">GLEIF+SEC</div></div>
      <div class="toolcard" data-tool="whois" data-v="example.com"><div class="t">WHOIS example.com</div><div class="d">domain info</div></div>
      <div class="toolcard" data-tool="ip" data-v="1.1.1.1"><div class="t">IP Geo 1.1.1.1</div><div class="d">geo lookup</div></div>
      <div class="toolcard" data-tool="revimg" data-v="https://i.imgur.com/EJbC0Iw.jpg"><div class="t">Reverse Image</div><div class="d">6 engine</div></div>
    </div>
  </div>
</div>

<script>
// ===== CRT: boot sequence, phosphor toggle, sound, settings =====
(function(){
  const root = document.documentElement;
  // --- boot sequence ---
  const boot = document.createElement('div');
  boot.id = 'crt-boot';
  boot.style.cssText = 'position:fixed;inset:0;z-index:99999;background:#000;color:var(--amber);'+
    'font-family:inherit;font-size:16px;padding:32px;white-space:pre-wrap;overflow:hidden;'+
    'text-shadow:0 0 2px #ffb00099,0 0 8px #ffb00040';
  const lines = [
    'OSINT CONSOLE BIOS v2.6 — AMBER CRT',
    'CPU: PY-NIKA @ 3.13GHz  ................ OK',
    'MEM: 640K BASE / 65536K EXT ........... OK',
    'DETECTING SOURCES:',
    '  [telegram] [shodan] [leakcheck] [gleif]',
    '  [github] [hudson-rock] [jina] [dns] ... OK',
    'MOUNTING /osint/modules ................ OK',
    'LOADING DASHBOARD . . .',
    '',
    'READY.',
  ];
  document.body.appendChild(boot);
  let li = 0, ci = 0, text = '';
  function type(){
    if (li >= lines.length){ setTimeout(()=>{ boot.style.transition='opacity .5s'; boot.style.opacity='0'; setTimeout(()=>boot.remove(),500); }, 300); return; }
    const cur = lines[li];
    if (ci < cur.length){ text += cur[ci++]; }
    else { text += '\n'; li++; ci = 0; }
    boot.textContent = text + '█';
    setTimeout(type, ci === 0 ? 90 : 8);
  }
  type();

  // --- sound ---
  let soundOn = false;
  let actx = null;
  function beep(freq, dur){
    if (!soundOn) return;
    try{
      actx = actx || new (window.AudioContext||window.webkitAudioContext)();
      const o = actx.createOscillator(), g = actx.createGain();
      o.type='square'; o.frequency.value=freq;
      g.gain.value=0.03;
      o.connect(g); g.connect(actx.destination);
      o.start(); o.stop(actx.currentTime + (dur||0.06));
    }catch(e){}
  }
  window.__beep = beep;
  document.getElementById('btn-sound').addEventListener('click', function(){
    soundOn = !soundOn;
    this.textContent = soundOn ? '♪ SOUND ON' : '♪ SOUND';
    this.style.color = soundOn ? 'var(--green)' : '';
    beep(soundOn?880:220, 0.08);
  });

  // --- phosphor toggle (amber <-> green) ---
  const amber = {'--amber':'#ffb000','--amber-bright':'#ffd066','--amber-dim':'#8a6410','--line':'#3a2a08','--card':'#120c02','--bg':'#0a0600'};
  const green = {'--amber':'#33ff66','--amber-bright':'#99ffbb','--amber-dim':'#1f7a3a','--line':'#0a3a18','--card':'#021206','--bg':'#000a02'};
  let phosphor = 'amber';
  document.getElementById('btn-phosphor').addEventListener('click', function(){
    phosphor = phosphor === 'amber' ? 'green' : 'amber';
    const pal = phosphor === 'green' ? green : amber;
    for (const [k,v] of Object.entries(pal)) root.style.setProperty(k,v);
    // update text-shadow glow
    document.body.style.textShadow = phosphor==='green'
      ? '0 0 2px #33ff6699, 0 0 8px #33ff6640'
      : '0 0 2px #ffb00099, 0 0 8px #ffb00040';
    this.textContent = phosphor === 'green' ? '◧ AMBER' : '◧ GREEN';
    beep(phosphor==='green'?660:440, 0.05);
  });

  // --- settings ---
  const FIELD_DEFS = [
    ['truecaller_cookie','Truecaller cookie','name=value; ...', true],
    ['serpapi_key','SerpAPI key','search engine', false],
    ['searxng_instance','SearXNG instance','https://...', false],
    ['shodan_key','Shodan API key','ipintel', false],
    ['abuseipdb_key','AbuseIPDB key','ipintel', false],
    ['censys_id','Censys API ID','ipintel', false],
    ['censys_secret','Censys secret','ipintel', false],
    ['hibp_key','HIBP key','breach', false],
    ['leakcheck_key','LeakCheck key','breach full', false],
    ['snusbase_key','Snusbase key','breach', false],
    ['dehashed_key','DeHashed key','email:key', false],
    ['rapidapi_key','RapidAPI key','BreachDirectory', false],
    ['emailrep_key','EmailRep key','email', false],
    ['opencorp_token','OpenCorporates token','business', false],
    ['ch_key','Companies House key','business UK', false],
  ];
  const modal = document.getElementById('settings-modal');
  const fields = document.getElementById('settings-fields');
  const msg = document.getElementById('settings-msg');

  document.getElementById('btn-settings').addEventListener('click', async function(){
    msg.textContent = '';
    fields.innerHTML = '<div><span class="spin"></span>loading status...</div>';
    modal.style.display = 'block';
    beep(600,0.05);
    let status = {};
    try { const r = await fetch('api_settings.php'); const j = await r.json(); status = j.status || {}; } catch(e){}
    let h = '<div class="grid" style="grid-template-columns:1fr">';
    FIELD_DEFS.forEach(([k,label,hint,big])=>{
      const st = status[k] || '';
      h += `<div class="field"><div class="k">${label} ${st?`<span style="color:var(--green)">[${esc(st)}]</span>`:'<span style="color:var(--mut)">[empty]</span>'}</div>`;
      h += big
        ? `<textarea data-k="${k}" placeholder="${hint}" rows="2" style="width:100%;background:#0e0901;color:var(--amber);border:1px solid var(--line);font-family:inherit;font-size:14px;padding:8px"></textarea>`
        : `<input data-k="${k}" placeholder="${hint}" style="width:100%">`;
      h += `<div style="font-size:11px;color:var(--mut);margin-top:3px">empty=no change</div></div>`;
    });
    h += '</div>';
    fields.innerHTML = h;
  });
  document.getElementById('btn-close-settings').addEventListener('click', ()=>{ modal.style.display='none'; });
  document.getElementById('btn-save-keys').addEventListener('click', async function(){
    const body = {};
    fields.querySelectorAll('[data-k]').forEach(el=>{ if(el.value.trim() !== '') body[el.dataset.k] = el.value.trim(); });
    if (!Object.keys(body).length){ msg.textContent = 'no changes'; msg.style.color='var(--warn)'; return; }
    msg.innerHTML = '<span class="spin"></span>saving...'; msg.style.color='';
    try{
      const r = await fetch('api_settings.php', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(body)});
      const j = await r.json();
      if(j.ok){ msg.textContent = 'saved: ' + (j.changed||[]).join(', '); msg.style.color='var(--green)'; beep(880,0.08); setTimeout(()=>location.reload(),1200); }
      else { msg.textContent = 'failed: ' + j.error; msg.style.color='var(--red)'; beep(200,0.15); }
    }catch(e){ msg.textContent = 'error: '+e; msg.style.color='var(--red)'; }
  });

  // beep on tab click
  document.querySelectorAll('.tab').forEach(t=>t.addEventListener('click',()=>beep(520,0.04)));
})();

// ---- Tabs ----
document.querySelectorAll('.tab').forEach(t => t.addEventListener('click', () => {
  document.querySelectorAll('.tab').forEach(x => x.classList.remove('active'));
  document.querySelectorAll('.view').forEach(x => x.classList.remove('active'));
  t.classList.add('active');
  document.getElementById('view-' + t.dataset.view).classList.add('active');
}));

// ---- helpers ----
function field(k,v){ return `<div class="field"><div class="k">${k}</div><div class="v">${(v==null||v==='')?'—':String(v).replace(/</g,'&lt;')}</div></div>`; }
function esc(s){ return String(s==null?'':s).replace(/</g,'&lt;'); }
function api(tool, val){
  const u = 'api_tools.php?tool=' + encodeURIComponent(tool) + (val!=null ? '&val=' + encodeURIComponent(val) : '');
  return fetch(u).then(r => r.json());
}

// ---- Phone OSINT (auto-resolve) ----
const btn = document.getElementById('go');
const numEl = document.getElementById('num');
const res = document.getElementById('osint-result');
const cfgNote = document.getElementById('cfg-note');

async function resolvePhone(){
  const num = numEl.value.trim();
  if(!/\d{6,}/.test(num)) return;
  res.style.display='block';
  res.innerHTML = `<h3>Processing ${esc(num)}</h3><div><span class="spin"></span>running resolvers (telegram, truecaller, pivot, search)</div>`;
  try{
    const j = await api('resolve', num);
    if(!j.ok){ res.innerHTML = `<h3>Error</h3><pre>${esc(j.error)}</pre>`; return; }
    res.innerHTML = renderPhone(j.data);
  }catch(err){ res.innerHTML = `<h3>Error</h3><pre>${esc(err)}</pre>`; }
}
btn.addEventListener('click', resolvePhone);
numEl.addEventListener('keydown', e => { if(e.key==='Enter') resolvePhone(); });

function renderPhone(d){
  const n = d.normalized; const p = d.profile || {}; const rz = p.resolved || {};
  let h = `<h3>Identity — ${esc(n.e164)}</h3><div class="grid">`;
  h += field('Operator', d.operator);
  h += field('Region (historic)', d.region);
  h += field('E.164', n.e164);
  h += field('Local', n.pretty);
  if(p.phonenumbers){
    h += field('Carrier (lib)', p.phonenumbers.carrier);
    h += field('Type', p.phonenumbers.number_type);
    h += field('Timezone', (p.phonenumbers.timezones||[]).join(', '));
    h += field('Valid', p.phonenumbers.is_valid?'yes':'no');
  }
  h += `</div>`;

  // Confidence
  if(p.confidence){
    const c = p.confidence;
    h += `<h3>Confidence</h3><div class="conf"><div class="num">${c.score}</div><div class="bar"><div class="fill" style="width:${c.score}%"></div></div><span class="badge ok">${c.level}</span></div>`;
    h += `<div style="margin-top:8px;font-size:12px;color:var(--mut)">${(c.signals||[]).map(s=>'+ '+esc(s)).join('<br>')}</div>`;
  }

  // === Telegram ===
  h += `<h3>Telegram</h3>`;
  const tg = rz.telegram && rz.telegram.data;
  if(tg){
    const byU = tg.by_username;
    const byN = tg.by_number && tg.by_number.data;
    if(byU && byU.display_name && !/Era baru mengirim pesan/.test(byU.display_name)){
      h += `<div class="tgcard"><img src="${byU.avatar||''}" onerror="this.style.visibility='hidden'"><div><div class="n">${esc(byU.display_name)}</div><div class="b">@${esc(byU.username)}</div><div class="b">${esc(byU.bio||'')}</div></div></div>`;
      h += `<div class="links"><a target="_blank" href="${byU.url}">open profile</a></div>`;
    } else {
      h += `<div class="result-item"><div><div class="tt">No direct Telegram profile</div><div class="ss">${byN&&byN.generic?'number not linked to a public account':''}</div></div><a class="go" target="_blank" href="https://t.me/+${n.intl}">check manually</a></div>`;
    }
  } else h += `<div class="empty">no data</div>`;

  // === Truecaller ===
  h += `<h3>Truecaller</h3>`;
  const tc = rz.truecaller;
  if(tc && tc.ok && tc.data){
    const t = tc.data;
    if(t.name || t.raw){
      h += `<div class="grid">`;
      if(t.name) h += field('Name', t.name);
      if(t.raw && t.raw.name) h += field('Name (raw)', t.raw.name);
      h += `</div>`;
    } else if(t.title && !/Free Reverse Phone/.test(t.title)){
      h += `<div class="grid">` + field('Info', t.title) + `</div>`;
    } else {
      h += `<div class="result-item"><div><div class="tt">Login required</div><div class="ss">set cookie in config.php to enable</div></div><a class="go" target="_blank" href="https://www.truecaller.com/search/id/${n.intl}">open Truecaller</a></div>`;
    }
  } else {
    h += `<div class="result-item"><div><div class="tt">Not enabled</div><div class="ss">${esc((tc&&tc.error)||'')}</div></div><a class="go" target="_blank" href="https://www.truecaller.com/search/id/${n.intl}">open manually</a></div>`;
  }

  // === Handle pivot ===
  h += `<h3>Number as Handle</h3>`;
  const hp = rz.handle_pivot && rz.handle_pivot.data;
  if(hp){
    const hits = hp.hits || {};
    const keys = Object.keys(hits);
    if(keys.length){
      h += `<div class="links">`;
      keys.forEach(pl => hits[pl].forEach(x => { h += `<a class="chip found" target="_blank" href="${x.url}">${pl}: ${esc(x.handle)}</a>`; }));
      h += `</div>`;
    } else {
      h += `<div class="result-item"><div><div class="tt">No matching handles</div><div class="ss">${hp.checked} checked</div></div></div>`;
    }
    if(hp.inconclusive && hp.inconclusive.length){
      h += `<div style="font-size:11.5px;color:var(--mut);margin-top:6px">needs manual check (requires login):</div><div class="links">`;
      hp.inconclusive.forEach(x => { h += `<a class="chip inc" target="_blank" href="${x.url}">${x.platform}: ${esc(x.handle)}</a>`; });
      h += `</div>`;
    }
  } else h += `<div class="empty">no data</div>`;

  // === Messaging apps ===
  h += `<h3>Messaging Apps</h3>`;
  const mg = rz.messaging && rz.messaging.data;
  if(mg){
    h += `<div class="links">`;
    for(const [k,v] of Object.entries(mg)){
      const note = v.reachable===true ? ' (reachable)' : '';
      h += `<a class="chip ${v.reachable===true?'found':''}" target="_blank" href="${v.url}">${k}${note}</a>`;
    }
    h += `</div>`;
  } else h += `<div class="empty">—</div>`;

  // === Dev profiles (when candidate usernames exist) ===
  const devKeys = Object.keys(rz).filter(k=>k.startsWith('social_'));
  if(devKeys.length){
    h += `<h3>Social (Jina)</h3>`;
    devKeys.forEach(dk=>{
      const u = dk.replace('social_','');
      const sp = rz[dk].data || rz[dk];
      if(sp && typeof sp==='object'){
        h += `<div class="sec-label">@${esc(u)}</div><div class="links">`;
        Object.entries(sp).forEach(([p,v])=>{ if(v&&v.data) h += `<a class="chip ${v.data.found?'found':'notfound'}" target="_blank" href="${v.data.url}">${p}${v.data.found?' ✓':''}</a>`; });
        h += `</div>`;
      }
    });
  }

  // === Search ===
  h += `<h3>Search</h3>`;
  const se = rz.search && rz.search.data;
  if(se && se.results && se.results.length){
    se.results.forEach(r => {
      h += `<div class="result-item"><div><div class="tt">${esc(r.title)}</div><div class="uu">${esc(r.url)}</div>${r.snippet?`<div class="ss">${esc(r.snippet)}</div>`:''}</div><a class="go" target="_blank" href="${r.url}">open</a></div>`;
    });
  } else if(se && se.google){
    h += `<div style="font-size:12px;color:var(--mut);margin-bottom:6px">Search API not configured — use direct links:</div><div class="links">`;
    for(const [k,v] of Object.entries(se)){ if(k==='query')continue; h += `<a target="_blank" href="${v}">${k}</a>`; }
    h += `</div>`;
  } else h += `<div class="empty">—</div>`;

  // === Google Dorks ===
  h += `<h3>Google Dorks</h3>`;
  (d.dorks||[]).forEach(dk => {
    h += `<div class="result-item"><div class="uu" style="color:var(--amber)">${esc(dk)}</div><a class="go" target="_blank" href="https://www.google.com/search?q=${encodeURIComponent(dk)}">search</a></div>`;
  });

  return h;
}

// ---- Tools ----
async function runTool(tool, val){
  const tr = document.getElementById('tool-result');
  tr.style.display='block';
  tr.innerHTML = `<h3>Running ${esc(tool)}...</h3><div><span class="spin"></span>working</div>`;
  try{
    const j = await api(tool, val);
    if(!j.ok){ tr.innerHTML = `<h3>Error</h3><pre>${esc((j.error||'')+'\n'+(j.raw||'')+'\n'+(j.stderr||''))}</pre>`; return; }
    tr.innerHTML = renderTool(j.tool, j.data);
  }catch(err){ tr.innerHTML = `<h3>Error</h3><pre>${esc(err)}</pre>`; }
}
document.getElementById('toolgo').addEventListener('click', () => {
  const t = document.getElementById('toolsel').value;
  const v = document.getElementById('toolval').value.trim();
  if(!v) return; runTool(t, v);
});
document.getElementById('toolval').addEventListener('keydown', e => { if(e.key==='Enter') document.getElementById('toolgo').click(); });
document.querySelectorAll('.toolcard').forEach(c => c.addEventListener('click', () => {
  document.getElementById('toolsel').value = c.dataset.tool;
  document.getElementById('toolval').value = c.dataset.v;
  runTool(c.dataset.tool, c.dataset.v);
}));

function renderTool(tool, data){
  if(tool==='ipintel' && data.ip_intel){
    const d = data.ip_intel;
    let h = `<h3>IP Intelligence</h3>`;
    const sid = d.shodan_internetdb && d.shodan_internetdb.data;
    if(sid && sid.found){
      h += `<div class="links">`;
      (sid.ports||[]).forEach(p=>{ h += `<span class="chip">port ${p}</span>`; });
      h += `</div>`;
      if(sid.hostnames && sid.hostnames.length){ h += `<h3>Hostnames</h3><div class="links">` + sid.hostnames.map(x=>`<span class="chip">${esc(x)}</span>`).join('') + `</div>`; }
      if(sid.vulns && sid.vulns.length){ h += `<h3>Vulnerabilities</h3><div class="links">` + sid.vulns.map(x=>`<a class="chip" style="background:#2a0d0d;border-color:#7a1f1f;color:#ff8a8a" target="_blank" href="https://nvd.nist.gov/vuln/detail/${esc(x)}">${esc(x)}</a>`).join('') + `</div>`; }
      if(sid.cpes && sid.cpes.length){ h += `<h3>CPE</h3><div class="links">` + sid.cpes.map(x=>`<span class="chip">${esc(x)}</span>`).join('') + `</div>`; }
    } else { h += `<div class="empty">Shodan InternetDB: no public data</div>`; }
    const ii = d.ipinfo && d.ipinfo.data;
    if(ii){ h += `<h3>IPinfo</h3><div class="grid">`; for(const [k,v] of Object.entries(ii)){ if(v!=null&&v!=='') h += field(k,v); } h += `</div>`; }
    const gn = d.greynoise && d.greynoise.data;
    if(gn){ h += `<h3>GreyNoise</h3><div class="grid">` + field('Noise (scanner)', gn.noise?'YES':'no') + field('RIOT (benign)', gn.riot?'yes':'no') + field('Classification', gn.classification) + `</div>`; }
    const ab = d.abuseipdb && d.abuseipdb.data;
    if(ab){ h += `<h3>AbuseIPDB</h3><div class="grid">` + field('Abuse score', ab.abuseConfidenceScore) + field('Total reports', ab.totalReports) + field('ISP', ab.isp) + `</div>`; }
    return h;
  }
  if(tool==='leakcheck' && data.leakcheck){
    const d = data.leakcheck;
    let h = `<h3>Breach / Leak Lookup</h3>`;
    const lc = d.leakcheck_public && d.leakcheck_public.data;
    if(lc){
      const found = lc.found || 0;
      h += `<div class="result-item"><div><div class="tt">LeakCheck (public) — ${found} results</div><div class="ss">${esc(lc.message||'')}</div></div></div>`;
      if(lc.fields && lc.fields.length){ h += `<h3>Data Fields</h3><div class="links">` + lc.fields.map(f=>`<span class="chip maybe">${esc(f)}</span>`).join('') + `</div>`; }
      if(lc.sources && lc.sources.length){ h += `<h3>Sources</h3><div class="links">` + lc.sources.map(s=>`<span class="chip">${esc(s)}</span>`).join('') + `</div>`; }
    }
    const ha = d.hibp_account;
    if(ha && ha.ok && ha.data.breaches && ha.data.breaches.length){
      h += `<h3>HIBP Breaches (${ha.data.breaches.length})</h3><div class="links">` + ha.data.breaches.map(b=>`<span class="chip maybe">${esc(b.Name||b.Title||'')}</span>`).join('') + `</div>`;
    } else if(ha && !ha.ok){ h += `<div class="sec-label">HIBP</div><div class="empty">${esc(ha.error)}</div>`; }
    ['leakcheck_api','snusbase','dehashed','breachdirectory'].forEach(k=>{
      const x = d[k];
      if(x && x.ok) h += `<div class="sec-label">${k}</div><pre>${esc(JSON.stringify(x.data,null,2).slice(0,1500))}</pre>`;
    });
    return h;
  }
  if(tool==='business' && data.business){
    const d = data.business;
    let h = `<h3>Business Registry</h3>`;
    const gl = d.gleif && d.gleif.data;
    if(gl && gl.entities && gl.entities.length){
      h += `<h3>GLEIF (LEI) — ${gl.count}</h3>`;
      gl.entities.forEach(e=>{
        h += `<div class="result-item"><div><div class="tt">${esc(e.name)}</div><div class="uu">LEI ${esc(e.lei)}</div><div class="ss">${esc(e.jurisdiction||'')} · ${esc(e.address||'')} · ${esc(e.status||'')}</div></div></div>`;
      });
    }
    const se = d.sec_edgar && d.sec_edgar.data;
    if(se && se.results && se.results.length){
      h += `<h3>SEC EDGAR (US)</h3>`;
      se.results.slice(0,8).forEach(r=>{ h += `<div class="result-item"><div><div class="tt">${esc(r.title)}</div><div class="ss">CIK ${esc(r.cik||'')}</div></div><a class="go" target="_blank" href="https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=${esc(r.cik||'')}&type=10-K">EDGAR</a></div>`; });
    }
    const ah = d.ahu_indonesia && d.ahu_indonesia.data;
    if(ah){ h += `<h3>Indonesia (AHU)</h3><div class="links">`; for(const [k,v] of Object.entries(ah.links||{})){ h += `<a target="_blank" href="${v}">${k}</a>`; } h += `</div>`; }
    const oc = d.opencorporates;
    if(oc && oc.ok && oc.data.companies) { h += `<h3>OpenCorporates — ${oc.data.count}</h3>`; oc.data.companies.slice(0,10).forEach(c=>{ h += `<div class="result-item"><div><div class="tt">${esc(c.name)}</div><div class="ss">${esc(c.jurisdiction||'')} · ${esc(c.status||'')}</div></div></div>`; }); }
    else if(oc && !oc.ok) h += `<div class="sec-label">OpenCorporates</div><div class="empty">${esc(oc.error)}</div>`;
    const ch = d.companies_house;
    if(ch && ch.ok && ch.data.companies){ h += `<h3>UK Companies House — ${ch.data.count}</h3>`; ch.data.companies.slice(0,10).forEach(c=>{ h += `<div class="result-item"><div><div class="tt">${esc(c.title)}</div><div class="ss">${esc(c.number||'')} · ${esc(c.status||'')} · ${esc(c.address||'')}</div></div></div>`; }); }
    else if(ch && !ch.ok) h += `<div class="sec-label">Companies House</div><div class="empty">${esc(ch.error)}</div>`;
    return h;
  }
  if(tool==='dev' && data.dev_profiles){
    const d = data.dev_profiles;
    const found = Object.entries(d).filter(([k,v])=>v.found);
    let h = `<h3>Dev Profiles — ${found.length} found</h3><div class="links">`;
    Object.entries(d).forEach(([k,v])=>{ h += `<span class="chip ${v.found?'found':'notfound'}">${k}${v.found?' ✓':''}</span>`; });
    h += `</div>`;
    found.forEach(([k,v])=>{
      h += `<h3>${k}</h3><div class="grid">`;
      const dd = v.data || {};
      for(const [kk,vv] of Object.entries(dd)){
        if(vv==null||vv===''||(Array.isArray(vv)&&!vv.length))continue;
        h += field(kk, Array.isArray(vv)?vv.map(x=>typeof x==='object'?JSON.stringify(x):x).join(', '):(typeof vv==='object'?JSON.stringify(vv):vv));
      }
      h += `</div>`;
    });
    return h;
  }
  if(tool==='social' && data.social_profiles){
    const d = data.social_profiles;
    const sm = d._summary || {};
    let h = `<h3>Social Profiles — @${esc(sm.username||'')}</h3>`;
    h += `<div class="grid">`;
    h += field('Found', (sm.found||[]).join(', ') || '—');
    h += field('Likely', (sm.probable||[]).join(', ') || '—');
    h += field('Blocked/login', (sm.blocked||[]).join(', ') || '—');
    h += field('Checked', sm.total_checked || 0);
    h += `</div>`;
    Object.entries(d).forEach(([k,v])=>{
      if(k==='_summary' || !v.data) return;
      const dd = v.data;
      const st = dd.status || (dd.found?'found':'unknown');
      const badgeCls = st==='found'?'found':(st==='probable'?'maybe':(st==='blocked'?'inc':'notfound'));
      h += `<h3>${k} <span class="chip ${badgeCls}" style="font-size:11px">${esc(st)}${dd.confidence!=null?(' · '+dd.confidence+'%'):''}</span></h3>`;
      h += `<div class="grid">`;
      if(dd.display_name) h += field('Name', dd.display_name);
      if(dd.bio) h += field('Bio', dd.bio);
      if(dd.signals) h += field('Signals', dd.signals.join(', '));
      if(dd.reason) h += field('Note', dd.reason);
      h += `</div>`;
      if(dd.url) h += `<div class="links"><a target="_blank" href="${dd.url}">open ${k}</a></div>`;
    });
    return h;
  }
  if(tool==='emailintel' && data.email_intel){
    const d = data.email_intel;
    let h = `<h3>Email Intelligence</h3>`;
    // Hudson Rock (most important)
    const hr = d.hudson_rock;
    if(hr && hr.ok){
      const infected = hr.data.infected;
      h += `<div class="result-item"><div><div class="tt">Hudson Rock — Info Stealer</div><div class="ss" style="color:${infected?'#ff5b3d':'var(--ok)'}">${infected?'INFECTED with info-stealer!':'clean'}</div></div></div>`;
      if(infected && hr.data.stealers){
        h += `<div class="links">`;
        hr.data.stealers.forEach(s=>{ h += `<span class="chip" style="background:#3a1a1a;border-color:#6b1f1f;color:#ff8a8a">${esc(s.computer||'PC')} · ${esc(s.date||'')} · ${esc(s.ip||'')}</span>`; });
        h += `</div>`;
      }
    }
    // Gravatar
    const gv = d.gravatar;
    if(gv && gv.ok && gv.data.found){
      h += `<h3>Gravatar</h3><div class="grid">` + field('Name', gv.data.display_name) + field('About', gv.data.about) + `</div>`;
      if(gv.data.accounts && gv.data.accounts.length){
        h += `<div class="links">`;
        gv.data.accounts.forEach(a=>{ h += `<a class="chip found" target="_blank" href="${a.url}">${esc(a.shortname)}: ${esc(a.username||'')}</a>`; });
        h += `</div>`;
      }
    }
    // PGP
    const pgp = d.pgp;
    if(pgp && pgp.ok && pgp.data.keys && pgp.data.keys.length){
      h += `<h3>PGP</h3><div class="links">`;
      pgp.data.keys.forEach(k=>{ h += `<span class="chip found">${esc(k.server)}</span>`; });
      h += `</div>`;
    }
    // HIBP
    const hibp = d.hibp;
    if(hibp && hibp.ok && hibp.data.breaches && hibp.data.breaches.length){
      h += `<h3>HIBP Breaches (${hibp.data.breaches.length})</h3><div class="links">`;
      hibp.data.breaches.forEach(b=>{ h += `<span class="chip maybe">${esc(b.Name||b.Title||'')}</span>`; });
      h += `</div>`;
    } else if(hibp && !hibp.ok){
      h += `<div class="sec-label">HIBP</div><div class="empty">${esc(hibp.error)}</div>`;
    }
    return h || `<div class="empty">no data</div>`;
  }
  if(tool==='ip' && data.ip_geo){
    const g = data.ip_geo; let h = `<h3>IP Geolocation</h3><div class="grid">`;
    if(g.raw){ for(const [k,v] of Object.entries(g.raw)) h += field(k, v); } else { h += field('Error', g.error); }
    h += `</div>`;
    if(g.lat && g.lon) h += `<div class="links"><a target="_blank" href="https://www.google.com/maps?q=${g.lat},${g.lon}">Google Maps (${g.lat}, ${g.lon})</a></div>`;
    return h;
  }
  if(tool==='username' && data.username){
    const d = data.username.data; let h = `<h3>Username Check</h3><div class="links">`;
    for(const [pl, info] of Object.entries(d)){
      const st = info.status || '';
      const cls = st==='found'?'found':(st==='not found'?'notfound':(st==='maybe'?'maybe':''));
      h += `<a class="chip ${cls}" target="_blank" href="${info.url}">${pl} — ${esc(st)}</a>`;
    }
    return h + `</div>`;
  }
  if(tool==='github' && data.github){
    const g = data.github;
    if(!g.ok) return `<h3>GitHub</h3><pre>${esc(g.error)}</pre>`;
    const d = g.data; let h = `<h3>GitHub — ${esc(d.login)}</h3><div class="grid">`;
    h += field('Name', d.name); h += field('Location', d.location); h += field('Company', d.company);
    h += field('Email', d.email); h += field('Blog', d.blog); h += field('Twitter', d.twitter);
    h += field('Public Repos', d.public_repos); h += field('Followers', d.followers); h += field('Created', d.created);
    h += `</div>`;
    if(d.commit_emails && d.commit_emails.length) h += `<h3>Commit Emails</h3><div class="links">` + d.commit_emails.map(e=>`<span class="chip">${esc(e)}</span>`).join('') + `</div>`;
    if(d.repos && d.repos.length){ h += `<h3>Repos</h3>`; d.repos.slice(0,12).forEach(r=>{ h += `<div class="result-item"><div><div class="tt">${esc(r.name)} ${r.lang?('· '+esc(r.lang)):''} ★${r.stars||0}</div></div><a class="go" target="_blank" href="${r.url}">open</a></div>`; }); }
    return h;
  }
  if(tool==='email' && data.email){
    const e2 = data.email.data || data.email; let h = `<h3>Email Lookup</h3><div class="grid">`;
    h += field('Domain', e2.domain); h += field('Disposable', e2.is_disposable?'yes':'no'); h += field('Free mail', e2.is_free?'yes':'no');
    h += `</div>`;
    if(e2.gravatar){
      h += `<h3>Gravatar</h3><div class="grid">` + field('Display name', e2.gravatar.display_name) + field('Name', e2.gravatar.name) + field('About', e2.gravatar.about) + `</div>`;
      if(e2.gravatar.profile_url) h += `<div class="links"><a target="_blank" href="${e2.gravatar.profile_url}">Gravatar Profile</a></div>`;
      if(e2.gravatar.accounts && e2.gravatar.accounts.length){
        h += `<h3>Linked Accounts</h3><div class="links">`;
        e2.gravatar.accounts.forEach(a=>{ h += `<a class="chip found" target="_blank" href="${a.url}">${esc(a.shortname)}: ${esc(a.username||'')}</a>`; });
        h += `</div>`;
      }
    } else h += `<h3>Gravatar</h3><div class="empty">none</div>`;
    return h;
  }
  if(tool==='whois' && data.whois){
    const w = data.whois; if(!w.ok) return `<h3>WHOIS</h3><pre>${esc(w.error)}</pre>`;
    const d = w.data; let h = `<h3>WHOIS — ${esc(d.domain_name||'')}</h3><div class="grid">`;
    for(const [k,v] of Object.entries(d)){ if(v==null||v===''||(Array.isArray(v)&&!v.length))continue; h += field(k, Array.isArray(v)?v.join(', '):v); }
    return h + `</div>`;
  }
  if(tool==='dns' && data.dns){
    const d = data.dns.data; let h = `<h3>DNS Records</h3>`;
    for(const [t, vals] of Object.entries(d)){
      h += `<h4 style="color:var(--mut);margin:12px 0 4px;font-size:12px">${t}</h4><div class="links">` + (vals.length? vals.map(v=>`<span class="chip">${esc(v)}</span>`).join('') : '<span class="empty">—</span>') + `</div>`;
    }
    return h;
  }
  if(tool==='subdomain' && data.subdomains){
    const d = data.subdomains.data; const keys = Object.keys(d); let h = `<h3>Subdomains (${keys.length})</h3><div class="links">`;
    keys.forEach(k=>{ h += `<a class="chip found" target="_blank" href="https://${k}">${esc(k)}</a>`; });
    return h + `</div>`;
  }
  if(tool==='revimg' && data.reverse_image){
    const d = data.reverse_image.data; let h = `<h3>Reverse Image</h3><div class="links">`;
    for(const [k,v] of Object.entries(d)){ if(k==='image_url')continue; h += `<a target="_blank" href="${v}">${esc(k)}</a>`; }
    return h + `</div>`;
  }
  return `<h3>Result</h3><pre>${esc(JSON.stringify(data,null,2))}</pre>`;
}
</script>
</body>
</html>
