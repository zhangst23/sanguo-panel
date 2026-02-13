<?php
/**
 * The base configuration for WordPress
 *
 * The wp-config.php creation script uses this file during the installation.
 * You don't have to use the web site, you can copy this file to "wp-config.php"
 * and fill in the values.
 *
 * This file contains the following configurations:
 *
 * * Database settings
 * * Secret keys
 * * Database table prefix
 * * Localized language
 * * ABSPATH
 *
 * @link https://wordpress.org/support/article/editing-wp-config-php/
 *
 * @package WordPress
 */

// ** Database settings - You can get this info from your web host ** //
/** The name of the database for WordPress */
define( 'DB_NAME', 'db_yunying2_com' );

/** Database username */
define( 'DB_USER', 'u_yunying2_com' );

/** Database password */
define( 'DB_PASSWORD', '43pGyA1wKDUPIRww' );

/** Database hostname */
define( 'DB_HOST', 'localhost' );

/** Database charset to use in creating database tables. */
define( 'DB_CHARSET', 'utf8' );

/** The database collate type. Don't change this if in doubt. */
define( 'DB_COLLATE', '' );

/**#@+
 * Authentication unique keys and salts.
 *
 * Change these to different unique phrases! You can generate these using
 * the {@link https://api.wordpress.org/secret-key/1.1/salt/ WordPress.org secret-key service}.
 *
 * You can change these at any point in time to invalidate all existing cookies.
 * This will force all users to have to log in again.
 *
 * @since 2.6.0
 */
define( 'AUTH_KEY',          '/+_5!qeWk&opR?b*Vd}`Y2Z3SOmWQ}VY[Iqw5.BvU(#fuJ(0VfaVJ`Q,4G n/}u.' );
define( 'SECURE_AUTH_KEY',   '(2tcC9 xQ<h4apmKDxv5bR+[)ay.a}Q y9o@PVrPq9#2HwRs6p5>  Nv*L~2c)|j' );
define( 'LOGGED_IN_KEY',     'X:#)2/hx;Ubd*e%5JXa9pP26{A5B{t=0[Al,4>J.RkH.1_3e,~l4y3u#Z`Gg{?l-' );
define( 'NONCE_KEY',         '@7l#qGf0n_6[KzWQzm(;QoJ|BXr OVrS}AWr#bRm!>BA!(*fgB5-BA(6xv6e,je|' );
define( 'AUTH_SALT',         '1tliehKqhom5l|r!gA>_lno yaxGknG?WepE3F@{X?!eDWoq%6sJmR#K$o-vvfma' );
define( 'SECURE_AUTH_SALT',  '*WGE5<VERo^]%xQUl4YtGzwa@`kwVBU$1{YIrG6$}<sA|Sq#~0TK53|i]0*A:CQO' );
define( 'LOGGED_IN_SALT',    '{6Jhv&]u,zZZQR4Dgnj>=`[sR}h3;D~i$R;6*P,u4b>,u_6ee89FA-dm 0Ce-SRh' );
define( 'NONCE_SALT',        '*[>U7Gy!AKpXT-6*=6{>|Y(p{<{;M&:igr)=n53,l<*E=5Ztk5SY0/Lk-p7bcTg2' );
define( 'WP_CACHE_KEY_SALT', 'q9Z*>V2M&`!$i85#{_T!c.8MT&.AQ3_%jv$Z:GEu_p4Hs0o< opjf.SQ5z[YXT.O' );


/**#@-*/

/**
 * WordPress database table prefix.
 *
 * You can have multiple installations in one database if you give each
 * a unique prefix. Only numbers, letters, and underscores please!
 */
$table_prefix = 'wp_3_';


/* Add any custom values between this line and the "stop editing" line. */



/**
 * For developers: WordPress debugging mode.
 *
 * Change this to true to enable the display of notices during development.
 * It is strongly recommended that plugin and theme developers use WP_DEBUG
 * in their development environments.
 *
 * For information on other constants that can be used for debugging,
 * visit the documentation.
 *
 * @link https://wordpress.org/support/article/debugging-in-wordpress/
 */
if ( ! defined( 'WP_DEBUG' ) ) {
	define( 'WP_DEBUG', false );
}

/* That's all, stop editing! Happy publishing. */

/** Absolute path to the WordPress directory. */
if ( ! defined( 'ABSPATH' ) ) {
	define( 'ABSPATH', __DIR__ . '/' );
}

/** Sets up WordPress vars and included files. */
require_once ABSPATH . 'wp-settings.php';
