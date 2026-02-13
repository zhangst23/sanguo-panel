<?php
/**
 * phpMyAdmin SSO (Single Sign-On) Script
 * This script integrates with the Sanguo Panel backend to verify tokens
 */

if (session_status() === PHP_SESSION_NONE) {
     session_name('PMA_SSO');
     // Use a more permissive cookie setup for the proxy environment
     session_set_cookie_params([
         'lifetime' => 0,
         'path' => '/', // Try root path to ensure it's captured by the browser
         'domain' => '',
         'secure' => false,
         'httponly' => false, // Set to false temporarily for debugging
         'samesite' => 'Lax'
     ]);
     session_start();
 }

// Debug logging
function pma_log($msg) {
    file_put_contents(__DIR__ . '/pma_sso.log', date('[Y-m-d H:i:s] ') . $msg . "\n", FILE_APPEND);
}

pma_log("--- SSO SCRIPT START ---");
pma_log("Request URI: " . $_SERVER['REQUEST_URI']);
pma_log("PHP Self: " . $_SERVER['PHP_SELF']);
pma_log("Included files: " . count(get_included_files()));

if (defined('PHPMYADMIN')) {
    pma_log("Included by phpMyAdmin. PHPMYADMIN constant is defined.");
}

pma_log("Session ID: " . session_id());
 pma_log("Cookies: " . json_encode($_COOKIE));
 
 // Add a flag to prevent infinite loops if index.php redirects back to sso.php
 if (isset($_GET['redirect_count']) && $_GET['redirect_count'] > 3) {
     pma_log("Too many redirects, stopping.");
     die("Redirect loop detected. Please clear your cookies and try again.");
 }

 if (isset($_GET['pma_token'])) {
    pma_log("Received token: " . $_GET['pma_token']);
    $token = $_GET['pma_token'];
    // Call the backend API to verify the token and get credentials
    // Use 127.0.0.1 instead of localhost to avoid IPv6 resolution issues on Windows
    $apiUrl = "http://127.0.0.1:8000/api/v1/database/pma-sso-verify/" . urlencode($token);
    
    $context = stream_context_create([
        'http' => [
            'method' => 'GET',
            'header' => 'Accept: application/json',
            'timeout' => 5
        ]
    ]);
    
    $response = @file_get_contents($apiUrl, false, $context);
    
    if ($response === false) {
        pma_log("Failed to verify token with API: " . $apiUrl);
        die("Failed to verify token with backend API. Please ensure the backend is running.");
    }
    
    $data = json_decode($response, true);
    
    if (isset($data['db_user'])) {
        pma_log("Verification successful for user: " . $data['db_user']);
        // Set credentials for phpMyAdmin signon authentication
        $_SESSION['PMA_single_signon_user'] = $data['db_user'];
        $_SESSION['PMA_single_signon_password'] = $data['db_password'];
        $_SESSION['PMA_single_signon_host'] = $data['db_host'];
        $_SESSION['PMA_single_signon_port'] = $data['db_port'];
        
        // If a specific database was requested via URL, set it
        if (isset($_GET['db'])) {
            $_SESSION['PMA_single_signon_db'] = $_GET['db'];
            pma_log("Setting target database to: " . $_GET['db']);
        }
        
        // If we are being included by phpMyAdmin, we DON'T need to redirect.
        // We just set the session and let phpMyAdmin continue.
        if (defined('PHPMYADMIN')) {
            pma_log("Token verified during inclusion. Continuing without redirect.");
            return;
        }
        
        // Save session and redirect to phpMyAdmin main page
        session_write_close();
        pma_log("Redirecting to index.php with session " . session_id());
        header('Location: index.php');
        exit;
    } else {
        pma_log("Invalid or expired token response: " . $response);
        die("Invalid or expired phpMyAdmin token. Please try again from the Sanguo Panel.");
    }
}

// If no token or verification fails, check if we have a valid session
if (empty($_SESSION['PMA_single_signon_user'])) {
    // If we are being included by phpMyAdmin, don't show the error page,
    // just let phpMyAdmin handle the lack of credentials (it might show login form)
    if (defined('PHPMYADMIN')) {
        pma_log("No session found during phpMyAdmin inclusion. Silently returning.");
        return;
    }

    pma_log("Access denied - no session and no token.");
    ?>
    <!DOCTYPE html>
    <html lang="zh">
    <head>
        <meta charset="UTF-8">
        <title>Access Denied - Sanguo Panel</title>
        <style>
            body { font-family: sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; background: #f5f5f5; }
            .card { background: white; padding: 2rem; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); text-align: center; }
            .btn { display: inline-block; background: #4a90e2; color: white; padding: 0.5rem 1rem; text-decoration: none; border-radius: 4px; margin-top: 1rem; }
        </style>
    </head>
    <body>
        <div class="card">
            <h2>访问拒绝</h2>
            <p>请通过三国面板点击“管理”按钮访问数据库。</p>
            <a href="http://localhost:5173/mariadb" class="btn">返回面板</a>
        </div>
    </body>
    </html>
    <?php
    exit;
}
pma_log("Session valid for user: " . $_SESSION['PMA_single_signon_user']);
?>
