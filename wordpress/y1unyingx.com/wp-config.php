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
define( 'DB_NAME', 'db_y1unyingx_com' );

/** Database username */
define( 'DB_USER', 'u_y1unyingx_com' );

/** Database password */
define( 'DB_PASSWORD', 'VkPsLV4t7QeBOmDe' );

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
define( 'AUTH_KEY',          '} tHWo*]bg]k1b057~EZ=UZPl2PHDy$ch:t/O 54RVTK!V2Xr>Z/he+vWm)=UN2A' );
define( 'SECURE_AUTH_KEY',   'NeG(I]0^;Ca>pk<(mku;f>H5KPh;Sa4C)0g2diS8$[*d)Xm`C0%%n<UvY{u[U*2L' );
define( 'LOGGED_IN_KEY',     'n@HzGD5W0PJsh[Hi`?@tz/p^R+=LS#e%Uin!%NZ;9S8+ta7a?/f@KpClLklk9pjY' );
define( 'NONCE_KEY',         'WNS1Kg,7a5$*Dx{_&/.unI`(&M:&H^<nKR?$0~UhCwfHI4ub:Bj $D9=07yNscID' );
define( 'AUTH_SALT',         '-kwPf|M`, ;g4)5<w4q&lm~yy+=S=N!<;wOzX`13<%zw~c ?_=pW.DM@% -/U_lf' );
define( 'SECURE_AUTH_SALT',  '<.Ef#x~Q$59:[V(_P9{T=>h[8qupk/<_[^W$5#VwOML+F#Q>5?K]+<LRvoKc&z31' );
define( 'LOGGED_IN_SALT',    '%y~znaGA0%+:1NDj:W=-j+u4nZ1)ve%Qoi5d:`WyIOWCSd*CWP}*|{^;=U?+Jf+$' );
define( 'NONCE_SALT',        '5{?qkCu`utalE(:R 8!R&&#Z.|2?;kUOsW!|)|1B~8KKUtE3o8<aZ&cpP.nM8T,{' );
define( 'WP_CACHE_KEY_SALT', '^y)^jQ>YO/^iuE@|!xWtZpr%HFgf/tT+nPE#P3Pxlhy,nwF57qWzTH_8Bxi*|G>/' );


/**#@-*/

/**
 * WordPress database table prefix.
 *
 * You can have multiple installations in one database if you give each
 * a unique prefix. Only numbers, letters, and underscores please!
 */
$table_prefix = 'wp_1_';


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
