<?php
// This file is automatically prepended to all PHP requests for phpMyAdmin
// It ensures that the session name is consistent across all scripts.

$sessionName = 'SanguoPMA';
// file_put_contents(__DIR__ . '/pma_sso.log', "[" . date('Y-m-d H:i:s') . "] pre-config.php running for: " . $_SERVER['REQUEST_URI'] . "\n", FILE_APPEND);

ini_set('session.name', $sessionName);
if (!headers_sent()) {
    session_name($sessionName);
    
    // Ensure session path is also consistent
    $sessionPath = __DIR__ . '/sessions';
    if (!is_dir($sessionPath)) {
        @mkdir($sessionPath, 0777, true);
    }
    ini_set('session.save_path', $sessionPath);
    session_save_path($sessionPath);

    // Set cookie parameters for the proxy environment
    session_set_cookie_params([
        'lifetime' => 0,
        'path' => '/', 
        'domain' => '',
        'secure' => false,
        'httponly' => true,
        'samesite' => 'Lax'
    ]);
}
