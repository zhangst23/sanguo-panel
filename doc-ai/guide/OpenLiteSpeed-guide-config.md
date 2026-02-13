
## Configure OpenLiteSpeed¶
Now that you have installed OpenLiteSpeed, it's time for some basic configuration. That starts with setting up one or more virtual hosts, and setting up listeners for the HTTP and HTTPS ports.

Set up Virtual Hosts¶
With name-based virtual hosting, you can host more than one website (also called a "virtual host" or "vhost") on each IP address. LiteSpeed provides a default virtual host named Example. If you don't need any more virtual hosts, you can skip ahead to Set up Listeners.

In the following steps we will set up a new virtual host that we'll call Example2.

Set up DNS¶
The domain names used by your virtual hosts will need to be forwarded to your web server's IP address. This is commonly done by adding an A record to the DNS zone file for the website. This is not part of OpenLiteSpeed configuration. Please see your DNS provider for further instruction, if needed.

Create a new Virtual Host¶
Create directories¶
To create directories for the new Example2 virtual host, start at the command line. Add an Example2 directory, plus three subdirectories - conf, html, and logs - in your lsws directory, like so:

mkdir /usr/local/lsws/Example2
mkdir /usr/local/lsws/Example2/{conf,html,logs}
Change the owner of the conf directory to lsadm:lsadm (the WebAdmin Console user) so that only the WebAdmin Console will have the ability to manipulate Example2's configuration:

chown lsadm:lsadm /usr/local/lsws/Example2/conf
Add to WebAdmin Console¶
Switch to the WebAdmin Console and navigate to Virtual Hosts > Add. Configure the settings like so:

Virtual Host Name = Example2
Virtual Host Root = $SERVER_ROOT/Example2
Config File = $SERVER_ROOT/conf/vhosts/Example2/vhost.conf
Enable Scripts/ExtApps = Yes
Restrained = No
You might see the following warning if you are starting from scratch with this virtual host's configuration. Go ahead and click to create:

file /usr/local/lsws/conf/vhosts/Example2/vhost.conf does not exist. CLICK TO CREATE
Click the Save button, return to Example2's configuration, and change the following settings under the General tab:

Document Root = /usr/local/lsws/Example2/html
Index Files = index.html, index.php
We recommend enabling the Rewrite feature as well. Change the following settings under the Rewrite tab:

Enable Rewrite = Yes
Auto Load from .htaccess = yes
Set up Listeners¶
Create a Listener¶
Navigate to Listeners in the WebAdmin Console. There is already a default listener that listens to all IPs on port 8088, but you might want to create another two listeners for both HTTP and HTTPS ports. Here is how:

Click the Add button to create an HTTP listener with following settings:

Listener Name = HTTP
IP Address = ANY IPv4
Port = 80
Secure = No
Click the Add button to create an HTTPS listener with following settings:

Listener Name = HTTPS
IP Address = ANY IPv4
Port = 443
Secure = Yes
To configure SSL on the listener you named HTTPS, navigate to Listeners > HTTPS > SSL, and click the Edit button. Specify the private key and certificate path, then click the Save button. Here are some examples, but be sure to use your own correct file path:

Let's Encrypt:

Private Key File = /etc/letsencrypt/live/example.com/privkey.pem
Certificate File = /etc/letsencrypt/live/example.com/fullchain.pem
Chained Certificate = Yes
Temporary WebAdmin certificate or a private self-signed certificate:

Private Key File = /usr/local/lsws/conf/example.key
Certificate File = /usr/local/lsws/conf/example.crt
Chained Certificate = Not Set
Note

For each IP address, only one process each may bind to ports 80 and 443, so you only need one listener for each port. These two listeners may then be mapped to multiple virtual hosts

Map Virtual Hosts¶
Navigate to Listeners > HTTP > Virtual Host Mappings and click the Add button. Use the following values to map the HTTP listener to the Example2 virtual host:

Virtual Host = Example2
Domains = example2.com, www.example2.com
Repeat for the HTTPS listener using the exact same settings.

Set up SSL for Virtual Hosts¶
OpenLiteSpeed supports Server Name Indication (SNI), allowing users to set SSL certificates at the virtual host level. This is optional, though. If you don't set up SSL at the virtual host level, the HTTPS Listener's SSL settings will be used.

To set up SSL for our Example2 virtual host in the WebAdmin Console, navigate to Virtual Hosts > Example2 > SSL > Edit SSL Private Key & Certificate.

Update the new SSL settings with the following example as a guide, using your own file paths:

Private Key File = /usr/local/lsws/conf/example.key
Certificate File = /usr/local/lsws/conf/example.crt
Chained Certificate = Not Set


## PHP
https://docs.openlitespeed.org/config/php/

## LiteSpeed Cache
https://docs.openlitespeed.org/config/lscache/

## Custom Headers
https://docs.openlitespeed.org/config/headers/

## Rewrite Rules
https://docs.openlitespeed.org/config/rewriterules/

## Logs
https://docs.openlitespeed.org/config/logs/

## Reverse Proxy
https://docs.openlitespeed.org/config/reverseproxy/

## App Server
Python LSAPI
https://docs.openlitespeed.org/config/appserver/python/

## Advanced Config
https://docs.openlitespeed.org/config/advanced/loadbalance/
https://docs.openlitespeed.org/config/advanced/compress/
https://docs.openlitespeed.org/config/advanced/geolocation/

