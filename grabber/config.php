<?php
// grabber/config.php
// Resolver + API key configuration.
// Editable manually OR via the dashboard Settings panel (stored in config_keys.json).

$cfg = [
    // === Resolvers (number -> social accounts) ===
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

    // === Dashboard security ===
    // Settings panel (saves API keys) only accepts POST from localhost.
    // Set true if the dashboard is publicly hosted + already protected (auth/reverse-proxy).
    'allow_remote_settings' => false,
];

// Override from config_keys.json (Settings panel) if present
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
