
## Installation
There are multiple ways to install OpenLiteSpeed Web Server. You can install to Debian, Ubuntu, CentOS, or AlmaLinux through the LiteSpeed Repository, or you can use one of our other fast setup methods (Cloud Image, Script, and Docker). Some of our alternate setup methods may bundle useful software, such as WordPress, all in one easy setup.

Supported Operating Systems¶
OpenLiteSpeed supports current and non-EOL versions of the following Linux distributions:

CentOS* 8, 9, 10
Debian 11, 12, 13
Ubuntu 20 (EOL May 31, 2025), 22, 24
* Includes RedHat Enterprise Linux and derivatives, AlmaLinux, CloudLinux, Oracle Linux, RockyLinux, VzLinux, etc.

## Install from Repository¶
The LiteSpeed Repository allows you to easily install OpenLiteSpeed and PHP to a supported operating system.

Supported Operating Systems¶
OpenLiteSpeed supports current and non-EOL versions of the following Linux distributions:

CentOS* 8, 9, 10
Debian 11, 12, 13
Ubuntu 20 (EOL May 31, 2025), 22, 24
* Includes RedHat Enterprise Linux and derivatives, AlmaLinux, CloudLinux, Oracle Linux, RockyLinux, VzLinux, etc.

Install the LiteSpeed Repository¶
sudo wget -O - https://repo.litespeed.sh | sudo bash
Install OpenLiteSpeed¶

Debian/Ubuntu
CentOS
sudo apt-get -y install openlitespeed

Install LSPHP¶
This command will install lsphp84 and lsphp84-mysql into /usr/local/lsws/lsphp84/bin/lsphp:


Debian/Ubuntu
CentOS
sudo apt-get install lsphp84 lsphp84-common lsphp84-mysql

To get a list of the LSPHP packages and extensions available, you can run the following:


Debian/Ubuntu
CentOS
sudo apt-cache search lsphp

Access the WebAdmin Console¶
The randomly generated WebAdmin password is stored in the /usr/local/lsws/adminpasswd file.

Run the following command to set the WebAdmin password if needed:

sudo /usr/local/lsws/admin/misc/admpass.sh
To access the WebAdmin console, visit port 7080 of your domain (for example, https://example.com:7080/) and log in using the password you just set.

## Install from One-Click Script¶
Our One-Click script comes with several options and can be used with any supported operating system.

Supported Operating Systems¶
OpenLiteSpeed supports current and non-EOL versions of the following Linux distributions:

CentOS* 8, 9, 10
Debian 11, 12, 13
Ubuntu 20 (EOL May 31, 2025), 22, 24
* Includes RedHat Enterprise Linux and derivatives, AlmaLinux, CloudLinux, Oracle Linux, RockyLinux, VzLinux, etc.

Common uses¶
Here are two ways that ols1clck is commonly used.

Install the following:

OpenLiteSpeed
LSPHP
MariaDB
WordPress
LiteSpeed Cache plugin
bash <( curl -k https://raw.githubusercontent.com/litespeedtech/ols1clk/master/ols1clk.sh ) -w
Install only:

OpenLiteSpeed
LSPHP
bash <( curl -k https://raw.githubusercontent.com/litespeedtech/ols1clk/master/ols1clk.sh )
Options¶
Essential Options¶
Opt	Options	Description
--adminuser [USERNAME]	To set the WebAdmin username for LiteSpeed instead of admin.
-A	--adminpassword [PASSWORD]	To set the WebAdmin password for LiteSpeed instead of using a random one.
--adminport [PORTNUMBER]	To set the WebAdmin console port number instead of 7080.
-E	--email [EMAIL]	To set the administrator email.
PHP Configuration¶
Opt	Options	Description
--lsphp [VERSION]	To set the LSPHP version, such as 84. We currently support 74 80 81 82 83 84 85.
DataBase Options¶
Opt	Options	Description
--mariadbver [VERSION]	To set MariaDB version. We currently support 10.6 10.11 11.4 11.8.
-R	--dbrootpassword [PASSWORD]	To set the database root password.
--dbname [DATABASENAME]	To set the database name to be used by WordPress.
--dbuser [DBUSERNAME]	To set the WordPress username in the database.
--dbpassword [PASSWORD]	To set the WordPress table password in MySQL.
--prefix [PREFIXNAME]	To set the WordPress table prefix.
--pure-mariadb	To install LiteSpeed and MariaDB.
--pure-mysql	To install LiteSpeed and MySQL.
--pure-percona	To install LiteSpeed and Percona.
--with-mysql	To install LiteSpeed/App with MySQL.
--with-percona	To install LiteSpeed/App with Percona.
Application Options¶
Opt	Options	Description
-W	--wordpress	To install WordPress. You will still need to complete the WordPress setup by browser
--wordpressplus [SITEDOMAIN]	To install, set up, and configure WordPress, also LSCache will be enabled
--wordpresspath [WP_PATH]	To specify a location for the WordPress installation or use for an existing WordPress.
--wpuser [WP_USER]	To set the WordPress admin user for WordPress dashboard login.
--wppassword [PASSWORD]	To set the WordPress admin user password for WordPress dashboard login.
--wplang [WP_LANGUAGE]	To set the WordPress language. Default value is "en_US" for English.
--sitetitle [WP_TITLE]	To set the WordPress site title. Default value is mySite.
System Configuration¶
Opt	Options	Description
--listenport [PORT]	To set the HTTP server listener port, default is 80.
--ssllistenport [PORT]	To set the HTTPS server listener port, default is 443.
--proxy-r	To set a proxy with rewrite type.
--proxy-c	To set a proxy with config type.
Security Configuration¶
Opt	Options	Description
--owasp-enable	To enable mod_security with OWASP rules. If OLS is installed, then enable the owasp directly
--owasp-disable	To disable mod_security with OWASP rules.
--fail2ban-enable	To enable fail2ban for webadmin and wordpress login pages.
Control¶
Opt	Options	Description
-U	--uninstall	To uninstall LiteSpeed and remove installation directory.
-P	--purgeall	To uninstall LiteSpeed, remove installation directory, and purge all data in MySQL.
-Q	--quiet	To use quiet mode, won't prompt to input anything.
-V	--version	To display the script version information.
-v	--verbose	To display more messages during the installation.
--update	To update ols1clk from github.
-H	--help	To display help messages.
Usage Examples¶
```
Web Server with PHP¶
# To install LiteSpeed with default PHP Version.
./ols1clk.sh
WordPress with PHP¶
# To install LiteSpeed with WordPress and MariaDB"
./ols1clk.sh -W
WordPress with Mysql¶
# To install LiteSpeed with WordPress and Mysql"
./ols1clk.sh -W --with-mysql
OWASP¶
# To enable OWASP feature for ols. This single option can be used even if the web server is already installed. 
./ols1clk.sh --owasp-enable
```
## Install from Precompiled Binary¶
Precompiled OpenLiteSpeed binaries are included in the download package. You can easily install these binaries instead of compiling and installing from source code.

Supported Operating Systems¶
OpenLiteSpeed supports current and non-EOL versions of the following Linux distributions:

CentOS* 8, 9, 10
Debian 11, 12, 13
Ubuntu 20 (EOL May 31, 2025), 22, 24
* Includes RedHat Enterprise Linux and derivatives, AlmaLinux, CloudLinux, Oracle Linux, RockyLinux, VzLinux, etc.

Note

Currently one-click installation only supports the above operating systems with 64-bit platforms.

User Permission¶
You will need Super User permissions to install OLS as root. How you do this will depend upon which distribution you use. Some distributions such as CentOS enable the root user, allowing you to use the su command. Others such as Ubuntu and Debian do not, and require you to use the sudo command.

Direct Download¶
Download the OpenLiteSpeed binary from the Download page. Or, use the wget command to download it from the console, like so:

 wget https://openlitespeed.org/packages/openlitespeed-1.8.4.tgz
Installation¶
Binary installation can be done in just a few commands:

tar -zxvf openlitespeed-*.tgz
cd openlitespeed
./install.sh
If the installation goes well, you will see:

[OK] The startup script has been successfully installed!
Now you can start the web server, like so:

/usr/local/lsws/bin/lswsctrl start
Check the status:

/usr/local/lsws/bin/lswsctrl status

## Upgrade or Downgrade OpenLiteSpeed¶
There are three different methods for upgrading or downgrading your version of OpenLiteSpeed:

LiteSpeed repository
lsup.sh script
Binary install
To avoid complications, always upgrade or downgrade using the same method you used to install OpenLiteSpeed originally.

Warning

If you are using OLS on DirectAdmin, please don't use any of these methods. Please see How to Upgrade OLS on DirectAdmin.

Method 1: LiteSpeed Repository¶
Note

You will only have access to the stable versions of the software via the repository. For example, v1.8.x may be available on the dev repository, but you may only be able to access versions in the 1.7.x family from the repo until 1.8.x is considered stable.

If you wish to use a version from the dev repo, you will need to upgrade via lsup.sh, or update the URL in the lst_debian_repo.list file from rpms.litespeedtech.com to repo-dev.litespeedtech.com.

If you installed OpenLiteSpeed through the LiteSpeed repository before, you should simply run the package update command.

Upgrade¶

CentOS
Debian/Ubuntu
 yum update openlitespeed

Downgrade¶

CentOS
Debian/Ubuntu from history
Debian/Ubuntu from repo
You can downgrade to any specific version that the repository supports.

Find all of the available versions from the repository
yum --showduplicates list openlitespeed
Run the downgrade command with the version you need
yum downgrade openlitespeed-1.8.4

Method 2: lsup.sh Script¶
The lsup.sh script works similarly to the LiteSpeed Enterprise lsup.sh script, and allows you to upgrade or downgrade OLS to a particular version.

You can download the latest lsup.sh with the following command if /usr/local/lsws/admin/misc/lsup.sh does not exist:

wget https://raw.githubusercontent.com/litespeedtech/openlitespeed/master/dist/admin/misc/lsup.sh
Note

If you previously installed OLS through yum or apt-get, it's fine to upgrade to other versions with the lsup command.

Running ./lsup.sh will update to the latest stable version, and ./lsup.sh -d will update to the latest stable DEBUG version.

Additionally, these options are available:

Usage: lsup.sh [-t] | [-c] | [[-d] [-r] | [-v VERSION]] | [-e VERSION]
  -a
     Update web admin password
  -d
     Choose Debug version to upgrade or downgrade, will do clean like -c at the same time.
  -v VERSION
     If VERSION is given, this command will install the specified VERSION. Otherwise, it will get the latest version from /usr/local/lsws/autoupdate/release.
  -e VERSION 
     Upgrade/downgrade to specified VERSION without making any other changes. The version listed in /usr/local/lsws/VERSION does not change.
  -r 
     Restore the originally installed version which is in file VERSION.
  -p
     Restore the previously installed version which was renamed to .old files.
  -t
     To test openlitespeed running status.
  -c
     Do some cleanup and restart openlitespeed service.
  -h | --help     
     Display this help and exit.
  -g 
     Toggle DEBUG log
lsup.sh is not only a very powerful tool to upgrade/downgrade OLS, but also an installation tool if OLS has not yet been installed on the server.

Tip

To test a particular version temporarily, use the -e VERSION option, run your tests, and then use the -r option to restore the original version listed in /usr/local/lsws/VERSION.

Commonly used example:

/usr/local/lsws/admin/misc/lsup.sh -v 1.8.4
Method 3: Binary Install¶
If you installed OLS by downloading the package and running ./install.sh, you will need to do the same to upgrade. For example, you could upgrade from 1.7.x to 1.8.4 like so:

wget https://openlitespeed.org/packages/openlitespeed-1.8.4.tgz
tar -zxvf openlitespeed-*.tgz
cd openlitespeed
./install.sh
Note

Binary install should not be mixed with repository installation. If you'd like to switch to a different type of installation, see below.

Switch Method of Installation¶
Most of the time, you should upgrade or downgrade with the same method that you originally used to install OLS. If you need to switch to a different version for some reason, follow these steps:

Back up your entire OLS configuration.
Uninstall OLS using yum or apt-get, as appropriate for your OS, to avoid accidentally downgrading in the future.
Copy the OLS configuration backup to /usr/local/lsws/conf/.
Install OLS using your preferred method.









