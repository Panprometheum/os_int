<?php
// osint/grabber/api_settings.php
// Save / read API keys to config_keys.json (used by the dashboard Settings panel).

header('Content-Type: application/json');

$keysFile = __DIR__ . '/config_keys.json';

// keys allowed to be stored (whitelist)
$allowed = [
    'truecaller_cookie','serpapi_key','searxng_instance',
    'shodan_key','abuseipdb_key','censys_id','censys_secret',
    'hibp_key','leakcheck_key','snusbase_key','dehashed_key','rapidapi_key','emailrep_key',
    'opencorp_token','ch_key',
];

$method = $_SERVER['REQUEST_METHOD'] ?? 'GET';

// Guard: keys can only be written from localhost unless explicitly allowed in config.
// (Prevents strangers from overwriting API keys if the dashboard is publicly exposed.)
$cfg = is_file(__DIR__ . '/config.php') ? (require __DIR__ . '/config.php') : [];
$remote = $_SERVER['REMOTE_ADDR'] ?? '';
$local = in_array($remote, ['127.0.0.1', '::1', '::ffff:127.0.0.1'], true);
if ($method === 'POST' && !$local && empty($cfg['allow_remote_settings'])) {
    http_response_code(403);
    echo json_encode(['ok' => false, 'error' => 'Settings POST only allowed from localhost (or set allow_remote_settings=true in config.php)']);
    exit;
}

function load($file) {
    if (!is_file($file)) return [];
    $j = json_decode(file_get_contents($file), true);
    return is_array($j) ? $j : [];
}

if ($method === 'GET') {
    $saved = load($keysFile);
    // status: which keys are already set (masked)
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
        echo json_encode(['ok' => false, 'error' => 'body is not JSON']);
        exit;
    }
    $saved = load($keysFile);
    $changed = [];
    foreach ($input as $k => $v) {
        if (!in_array($k, $allowed, true)) continue;
        if ($v === '__CLEAR__') { unset($saved[$k]); $changed[] = $k . ' (cleared)'; continue; }
        if ($v !== '' && $v !== null) { $saved[$k] = $v; $changed[] = $k; }
    }
    // protect the file
    if (@file_put_contents($keysFile, json_encode($saved, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES), LOCK_EX) === false) {
        echo json_encode(['ok' => false, 'error' => 'failed to write config_keys.json (check permissions)']);
        exit;
    }
    @chmod($keysFile, 0600);
    echo json_encode(['ok' => true, 'changed' => $changed]);
    exit;
}

echo json_encode(['ok' => false, 'error' => 'method not supported']);
