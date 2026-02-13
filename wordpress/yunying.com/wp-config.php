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
define( 'DB_NAME', 'db_yunying_com' );

/** Database username */
define( 'DB_USER', 'u_yunying_com' );

/** Database password */
define( 'DB_PASSWORD', 'QZT0TxHOVXp5xehD' );

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
define( 'AUTH_KEY',          '?J`y|PqgKe?T,0TDcX}*E?!njUOn&_q)|N*`=Aw3~fWaPV/$DbuSN{CAvL YGA6:' );
define( 'SECURE_AUTH_KEY',   'izq&DyT1|yx?rxieCiE5mn@wxcv8`ZUnH$@X*u*jm/c?K8eY=yoa8dx8)$c[P2Q,' );
define( 'LOGGED_IN_KEY',     '7%~SQ?!e[Tz~W+-/|=u-8|+Q.8Gp/:hm[:znks(uF-Jf}~f7e9Y{Uh>imL6e3I19' );
define( 'NONCE_KEY',         'xT{<XmQl*xWZT@451`.aGii W+Q&gm.]R/*u4]qlZ(N5hdP3M$JI Wa<$4(zOFR=' );
define( 'AUTH_SALT',         'B)V_oWy62!Q.I+YKOCz1n~<(>=po-O}cyw.[Z@#]K$4fP,KviarEB=.U!^Q6=wk>' );
define( 'SECURE_AUTH_SALT',  'M{~yhaeBIFt?c$cQm({pJE4*8Bg{J3$Twd{8OQ$!Ocx;, XtyAGZvF<BiRrcgMLh' );
define( 'LOGGED_IN_SALT',    '&Wd?o7+C@5T^9Yzl<09:o;$TA40m}kJvWAtADp_p (:In4ikHOwDBK/V8LStdLZT' );
define( 'NONCE_SALT',        'UJ Ao+@_:8N>l=zZF@*Ypn7tB?[jFMg)XLB &MS!)O,LY6^<_&P-0=h@G8Ku#9sb' );
define( 'WP_CACHE_KEY_SALT', '0&9?ApjtJIO0=CrK1HpJE3D0OY]@Uz@ld>zkeBcaP)>l59q(mEm7&KK;s#ZWO.)o' );


/**#@-*/

/**
 * WordPress database table prefix.
 *
 * You can have multiple installations in one database if you give each
 * a unique prefix. Only numbers, letters, and underscores please!
 */
$table_prefix = 'wp_2_';


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
