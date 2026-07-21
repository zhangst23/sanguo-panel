## WP-CLI 通过命令行来建立（安装和配置）WordPress 网站。**

事实上，这是 WP-CLI 最核心、最强大的功能之一。使用命令行相比传统的浏览器安装方式（下载压缩包 -> 上传 -> 解压 -> 访问域名 -> 填写表单），不仅速度快得多，而且非常适合自动化部署和批量建站。

以下是通过 WP-CLI 从零开始建立一个 WordPress 网站的基本步骤：

### 前置准备
1.  你需要一个已经配置好的服务器环境。
2.  你需要已经安装好 WP-CLI 工具。
3.  你已经在服务器上创建了一个空的数据库（或者你有创建数据库的权限）。

---

### 建站核心命令步骤

假设你的域名是 `example.com`，以下是操作流程：

#### 1. 下载 WordPress 核心文件
进入你的网站根目录（例如 `/var/www/html/example.com`），然后运行：

```bash
wp core download --locale=zh_CN
```
*   `--locale=zh_CN`：表示下载中文版本。如果不加这个参数，默认下载英文版。

#### 2. 创建配置文件 (`wp-config.php`)
你需要将数据库名、用户名和密码写入配置文件：

```bash
wp config create --dbname=your_dbname --dbuser=your_dbuser --dbpass=your_dbpassword --dbhost=localhost
```
*   `your_dbname`：数据库名。
*   `your_dbuser`：数据库用户名。
*   `your_dbpass`：数据库密码。
*   `dbhost`：数据库地址，通常是 `localhost`。

#### 3. 安装 WordPress (初始化数据库)
这一步会初始化数据库表，并创建管理员账户：

```bash
wp core install --url=example.com --title="我的网站标题" --admin_user=admin --admin_password=strongpassword --admin_email=admin@example.com
```
*   `--url`：你的网站域名。
*   `--title`：网站名称。
*   `--admin_user`：管理员用户名。
*   `--admin_password`：管理员密码。
*   `--admin_email`：管理员邮箱。

---

### 完成与后续操作

执行完上面三步，你的 WordPress 网站其实就已经**建好了**。你可以直接访问域名查看。

除此之外，WP-CLI 还可以继续通过命令行完成后续的建站工作，例如：

*   **安装插件：**
    ```bash
    wp plugin install woocommerce --activate
    # 安装并激活 WooCommerce 插件
    ```
*   **安装主题：**
    ```bash
    wp theme install twentynineteen --activate
    # 安装并激活主题
    ```
*   **更新伪静态规则：**
    如果你使用的是 Nginx 或 Apache，可以通过命令重置伪静态规则。

### 为什么用命令行建站更好？

1.  **速度极快**：不需要通过浏览器下载文件，也不需要点击各种“下一步”按钮，几秒钟就能完成安装。
2.  **可自动化**：你可以把上面这些命令写成一个 Shell 脚本，以后建新站只需运行脚本，一分钟内搞定。
3.  **更安全**：不需要通过浏览器暴露安装界面，减少潜在的安全风险。

总结来说，WP-CLI 是开发者运维 WordPress 的必备工具，完全可以替代浏览器安装过程。


## WP-CLI Commands
In this article
Commands
Other Developer Resources
↑ Back to top

Below is a listing of all currently available WP-CLI commands with links to documentation on usage and subcommands.

Looking to learn more about the internal API of WP-CLI or to contribute to its development? Check out the WP-CLI team’s handbook and the WP-CLI Blog.

Commands
Command	Description
wp ability
Lists, inspects, and executes abilities registered via the WordPress Abilities API.
wp admin
Open /wp-admin/ in a browser.
wp block
Manages WordPress block editor blocks and related entities.
wp cache
Adds, removes, fetches, and flushes the WP Object Cache object.
wp cap
Adds, removes, and lists capabilities of a user role.
wp cli
Reviews current WP-CLI info, checks for updates, or views defined aliases.
wp comment
Creates, updates, deletes, and moderates comments.
wp config
Generates and reads the wp-config.php file.
wp core
Downloads, installs, updates, and manages a WordPress installation.
wp cron
Tests, runs, and deletes WP-Cron events; manages WP-Cron schedules.
wp db
Performs basic database operations using credentials stored in wp-config.php.
wp dist-archive
Create a distribution archive based on a project’s .distignore file.
wp embed
Inspects oEmbed providers, clears embed cache, and more.
wp eval
Executes arbitrary PHP code.
wp eval-file
Loads and executes a PHP file.
wp export
Exports WordPress content to a WXR file.
wp find
Find WordPress installations on the filesystem.
wp help
Gets help on WP-CLI, or on a specific command.
wp i18n
Provides internationalization tools for WordPress projects.
wp import
Imports content from a given WXR file.
wp language
Installs, activates, and manages language packs.
wp maintenance-mode
Activates, deactivates or checks the status of the maintenance mode of a site.
wp media
Imports files as attachments, regenerates thumbnails, or lists registered image sizes.
wp menu
Lists, creates, assigns, and deletes the active theme’s navigation menus.
wp network
Perform network-wide operations.
wp option
Retrieves and sets site options, including plugin and WordPress settings.
wp package
Lists, installs, and removes WP-CLI packages.
wp plugin
Manages plugins, including installs, activations, and updates.
wp post
Manages posts, content, and meta.
wp post-type
Retrieves details on the site’s registered post types.
wp profile
Quickly identify what’s slow with WordPress.
wp rewrite
Lists or flushes the site’s rewrite rules, updates the permalink structure.
wp role
Manages user roles, including creating new roles and resetting to defaults.
wp scaffold
Generates code for post types, taxonomies, plugins, child themes, etc.
wp search-replace
Searches/replaces strings in the database.
wp server
Launches PHP’s built-in web server for a specific WordPress installation.
wp shell
Opens an interactive PHP console for running and testing PHP code.
wp sidebar
Lists registered sidebars.
wp site
Creates, deletes, empties, moderates, and lists one or more sites on a multisite installation.
wp super-admin
Lists, adds, or removes super admin users on a multisite installation.
wp taxonomy
Retrieves information about registered taxonomies.
wp term
Manages taxonomy terms and term meta, with create, delete, and list commands.
wp theme
Manages themes, including installs, activations, and updates.
wp transient
Adds, gets, and deletes entries in the WordPress Transient Cache.
wp user
Manages users, along with their roles, capabilities, and meta.
wp widget
Manages widgets, including adding and moving them within sidebars.