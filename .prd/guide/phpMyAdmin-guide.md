## 介绍
phpMyAdmin 是由 PHP 编写的用于管理 MySQL 或 MariaDB 数据服务器的免费软件工具。您可以使用 phpMyAdmin 来实行大部分管理任务，如创建数据库、运行查询和添加用户账户。

支持的功能
目前 phpMyAdmin 能：

创建、浏览、编辑和删除数据库、表、视图、字段及索引
通过存储过程或查询显示多种结果集
创建、复制、删除、改名和修改数据库、表、字段及索引
在服务器设置中提供对如何维护服务器、数据库和表的建议
执行、编辑并将任意 SQL 语句甚至批量查询加入书签
载入文本文件至表
创建 [1] 和读取表的转储
导出 [1] 数据为多种格式： CSV、 XML、 PDF、 ISO/IEC 26300 - OpenDocument 文本和电子表格、微软 Word 2000 和 LATEX 格式
从 OpenDocument 电子表格、 XML 、 CSV 和 SQL 文件中导入数据和 MySQL 结构
管理多台服务器
添加、编辑和删除 MySQL 用户和权限
检查 MyISAM 表的参照完整性
根据您数据库的设计创建 PDF 图
在全部或部分数据库中搜索
通过一系列预定义函数转换现有数据至任意形式，如将 BLOB 数据显示为图像或下载链接
追踪数据库、表和视图的变化
支持 InnoDB 表和外键
支持 mysqli，改进的 MySQL 扩展，参见 1.17.1 phpMyAdmin 支持哪些数据库版本？
创建、编辑、调用、导出和删除存储过程及函数
创建、编辑、导出和删除事件及触发器
支持多达 80 种语言
快捷键
目前 phpMyAdmin 支持以下快捷键：

k - 切换控制台显示
h - 前往主页
s - 打开设置
d + s - 前往数据库结构（如果你在数据库相关页面）
d + f - 查找数据库（如果你在数据库相关页面）
t + s - 前往表格结构（如果你在表格相关页面）
t + f - 表格查询（如果你在表格相关页面）
backspace - 回到之前的页面。
关于用户
很多人难以理解 phpMyAdmin 用户的概念。当用户登录到 phpMyAdmin 时，用户名和密码是被直接发送到 MySQL 的。phpMyAdmin 本身并不管理任何用户（但有相应权限的用户可以通过 phpMyAdmin 管理 MySQL 用户)；所有用户都必须是有效的 MySQL 用户。

## 需求:
网站服务器
因为 phpMyAdmin 的界面是完全基于您的浏览器，所以您需要一个网站服务器（如 Apache, nginx, IIS）来安装 phpMyAdmin。

PHP
You need PHP 8.1.2 or newer, with session support, the Standard PHP Library (SPL) extension, hash, ctype, and JSON support.
为性能需求，强烈推荐使用 mbstring 扩展（参见 mbstring）。
要支持上传 ZIP 文件，您需要 PHP zip 扩展。
要支持内嵌 JPEG 图像（“image/jpeg: inline”）的等比缩略图，您需要 PHP GD2 支持。
当使用 cookie 认证（默认）时，强烈建议使用 openssl 扩展。
要支持上传进度条，参见 2.9 怎样设置才能显示上传进度条？。
要支持导入 XML 和开放文档电子表格，您需要 libxml 扩展。
要在登陆页支持使用 reCAPTCHA，您需要 openssl 扩展。
为支持显示 phpMyAdmin 的最新版本，您需要在 php.ini 中启用 allow_url_open 或安装 curl 扩展。
参见 1.31 phpMyAdmin 支持哪些 PHP 版本？ 、认证方式的使用
数据库
phpMyAdmin 支持与 MySQL 兼容的数据库。

MySQL 5.5 或更高版本
MariaDB 5.5 或更高版本
参见 1.17.1 phpMyAdmin 支持哪些数据库版本？
网页浏览器
您需要一个支持 cookies 和启用了 JavaScript 的网页浏览器来访问 phpMyAdmin。


## 安装
phpMyAdmin 不会在 MySQL 数据库服务器上应用任何特别的安全措施。正确设置 MySQL 数据库的权限是系统管理员应该做的。phpMyAdmin 的 用户 页面可以帮助系统管理员设置权限。

Linux发行版
phpMyAdmin包含在大多数Linux发行版中。建议尽可能使用分发包 - 它们通常提供与您的发行版的集成，并且您将自动从您的发行版中获取安全更新。

Debian 和 Ubuntu
大多数 Debian 和 Ubuntu 版本中包含了 phpMyAdmin 软件包，但要注意配置文件是在 /etc/phpmyadmin 中维护的，并且可能在某些方面与官方的phpMyAdmin文档有所不同。具体来说它包括：

Web 服务器的配置（适用于Apache和lighttpd）。
使用dbconfig-common创建 phpMyAdmin配置存储。
保护设置脚本，请参阅： Debian、Ubuntu及其衍生产品的安装脚本。

Windows安装
在Windows上获得phpMyAdmin最容易的方法是使用带有phpMyAdmin、数据库和网络服务器的第三方产品，比如 XAMPP 。

从Git安装
为了从 Git 安装，您需要一些支持的应用：

Git 来下载源代码，或直接从 Github 下载最新的代码
Composer
Node.js (version 14 or higher)
Yarn
你可以从 https://github.com/phpmyadmin/phpmyadmin.git 克隆当前的phpMyAdmin源代码：

git clone https://github.com/phpmyadmin/phpmyadmin.git
此外，您需要使用 Composer 来安装依赖项：

composer update
如果您不打算开发，可以通过调用以下命令跳过开发人员工具的安装：

composer update --no-dev
最终，你需要用 Yarn 安装一些 JavaScript 依赖：

yarn install --production


## 设置
所有可配置的数据均位于 phpMyAdmin 的根目录下的 config.inc.php 文件中。若该文件不存在，请参考 安装 一节来创建它。该文件只需包含你想从其相应的默认值中改变的参数。
https://docs.phpmyadmin.net/zh-cn/latest/config.html#
https://docs.phpmyadmin.net/zh-cn/latest/config.html#server-connection-settings





