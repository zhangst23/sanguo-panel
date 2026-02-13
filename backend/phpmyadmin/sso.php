<?php
/**
 * phpMyAdmin SSO (Single Sign-On) Script
 * This script integrates with the Sanguo Panel backend to verify tokens
 */

session_set_cookie_params(0, '/', '', false, true);
session_name('PMA_SSO');
session_start();

if (isset($_GET['pma_token'])) {
    $token = $_GET['pma_token'];
    // Call the backend API to verify the token and get credentials
    $apiUrl = "http://localhost:8000/api/v1/database/pma-sso-verify/" . urlencode($token);
    
    $context = stream_context_create([
        'http' => [
            'method' => 'GET',
            'header' => 'Accept: application/json',
            'timeout' => 5
        ]
    ]);
    
    $response = @file_get_contents($apiUrl, false, $context);
    
    if ($response === false) {
        die("Failed to verify token with backend API. Please ensure the backend is running.");
    }
    
    $data = json_decode($response, true);
    
    if (isset($data['db_user'])) {
        // Set credentials for phpMyAdmin signon authentication
        $_SESSION['PMA_single_signon_user'] = $data['db_user'];
        $_SESSION['PMA_single_signon_password'] = $data['db_password'];
        $_SESSION['PMA_single_signon_host'] = $data['db_host'];
        $_SESSION['PMA_single_signon_port'] = $data['db_port'];
        
        // Save session and redirect to phpMyAdmin main page
        session_write_close();
        header('Location: index.php');
        exit;
    } else {
        die("Invalid or expired phpMyAdmin token.");
    }
}

// If no token or verification fails, redirect to login or show error
if (empty($_SESSION['PMA_single_signon_user'])) {
    die("Access denied. Please access phpMyAdmin through the Sanguo Panel.");
}
?>
