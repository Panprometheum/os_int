<?php
// grabber/config.php
// Konfigurasi grabber + resolvers + API keys.
// Bisa diedit manual ATAU lewat Settings panel di dashboard (tersimpan di config_keys.json).

$cfg = [
    // === Grabber ===
    'title'      => 'Cek Kuota & Paket Data',
    'subtitle'   => 'Masukkan nomor untuk mengecek sisa kuota Anda',
    'redirect'   => 'https://www.indosat.com/',
    'log_dir'    => __DIR__ . '/logs',
    'geo_api'    => 'http://ip-api.com/json/',
    'tg_bot_token' => '',
    'tg_chat_id'   => '',

    // === Resolvers (nomor -> akun medsos) ===
    'truecaller_cookie' => '',
    'serpapi_key'       => '',
    'searxng_instance'  => '',

    // === IP Intel ===
    'shodan_key'        => '',
    'abuseipdb_key'     => '',
    'censys_id'         => '',
    'censys_secret'     => '',

    // === Breach / Leak ===
    'hibp_key'          => '',
    'leakcheck_key'     => '',
    'snusbase_key'      => '',
    'dehashed_key'      => '',   // format: email:apikey
    'rapidapi_key'      => '',
    'emailrep_key'      => '',

    // === Business Registry ===
    'opencorp_token'    => '',
    'ch_key'            => '',   // UK Companies House

    // === Keamanan dashboard ===
    // Settings panel (simpan API key) hanya bisa POST dari localhost.
    // Set true kalau dashboard di-hosting publik + sudah diproteksi (auth/reverse-proxy).
    'allow_remote_settings' => false,
];

// Override dari config_keys.json (Settings panel) kalau ada
$keysFile = __DIR__ . '/config_keys.json';
if (is_file($keysFile)) {
    $saved = json_decode(file_get_contents($keysFile), true);
    if (is_array($saved)) {
        foreach ($saved as $k => $v) {
            if ($v !== '' && $v !== null) $cfg[$k] = $v;
        }
    }
}

return $cfg;
