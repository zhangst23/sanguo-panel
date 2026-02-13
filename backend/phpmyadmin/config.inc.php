<?php
declare(strict_types=1);

$cfg['blowfish_secret'] = '32_chars_long_random_string_for_pma'; /* YOU MUST FILL IN THIS FOR COOKIE AUTH! */

/**
 * Servers configuration
 */
$i = 0;

/* First server */
$i++;
/* Authentication type */
$cfg['Servers'][$i]['auth_type'] = 'signon';
$cfg['Servers'][$i]['SignonSession'] = 'SanguoPMA';
$cfg['Servers'][$i]['SignonScript'] = 'sso.php';
$cfg['Servers'][$i]['SignonURL'] = 'sso.php';
$cfg['Servers'][$i]['host'] = 'localhost';
$cfg['Servers'][$i]['compress'] = false;
$cfg['Servers'][$i]['AllowNoPassword'] = false;

/**
 * End of servers configuration
 */

$cfg['UploadDir'] = '';
$cfg['SaveDir'] = '';
$cfg['DefaultLang'] = 'zh_CN';
$cfg['ServerDefault'] = 1;

// 强制 phpMyAdmin 使用统一的 Session 名称
$cfg['SessionName'] = 'SanguoPMA';
