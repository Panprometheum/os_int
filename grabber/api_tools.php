<?php
// osint/grabber/api_tools.php
// API bridge: panggil osint_phone.py untuk semua tool + resolve.

header('Content-Type: application/json');

$cfg = require __DIR__ . '/config.php';

$script = realpath(__DIR__ . '/../osint_phone.py');
if ($script === false) {
    echo json_encode(['ok' => false, 'error' => 'osint_phone.py tidak ditemukan']);
    exit;
}
$python = 'python';

function run_py($python, $script, array $args) {
    $cmd = escapeshellarg($python) . ' ' . escapeshellarg($script);
    foreach ($args as $a) $cmd .= ' ' . escapeshellarg($a);
    $proc = @proc_open($cmd, [1 => ['pipe', 'w'], 2 => ['pipe', 'w']], $pipes);
    if (!is_resource($proc)) return [null, 'proc_open gagal'];
    $out = stream_get_contents($pipes[1]);
    $err = stream_get_contents($pipes[2]);
    fclose($pipes[1]); fclose($pipes[2]);
    $code = proc_close($proc);
    return [$out, $err . ($code !== 0 ? " (exit $code)" : '')];
}

$tool = $_GET['tool'] ?? '';
$val  = $_GET['val'] ?? '';

$map = [
    'lookup'    => ['--json'],
    'resolve'   => ['--resolve', '--json'],
    'ip'        => ['--ip',     $val, '--json'],
    'ipintel'   => ['--ipintel', $val, '--json'],
    'username'  => ['--username', $val, '--json'],
    'github'    => ['--github', $val, '--json'],
    'dev'       => ['--dev',    $val, '--json'],
    'social'    => ['--social', $val, '--json'],
    'emailintel'=> ['--email-intel', $val, '--json'],
    'leakcheck' => ['--leakcheck', $val, '--json'],
    'business'  => ['--business', $val, '--json'],
    'email'     => ['--email',  $val, '--json'],
    'whois'     => ['--whois',  $val, '--json'],
    'dns'       => ['--whois',  $val, '--dns', '--json'],
    'subdomain' => ['--subdomain', $val, '--json'],
    'revimg'    => ['--reverse-image', $val, '--json'],
];

// helper: tambah pasangan --flag value kalau key terisi
function add_key(array &$args, array $cfg, string $flag, string $key) {
    if (!empty($cfg[$key])) { $args[] = $flag; $args[] = $cfg[$key]; }
}

if ($tool === 'lookup' || $tool === 'resolve') {
    if (!preg_match('/\d{6,15}/', $val)) { echo json_encode(['ok'=>false,'error'=>'Nomor tidak valid']); exit; }
    if ($tool === 'lookup') {
        $map['lookup'] = [$val, '--json'];
    } else {
        $args = [$val, '--resolve', '--json'];
        add_key($args, $cfg, '--truecaller-cookie', 'truecaller_cookie');
        add_key($args, $cfg, '--serpapi-key', 'serpapi_key');
        add_key($args, $cfg, '--searxng', 'searxng_instance');
        add_key($args, $cfg, '--hibp-key', 'hibp_key');
        $map['resolve'] = $args;
    }
}

// key untuk tool spesifik
if ($tool === 'ipintel') {
    $args = ['--ipintel', $val, '--json'];
    add_key($args, $cfg, '--shodan-key', 'shodan_key');
    add_key($args, $cfg, '--abuseipdb-key', 'abuseipdb_key');
    add_key($args, $cfg, '--censys-id', 'censys_id');
    add_key($args, $cfg, '--censys-secret', 'censys_secret');
    $map['ipintel'] = $args;
}
if ($tool === 'leakcheck') {
    $args = ['--leakcheck', $val, '--json'];
    add_key($args, $cfg, '--leakcheck-key', 'leakcheck_key');
    add_key($args, $cfg, '--hibp-key', 'hibp_key');
    add_key($args, $cfg, '--snusbase-key', 'snusbase_key');
    add_key($args, $cfg, '--dehashed-key', 'dehashed_key');
    add_key($args, $cfg, '--rapidapi-key', 'rapidapi_key');
    $map['leakcheck'] = $args;
}
if ($tool === 'business') {
    $args = ['--business', $val, '--json'];
    add_key($args, $cfg, '--opencorp-token', 'opencorp_token');
    add_key($args, $cfg, '--ch-key', 'ch_key');
    $map['business'] = $args;
}
if ($tool === 'emailintel') {
    $args = ['--email-intel', $val, '--json'];
    add_key($args, $cfg, '--hibp-key', 'hibp_key');
    add_key($args, $cfg, '--emailrep-key', 'emailrep_key');
    $map['emailintel'] = $args;
}

if (!isset($map[$tool])) {
    echo json_encode(['ok' => false, 'error' => 'tool tidak dikenal: ' . $tool]);
    exit;
}

[$out, $err] = run_py($python, $script, $map[$tool]);
$out = trim($out ?? '');
// sanitasi: buang byte UTF-8 invalid biar json_decode + json_encode gak gagal
$out = mb_convert_encoding($out, 'UTF-8', 'UTF-8');
$j = json_decode($out, true);
if (is_array($j)) {
    echo json_encode(['ok' => true, 'tool' => $tool, 'data' => $j], JSON_INVALID_UTF8_SUBSTITUTE | JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
} else {
    echo json_encode(['ok' => false, 'tool' => $tool, 'error' => 'parse gagal: ' . json_last_error_msg(),
                      'raw' => substr($out, 0, 500), 'stderr' => $err], JSON_INVALID_UTF8_SUBSTITUTE);
}
