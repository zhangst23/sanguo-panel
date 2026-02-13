<?php
/**
 * phpMyAdmin SSO (Single Sign-On) Script
 * This script integrates with the Sanguo Panel backend to verify tokens
 */

/**
 * Required function for phpMyAdmin SignOn authentication plugin when SignonScript is used.
 * @param string $user Default user from config
 * @return array [username, password]
 */
function get_login_credentials($user) {
    return [
        $_SESSION['PMA_single_signon_user'] ?? '',
        $_SESSION['PMA_single_signon_password'] ?? ''
    ];
}

// Enable error reporting for debugging
ini_set('display_errors', 1);
error_reporting(E_ALL);

// Debug logging
function pma_log($msg) {
    file_put_contents(__DIR__ . '/pma_sso.log', date('[Y-m-d H:i:s] ') . $msg . "\n", FILE_APPEND);
}

// Initialize session if not already started
if (session_status() === PHP_SESSION_NONE) {
    // Set session name to something unique to avoid clashing with other phpMyAdmin instances
    $sessionName = 'SanguoPMA';
    session_name($sessionName);
    
    // Use a local session path to avoid permission issues and isolation
    $sessionPath = __DIR__ . '/sessions';
    if (!is_dir($sessionPath)) {
        @mkdir($sessionPath, 0777, true);
    }
    if (is_writable($sessionPath)) {
        session_save_path($sessionPath);
    }
    
    // Set cookie parameters for the proxy environment
    // Use a very permissive setup first to rule out cookie rejection
    session_set_cookie_params([
        'lifetime' => 0,
        'path' => '/', 
        'domain' => '',
        'secure' => false,
        'httponly' => false, // Set to false to see if it helps with proxy
        'samesite' => 'Lax'
    ]);
    
    session_start();
}

pma_log("--- SSO SCRIPT START ---");
pma_log("Request URI: " . $_SERVER['REQUEST_URI']);
pma_log("Cookies received by PHP: " . json_encode($_COOKIE));
pma_log("Session ID: " . session_id());
pma_log("Session data: " . json_encode($_SESSION));

// If we are being included by phpMyAdmin, we just need to provide the credentials
if (defined('PHPMYADMIN')) {
    pma_log("sso.php included by phpMyAdmin.");
    if (!empty($_SESSION['PMA_single_signon_user'])) {
        pma_log("Session valid for user: " . $_SESSION['PMA_single_signon_user']);
        return;
    } else {
        pma_log("No session during PMA inclusion. Session ID: " . session_id());
        // Do NOT return yet, let it fall through or handle it
    }
}

// Prevent redirect loops
if (!isset($_SESSION['redirect_count'])) $_SESSION['redirect_count'] = 0;
if (isset($_GET['pma_token'])) {
    $_SESSION['redirect_count'] = 0; // Reset on new token
}

if ($_SESSION['redirect_count'] > 5) {
    pma_log("Redirect loop detected. Stopping.");
    $_SESSION['redirect_count'] = 0;
    die("检测到重定向死循环。请尝试清除浏览器 Cookie 并重新登录。");
}

if (isset($_GET['pma_token'])) {
    pma_log("Received token: " . $_GET['pma_token']);
    $token = $_GET['pma_token'];
    
    // Call backend API
    $apiUrl = "http://127.0.0.1:8000/api/v1/database/pma-sso-verify/" . urlencode($token);
    $context = stream_context_create([
        'http' => [
            'method' => 'GET',
            'header' => 'Accept: application/json',
            'timeout' => 10
        ]
    ]);
    
    $response = @file_get_contents($apiUrl, false, $context);
    
    if ($response === false) {
        pma_log("Failed to verify token with API: " . $apiUrl);
        die("无法通过后端 API 验证 Token。请确保后端服务（端口 8000）正在运行。");
    }
    
    $data = json_decode($response, true);
    
    if (isset($data['db_user'])) {
        pma_log("Verification successful for user: " . $data['db_user']);
        
        // Set credentials
        $_SESSION['PMA_single_signon_user'] = $data['db_user'];
        $_SESSION['PMA_single_signon_password'] = $data['db_password'];
        $_SESSION['PMA_single_signon_host'] = $data['db_host'];
        $_SESSION['PMA_single_signon_port'] = $data['db_port'];
        $_SESSION['PMA_single_signon_error'] = '';
        
        if (isset($_GET['db'])) {
            $_SESSION['PMA_single_signon_db'] = $_GET['db'];
            pma_log("Setting target database to: " . $_GET['db']);
        }
        if (isset($_GET['route'])) {
            $_SESSION['PMA_single_signon_route'] = $_GET['route'];
            pma_log("Setting target route to: " . $_GET['route']);
        }

        $_SESSION['redirect_count']++;
        session_write_close();
        
        // 关键修复：重定向回 index.php，phpMyAdmin 会再次调用 sso.php（这次是通过 Include）
        $redirectUrl = 'index.php';
        $params = [];
        if (isset($_GET['db'])) $params['db'] = $_GET['db'];
        if (isset($_GET['route'])) $params['route'] = $_GET['route'];
        if (!empty($params)) $redirectUrl .= '?' . http_build_query($params);
        
        pma_log("Redirecting to index.php after token verification. Redirect URL: " . $redirectUrl);
        header('Location: ' . $redirectUrl);
        exit;
    } else {
        pma_log("Invalid token response: " . $response);
        die("Token 无效或已过期。请从三国面板重新点击进入。");
    }
}

// Check if already logged in
if (empty($_SESSION['PMA_single_signon_user'])) {
    pma_log("No session and no token. Access denied.");
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
            <h2>访问拒绝 (Access Denied)</h2>
            <p>请通过三国面板点击“管理”按钮访问数据库。</p>
            <p style="font-size: 12px; color: #999;">Session ID: <?php echo session_id(); ?></p>
            <a href="/mariadb" class="btn">返回面板</a>
        </div>
    </body>
    </html>
    <?php
    exit;
}

// Already logged in, redirect to index.php if accessing sso.php directly
pma_log("Session valid for user: " . $_SESSION['PMA_single_signon_user'] . ". Redirecting to index.php");
$_SESSION['redirect_count']++;
session_write_close();

$redirectUrl = 'index.php';
$params = [];
if (isset($_GET['db'])) $params['db'] = $_GET['db'];
if (isset($_GET['route'])) $params['route'] = $_GET['route'];
if (!empty($params)) $redirectUrl .= '?' . http_build_query($params);

header('Location: ' . $redirectUrl);
exit;

?>
