<template>
    <a-layout class="layout-container">
        <a-layout-sider
            breakpoint="lg"
            :width="220"
            collapsible
            :collapsed="collapsed"
            @collapse="onCollapse"
            :trigger="null"
        >
            <!-- Logo + 折叠 < -->
            <div class="logo-wrapper">
                <div v-if="!collapsed" class="logo">SanGuo WP面板</div>
                <a-button
                    type="text"
                    size="small"
                    @click="onCollapse(!collapsed)"
                    class="collapse-btn"
                    :class="{ 'collapse-btn-collapsed': collapsed }"
                    :aria-label="collapsed ? '展开' : '折叠'"
                >
                    <icon-left v-if="!collapsed" />
                    <icon-right v-else />
                </a-button>
            </div>

            <!-- 服务器 IP（点击复制） -->
            <a-tooltip
                v-if="!collapsed && serverIp"
                content="点击复制 IP"
                position="bottom"
            >
                <div class="ip-wrapper" @click="copyServerIp">
                    <span class="ip-text">{{ serverIp }}</span>
                    <icon-copy class="ip-copy" />
                </div>
            </a-tooltip>

            <!-- 菜单 -->
            <div class="sider-content">
                <a-menu
                    :selected-keys="[selectedKey]"
                    :auto-open-selected="true"
                    @menu-item-click="handleMenuClick"
                    :collapsed="collapsed"
                    mode="vertical"
                    :theme="theme === 'dark' ? 'dark' : 'light'"
                >
                    <a-menu-item key="Dashboard">
                        <template #icon><icon-dashboard /></template>
                        仪表盘
                    </a-menu-item>
                    <a-menu-item key="Website">
                        <template #icon><icon-common /></template>
                        网站管理
                    </a-menu-item>
                    <a-menu-item key="FileManager">
                        <template #icon><icon-folder /></template>
                        文件夹
                    </a-menu-item>
                    <a-menu-item key="MariaDB">
                        <template #icon><icon-storage /></template>
                        数据库
                    </a-menu-item>
                    <a-menu-item key="Security">
                        <template #icon><icon-safe /></template>
                        安全防御
                    </a-menu-item>
                    <a-menu-item key="OneClickTools">
                        <template #icon><icon-thunderbolt /></template>
                        AI 管理
                    </a-menu-item>
                    <a-menu-item key="WPAssets">
                        <template #icon>
                            <svg class="wp-menu-icon" viewBox="0 0 24 24" aria-hidden="true">
                                <path d="M21.469 6.825c.84 1.537 1.318 3.3 1.318 5.175 0 3.979-2.156 7.456-5.363 9.325l3.295-9.527c.615-1.54.82-2.771.82-3.864 0-.405-.026-.78-.07-1.11m-7.981.105c.647-.03 1.232-.105 1.232-.105.582-.075.514-.93-.067-.899 0 0-1.755.135-2.88.135-1.064 0-2.85-.15-2.85-.15-.585-.03-.661.855-.075.885 0 0 .54.061 1.125.09l1.68 4.605-2.37 7.08L5.354 6.9c.649-.03 1.234-.1 1.234-.1.585-.075.516-.93-.065-.896 0 0-1.746.138-2.874.138-.2 0-.438-.008-.69-.015C4.911 3.15 8.235 1.215 12 1.215c2.809 0 5.365 1.072 7.286 2.833-.046-.003-.091-.009-.141-.009-1.06 0-1.812.923-1.812 1.914 0 .89.513 1.643 1.06 2.531.411.72.89 1.643.89 2.977 0 .915-.354 1.994-.821 3.479l-1.075 3.585-3.9-11.61.001.014zM12 22.784c-1.059 0-2.081-.153-3.048-.437l3.237-9.406 3.315 9.087c.024.053.05.101.078.149-1.12.393-2.325.609-3.582.609M1.211 12c0-1.564.336-3.05.935-4.39L7.29 21.709C3.694 19.96 1.212 16.271 1.211 12M12 0C5.385 0 0 5.385 0 12s5.385 12 12 12 12-5.385 12-12S18.615 0 12 0" />
                            </svg>
                        </template>
                        WP 管理
                    </a-menu-item>
                    <a-menu-item key="Backup">
                        <template #icon><icon-cloud-download /></template>
                        备份迁移
                    </a-menu-item>

                    <a-sub-menu key="System">
                        <template #icon><icon-settings /></template>
                        <template #title>系统工具</template>
                        <a-menu-item key="Linux">系统管理</a-menu-item>
                        <a-menu-item key="Monitor">监控中心</a-menu-item>
                        <a-menu-item key="SystemSettings">面板设置</a-menu-item>
                        <a-menu-item key="TaskList">操作日志</a-menu-item>
                        <a-menu-item key="About">关于</a-menu-item>
                    </a-sub-menu>
                </a-menu>
            </div>

            <!-- 底部用户区域 -->
            <div class="user-area-wrapper">
                <a-popover
                    trigger="click"
                    position="top"
                    :popup-visible="userPopupVisible"
                    @popup-visible-change="onPopupVisibleChange"
                    content-class="user-popover-content"
                    :arrow-style="{ display: 'none' }"
                    :content-style="{ padding: 0 }"
                >
                    <div class="user-trigger" :class="{ collapsed }">
                        <a-avatar
                            :size="collapsed ? 32 : 36"
                            style="
                                background-color: var(--arco-blue-6);
                                flex-shrink: 0;
                            "
                        >
                            {{ userInitial }}
                        </a-avatar>
                        <div v-if="!collapsed" class="user-info">
                            <span class="username">{{ username }}</span>
                        </div>
                    </div>
                    <template #content>
                        <div class="popover-menu">
                            <!-- 语言行 -->
                            <div class="menu-row" @click="toggleLangOptions">
                                <span class="menu-label">语言</span>
                                <span class="menu-value">
                                    {{ languageLabel }}
                                    <icon-right class="menu-arrow" />
                                </span>
                            </div>
                            <div v-if="showLangOptions" class="menu-sub">
                                <div
                                    class="menu-sub-item"
                                    :class="{
                                        selected: currentLanguage === 'zh',
                                    }"
                                    @click="changeLanguage('zh')"
                                >
                                    中文
                                </div>
                                <div
                                    class="menu-sub-item"
                                    :class="{
                                        selected: currentLanguage === 'en',
                                    }"
                                    @click="changeLanguage('en')"
                                >
                                    English
                                </div>
                            </div>

                            <div class="menu-divider" />

                            <!-- 主题行 -->
                            <div class="menu-row" @click="toggleThemeOptions">
                                <span class="menu-label">主题</span>
                                <span class="menu-value">
                                    {{ themeLabel }}
                                    <icon-right class="menu-arrow" />
                                </span>
                            </div>
                            <div v-if="showThemeOptions" class="menu-sub">
                                <div
                                    class="menu-sub-item"
                                    :class="{ selected: theme === 'dark' }"
                                    @click="changeTheme('dark')"
                                >
                                    暗色
                                </div>
                                <div
                                    class="menu-sub-item"
                                    :class="{ selected: theme === 'light' }"
                                    @click="changeTheme('light')"
                                >
                                    明亮
                                </div>
                            </div>

                            <div class="menu-divider" />

                            <!-- 退出行 -->
                            <div
                                class="menu-row logout-row"
                                @click="handleLogout"
                            >
                                <span class="menu-label">退出登录</span>
                            </div>
                        </div>
                    </template>
                </a-popover>
            </div>
        </a-layout-sider>
        <a-layout-content class="content">
            <router-view />
        </a-layout-content>
    </a-layout>
</template>

<script setup>
import { ref, computed, watch } from "vue";
import { useRouter, useRoute } from "vue-router";
import {
    IconDashboard,
    IconCommon,
    IconStorage,
    IconFolder,
    IconThunderbolt,
    IconSafe,
    IconCloudDownload,
    IconSettings,
    IconLeft,
    IconRight,
    IconCopy,
} from "@arco-design/web-vue/es/icon";
import { Message } from "@arco-design/web-vue";
import request from "@/utils/request";
import { onMounted, onUnmounted } from "vue";

const router = useRouter();
const route = useRoute();
const collapsed = ref(false);
const theme = ref(localStorage.getItem("theme") || "dark");
const currentLanguage = ref(localStorage.getItem("language") || "zh");
const userPopupVisible = ref(false);
const showLangOptions = ref(false);
const showThemeOptions = ref(false);
const username = ref("Admin");
const userInitial = ref("A");

const selectedKey = computed(() => route.name);
const languageLabel = computed(() =>
    currentLanguage.value === "zh" ? "中文" : "English",
);
const themeLabel = computed(() => (theme.value === "dark" ? "暗色" : "明亮"));

// 服务器 IP（进入面板时获取一次）
const serverIp = ref("");
const fetchServerIp = async () => {
    try {
        const res = await request.get("/system/status");
        serverIp.value = res?.ip || "";
    } catch (error) {
        console.error(error);
    }
};

const copyServerIp = async () => {
    if (!serverIp.value) return;
    try {
        if (navigator.clipboard?.writeText) {
            await navigator.clipboard.writeText(serverIp.value);
        } else {
            // 非 HTTPS 环境下 navigator.clipboard 不可用，使用兼容写法
            const textarea = document.createElement("textarea");
            textarea.value = serverIp.value;
            textarea.style.position = "fixed";
            textarea.style.opacity = "0";
            document.body.appendChild(textarea);
            textarea.select();
            document.execCommand("copy");
            document.body.removeChild(textarea);
        }
        Message.success("IP 已复制");
    } catch (error) {
        Message.error("复制失败，请手动复制");
    }
};

// title
let expectedTitle = "";
const setPageTitle = (r) => {
    const title = r.meta?.title || "三国面板";
    const fullTitle = title ? `${title} - 三国面板` : "三国面板";
    expectedTitle = fullTitle;
    document.title = fullTitle;
};
watch(route, (r) => setPageTitle(r), { immediate: true });
const restoreTitle = () => {
    if (document.title !== expectedTitle && expectedTitle)
        document.title = expectedTitle;
};
const titleInterval = setInterval(restoreTitle, 500);
window.__titleInterval = titleInterval;

const onCollapse = (val) => {
    collapsed.value = val;
    if (val) userPopupVisible.value = false;
};

const onPopupVisibleChange = (visible) => {
    userPopupVisible.value = visible;
    if (!visible) {
        showLangOptions.value = false;
        showThemeOptions.value = false;
    }
};

const toggleLangOptions = () => {
    showLangOptions.value = !showLangOptions.value;
    showThemeOptions.value = false;
};
const toggleThemeOptions = () => {
    showThemeOptions.value = !showThemeOptions.value;
    showLangOptions.value = false;
};

const applyTheme = (val) => {
    if (val === "dark") {
        document.body.setAttribute("arco-theme", "dark");
        document.documentElement.setAttribute("arco-theme", "dark");
        document.body.style.backgroundColor = "#000000";
    } else {
        document.body.removeAttribute("arco-theme");
        document.documentElement.removeAttribute("arco-theme");
        document.body.style.backgroundColor = "";
    }
    localStorage.setItem("theme", val);
};
const changeTheme = (newTheme) => {
    theme.value = newTheme;
    applyTheme(newTheme);
    userPopupVisible.value = false;
};
const changeLanguage = (lang) => {
    currentLanguage.value = lang;
    localStorage.setItem("language", lang);
    userPopupVisible.value = false;
};
const handleLogout = () => {
    localStorage.removeItem("token");
    router.push("/login");
};

onMounted(() => {
    applyTheme(theme.value);
    fetchServerIp();
});
onUnmounted(() => {
    const t = window.__titleInterval;
    if (t) clearInterval(t);
});

const handleMenuClick = (key) => {
    router.push({ name: key });
};
</script>

<style scoped lang="scss">
.layout-container {
    height: 100vh;
    background-color: var(--color-bg-1);
}

.arco-layout-sider {
    display: flex;
    flex-direction: column;
    height: 100vh;
    background: var(--color-bg-2);
    border-right: 1px solid var(--color-border-2);
    overflow: hidden;
}

.arco-layout-sider :deep(.arco-layout-sider-children) {
    display: flex;
    flex-direction: column;
    height: 100%;
}

.arco-layout-sider :deep(.arco-layout-sider-trigger) {
    display: none !important;
}

.sider-content {
    flex: 1;
    overflow-y: auto;
    padding: 12px 0 52px 0;
    min-height: 0;
}

.logo-wrapper {
    display: flex;
    align-items: center;
    justify-content: space-between;
    height: 64px;
    padding: 0 16px;
    background: var(--color-bg-2);

    /* 折叠时隐藏 logo，折叠按钮居中 */
    &:has(.collapse-btn-collapsed) {
        justify-content: center;
    }
}

.logo {
    color: var(--color-text-1);
    font-size: 18px;
    font-weight: 600;
    white-space: nowrap;
}

.wp-menu-icon {
    width: 14px;
    height: 14px;
    flex-shrink: 0;
    fill: currentColor;
    color: var(--color-text-3, #86909c);
}

.ip-wrapper {
    display: flex;
    align-items: center;
    gap: 4px;
    padding: 8px 16px 10px;
    font-size: 12px;
    color: var(--color-text-3);
    cursor: pointer;
    user-select: none;
    transition: background-color 0.15s;

    &:hover {
        background-color: var(--color-fill-2);
        color: var(--color-text-1);

        .ip-copy {
            color: var(--color-primary);
        }
    }
}
.ip-text {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}
.ip-copy {
    flex-shrink: 0;
    font-size: 14px;
}

.collapse-btn {
    width: 28px;
    height: 28px;
    padding: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 6px;
    color: var(--color-text-3);
    flex-shrink: 0;

    &:hover {
        background-color: var(--color-fill-2);
        color: var(--color-text-1);
    }
}

.user-area-wrapper {
    position: absolute;
    bottom: 0;
    left: 0;
    right: 0;
    border-top: 1px solid var(--color-border-2);
    background: var(--color-bg-2);
}

.user-trigger {
    display: flex;
    align-items: center;
    padding: 10px 16px;
    cursor: pointer;
    transition: background-color 0.2s;

    &:hover {
        background-color: var(--color-fill-2);
    }

    &.collapsed {
        justify-content: center;
        padding: 10px 0;
    }
}

.user-info {
    margin-left: 10px;
    min-width: 0;
    overflow: hidden;
}

.username {
    display: block;
    font-size: 13px;
    font-weight: 500;
    color: var(--color-text-1);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

.content {
    padding: 16px 20px;
    overflow-y: auto;
    background-color: var(--color-bg-1);
    flex: 1;
}

.content :deep(.arco-typography) {
    margin-top: 0;
}
</style>

<style lang="scss">
/* Popover 菜单 — 非 scoped，因为 a-popover 内容渲染在 body */
.user-popover-content {
    padding: 0 !important;
    min-width: 180px;
    background: var(--color-bg-4) !important;
    border: 1px solid var(--color-border-2) !important;
    border-radius: 6px;
    box-shadow: 0 -4px 12px rgba(0, 0, 0, 0.35) !important;
}

.popover-menu {
    padding: 6px 0;
}

.menu-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 9px 14px;
    cursor: pointer;
    font-size: 13px;
    color: var(--color-text-1);
    transition: background-color 0.15s;

    &:hover {
        background-color: var(--color-fill-2);
    }

    &.logout-row {
        color: var(--arco-red-6);

        &:hover {
            background-color: var(--arco-red-1);
        }
    }
}

.menu-label {
    font-weight: 500;
}

.menu-value {
    display: flex;
    align-items: center;
    gap: 2px;
    color: var(--color-text-3);
    font-size: 12px;
}

.menu-arrow {
    font-size: 11px;
    color: var(--color-text-3);
}

.menu-sub {
    background: var(--color-fill-1);
}

.menu-sub-item {
    padding: 9px 14px 9px 28px;
    cursor: pointer;
    font-size: 13px;
    color: var(--color-text-1);
    transition: background-color 0.15s;

    &:hover {
        background-color: var(--color-fill-2);
    }

    &.selected {
        color: var(--arco-blue-6);
        font-weight: 500;
        background-color: var(--arco-blue-1);
    }
}

.menu-divider {
    height: 1px;
    margin: 4px 10px;
    background-color: var(--color-border-1);
}
</style>
