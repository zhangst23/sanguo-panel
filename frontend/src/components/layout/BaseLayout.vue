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

      <!-- 菜单 -->
      <div class="sider-content">
        <a-menu
          :selected-keys="[selectedKey]"
          :auto-open-selected="true"
          @menu-item-click="handleMenuClick"
          :collapsed="collapsed"
          mode="vertical"
          theme="dark"
        >
          <a-menu-item key="Dashboard">
            <template #icon><icon-dashboard /></template>
            仪表盘
          </a-menu-item>
          <a-menu-item key="Website">
            <template #icon><icon-common /></template>
            网站管理
          </a-menu-item>
          <a-menu-item key="MariaDB">
            <template #icon><icon-storage /></template>
            数据库管理
          </a-menu-item>
          <a-menu-item key="FileManager">
            <template #icon><icon-folder /></template>
            文件管理
          </a-menu-item>
          <a-menu-item key="OneClickTools">
            <template #icon><icon-thunderbolt /></template>
            AI工具
          </a-menu-item>
          <a-menu-item key="Security">
            <template #icon><icon-safe /></template>
            安全防御
          </a-menu-item>
          <a-menu-item key="Backup">
            <template #icon><icon-cloud-download /></template>
            备份迁移
          </a-menu-item>
          <a-menu-item key="TaskList">
            <template #icon><icon-list /></template>
            任务列表
          </a-menu-item>
          <a-sub-menu key="System">
            <template #icon><icon-settings /></template>
            <template #title>系统工具</template>
            <a-menu-item key="Linux">系统管理</a-menu-item>
            <a-menu-item key="Monitor">监控中心</a-menu-item>
            <a-menu-item key="Nginx">OpenLiteSpeed 管理</a-menu-item>
            <a-menu-item key="LiteSpeed">OpenLiteSpeed</a-menu-item>
            <a-menu-item key="ApiDocs">API 接口文档</a-menu-item>
            <a-menu-item key="SystemSettings">系统设置</a-menu-item>
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
              style="background-color: var(--arco-blue-6); flex-shrink: 0;"
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
                  :class="{ selected: currentLanguage === 'zh' }"
                  @click="changeLanguage('zh')"
                >中文</div>
                <div
                  class="menu-sub-item"
                  :class="{ selected: currentLanguage === 'en' }"
                  @click="changeLanguage('en')"
                >English</div>
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
                >暗色</div>
                <div
                  class="menu-sub-item"
                  :class="{ selected: theme === 'light' }"
                  @click="changeTheme('light')"
                >明亮</div>
              </div>

              <div class="menu-divider" />

              <!-- 退出行 -->
              <div class="menu-row logout-row" @click="handleLogout">
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
import { ref, computed, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import {
  IconDashboard,
  IconCommon,
  IconStorage,
  IconFolder,
  IconThunderbolt,
  IconSafe,
  IconCloudDownload,
  IconSettings,
  IconList,
  IconLeft,
  IconRight,
} from '@arco-design/web-vue/es/icon'
import { onMounted, onUnmounted } from 'vue'

const router = useRouter()
const route = useRoute()
const collapsed = ref(false)
const theme = ref(localStorage.getItem('theme') || 'dark')
const currentLanguage = ref(localStorage.getItem('language') || 'zh')
const userPopupVisible = ref(false)
const showLangOptions = ref(false)
const showThemeOptions = ref(false)
const username = ref('Admin')
const userInitial = ref('A')

const selectedKey = computed(() => route.name)
const languageLabel = computed(() => currentLanguage.value === 'zh' ? '中文' : 'English')
const themeLabel = computed(() => theme.value === 'dark' ? '暗色' : '明亮')

// title
let expectedTitle = ''
const setPageTitle = (r) => {
  const title = r.meta?.title || '三国面板'
  const fullTitle = title ? `${title} - 三国面板` : '三国面板'
  expectedTitle = fullTitle
  document.title = fullTitle
}
watch(route, (r) => setPageTitle(r), { immediate: true })
const restoreTitle = () => {
  if (document.title !== expectedTitle && expectedTitle) document.title = expectedTitle
}
const titleInterval = setInterval(restoreTitle, 500)
window.__titleInterval = titleInterval

const onCollapse = (val) => {
  collapsed.value = val
  if (val) userPopupVisible.value = false
}

const onPopupVisibleChange = (visible) => {
  userPopupVisible.value = visible
  if (!visible) {
    showLangOptions.value = false
    showThemeOptions.value = false
  }
}

const toggleLangOptions = () => {
  showLangOptions.value = !showLangOptions.value
  showThemeOptions.value = false
}
const toggleThemeOptions = () => {
  showThemeOptions.value = !showThemeOptions.value
  showLangOptions.value = false
}

const applyTheme = (val) => {
  if (val === 'dark') {
    document.body.setAttribute('arco-theme', 'dark')
    document.documentElement.setAttribute('arco-theme', 'dark')
    document.body.style.backgroundColor = '#000000'
  } else {
    document.body.removeAttribute('arco-theme')
    document.documentElement.removeAttribute('arco-theme')
    document.body.style.backgroundColor = ''
  }
  localStorage.setItem('theme', val)
}
const changeTheme = (newTheme) => {
  theme.value = newTheme
  applyTheme(newTheme)
  userPopupVisible.value = false
}
const changeLanguage = (lang) => {
  currentLanguage.value = lang
  localStorage.setItem('language', lang)
  userPopupVisible.value = false
}
const handleLogout = () => {
  localStorage.removeItem('token')
  router.push('/login')
}

onMounted(() => applyTheme(theme.value))
onUnmounted(() => {
  const t = window.__titleInterval
  if (t) clearInterval(t)
})

const handleMenuClick = (key) => {
  if (key === 'ApiDocs') {
    window.open('/api-docs', '_blank')
    return
  }
  router.push({ name: key })
}
</script>

<style scoped lang="scss">
.layout-container {
  height: 100vh;
  background-color: var(--arco-color-bg-1);
}

.arco-layout-sider {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: var(--arco-color-bg-2);
  border-right: 1px solid var(--arco-color-border-1);
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
  background: var(--arco-color-bg-2);
  border-bottom: 1px solid var(--arco-color-border-1);

  /* 折叠时隐藏 logo，折叠按钮居中 */
  &:has(.collapse-btn-collapsed) {
    justify-content: center;
  }
}

.logo {
  color: #fff;
  font-size: 18px;
  font-weight: 600;
  white-space: nowrap;
}

.collapse-btn {
  width: 28px;
  height: 28px;
  padding: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 6px;
  color: #86909c;
  flex-shrink: 0;

  &:hover {
    background-color: var(--arco-color-fill-2);
    color: #c9cdd4;
  }
}

.user-area-wrapper {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  border-top: 1px solid var(--arco-color-border-1);
  background: var(--arco-color-bg-2);
}

.user-trigger {
  display: flex;
  align-items: center;
  padding: 10px 16px;
  cursor: pointer;
  transition: background-color 0.2s;

  &:hover {
    background-color: var(--arco-color-fill-2);
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
  color: #ffffff !important;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.content {
  padding: 16px 20px;
  overflow-y: auto;
  background-color: var(--arco-color-bg-1);
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
  background: var(--arco-color-bg-4) !important;
  border: 1px solid var(--arco-color-border-2) !important;
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
  color: var(--arco-color-text-1);
  transition: background-color 0.15s;

  &:hover {
    background-color: var(--arco-color-fill-2);
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
  color: var(--arco-color-text-3);
  font-size: 12px;
}

.menu-arrow {
  font-size: 11px;
  color: var(--arco-color-text-3);
}

.menu-sub {
  background: var(--arco-color-fill-1);
}

.menu-sub-item {
  padding: 9px 14px 9px 28px;
  cursor: pointer;
  font-size: 13px;
  color: var(--arco-color-text-1);
  transition: background-color 0.15s;

  &:hover {
    background-color: var(--arco-color-fill-2);
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
  background-color: var(--arco-color-border-1);
}</style>