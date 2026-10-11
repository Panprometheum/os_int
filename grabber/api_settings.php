<?php
// osint/grabber/api_settings.php
// Simpan / baca API keys ke config_keys.json (dipakai Settings panel dashboard).

header('Content-Type: application/json');

$keysFile = __DIR__ . '/config_keys.json';

// daftar key yang boleh disimpan (whitelist)
$allowed = [
    'truecaller_cookie','serpapi_key','searxng_instance',
    'shodan_key','abuseipdb_key','censys_id','censys_secret',
    'hibp_key','leakcheck_key','snusbase_key','dehashed_key','rapidapi_key','emailrep_key',
    'opencorp_token','ch_key','tg_bot_token','tg_chat_id',
];

$method = $_SERVER['REQUEST_METHOD'] ?? 'GET';

// Guard: tulis key hanya dari localhost, kecuali diizinkan eksplisit di config.
// (Mencegah orang asing menimpa API key kalau dashboard di-expose publik.)
$cfg = is_file(__DIR__ . '/config.php') ? (require __DIR__ . '/config.php') : [];
$remote = $_SERVER['REMOTE_ADDR'] ?? '';
$local = in_array($remote, ['127.0.0.1', '::1', '::ffff:127.0.0.1'], true);
if ($method === 'POST' && !$local && empty($cfg['allow_remote_settings'])) {
    http_response_code(403);
    echo json_encode(['ok' => false, 'error' => 'POST settings hanya dari localhost (atau set allow_remote_settings=true di config.php)']);
    exit;
}

function load($file) {
    if (!is_file($file)) return [];
    $j = json_decode(file_get_contents($file), true);
    return is_array($j) ? $j : [];
}

if ($method === 'GET') {
    $saved = load($keysFile);
    // status: key apa yang sudah terisi (mask)
    $status = [];
    foreach ($allowed as $k) {
        $v = $saved[$k] ?? '';
        $status[$k] = $v === '' ? '' : (strlen($v) > 8 ? substr($v, 0, 4) . '…' . substr($v, -3) : '•••');
    }
    echo json_encode(['ok' => true, 'status' => $status]);
    exit;
}

if ($method === 'POST') {
    $input = json_decode(file_get_contents('php://input'), true);
    if (!is_array($input)) {
        echo json_encode(['ok' => false, 'error' => 'body bukan JSON']);
        exit;
    }
    $saved = load($keysFile);
    $changed = [];
    foreach ($input as $k => $v) {
        if (!in_array($k, $allowed, true)) continue;
        if ($v === '__CLEAR__') { unset($saved[$k]); $changed[] = $k . ' (dihapus)'; continue; }
        if ($v !== '' && $v !== null) { $saved[$k] = $v; $changed[] = $k; }
    }
    // proteksi file
    if (@file_put_contents($keysFile, json_encode($saved, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES), LOCK_EX) === false) {
        echo json_encode(['ok' => false, 'error' => 'gagal menulis config_keys.json (cek permission)']);
        exit;
    }
    @chmod($keysFile, 0600);
    echo json_encode(['ok' => true, 'changed' => $changed]);
    exit;
}

echo json_encode(['ok' => false, 'error' => 'method tidak didukung']);
