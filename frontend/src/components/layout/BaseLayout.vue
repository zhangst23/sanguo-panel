<template>
  <a-layout class="layout-container">
    <a-layout-sider
      breakpoint="lg"
      :width="220"
      collapsible
      :collapsed="collapsed"
      @collapse="onCollapse"
    >
      <div class="logo">
        <span v-if="!collapsed">SanGuoWP面板</span>
        <span v-else>SG</span>
      </div>
      <div class="sider-content">
        <a-menu
          :selected-keys="[selectedKey]"
          :auto-open-selected="true"
          @menu-item-click="handleMenuClick"
        >
          <a-menu-item key="Dashboard">
            <template #icon><icon-dashboard /></template>
            仪表盘
          </a-menu-item>
          <a-menu-item key="Website">
            <template #icon><icon-common /></template>
            站点管理
          </a-menu-item>
          <a-menu-item key="MariaDB">
            <template #icon><icon-storage /></template>
            数据库管理
          </a-menu-item>
          <a-menu-item key="OneClickTools">
            <template #icon><icon-thunderbolt /></template>
            一键工具
          </a-menu-item>
          <a-menu-item key="Security">
            <template #icon><icon-safe /></template>
            安全中心
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
            <template #title>系统管理</template>
            <a-menu-item key="Monitor">监控中心</a-menu-item>
            <a-menu-item key="Redis">Redis</a-menu-item>
            <a-menu-item key="PHP">PHP</a-menu-item>
            <a-menu-item key="LiteSpeed">OpenLiteSpeed</a-menu-item>
            <a-menu-item key="Linux">Linux</a-menu-item>
            <a-menu-item key="ApiDocs">API 接口文档</a-menu-item>
            <a-menu-item key="SystemSettings">系统设置</a-menu-item>
          </a-sub-menu>
        </a-menu>
      </div>
      <div class="sider-footer">
        <a-space direction="vertical" fill size="medium" align="center">
          <a-space :size="collapsed ? 0 : 'medium'" class="footer-actions">
            <a-button type="text" @click="toggleTheme" size="small">
              <template #icon>
                <icon-moon-fill v-if="theme === 'light'" />
                <icon-sun-fill v-else />
              </template>
            </a-button>
            <a-badge :count="3" v-if="!collapsed">
              <a-button type="text" size="small"><icon-notification /></a-button>
            </a-badge>
            <a-dropdown @select="handleUserAction">
              <a-avatar :size="24" style="cursor: pointer; background-color: var(--arco-blue-6)">
                A
              </a-avatar>
              <template #content>
                <a-doption value="profile">Profile</a-doption>
                <a-doption value="logout">Logout</a-doption>
              </template>
            </a-dropdown>
          </a-space>
          <a-button type="text" @click="onCollapse(!collapsed)" class="collapse-btn">
            <icon-menu-fold v-if="!collapsed" />
            <icon-menu-unfold v-else />
          </a-button>
        </a-space>
      </div>
    </a-layout-sider>
    <a-layout>
      <a-layout-content class="content">
        <router-view />
      </a-layout-content>
    </a-layout>
  </a-layout>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import {
  IconDashboard,
  IconCommon,
  IconStorage,
  IconThunderbolt,
  IconSafe,
  IconCloudDownload,
  IconSettings,
  IconMenuFold,
  IconMenuUnfold,
  IconNotification,
  IconList,
  IconMoonFill,
  IconSunFill
} from '@arco-design/web-vue/es/icon'
import { onMounted } from 'vue'

const router = useRouter()
const route = useRoute()
const collapsed = ref(false)
const theme = ref(localStorage.getItem('theme') || 'dark')

const selectedKey = computed(() => route.name)

const onCollapse = (val) => {
  collapsed.value = val
}

const toggleTheme = () => {
  const newTheme = theme.value === 'light' ? 'dark' : 'light'
  theme.value = newTheme
  applyTheme(newTheme)
}

const applyTheme = (val) => {
  if (val === 'dark') {
    document.body.setAttribute('arco-theme', 'dark')
    document.documentElement.setAttribute('arco-theme', 'dark')
    // 强制更新 body 背景色
    document.body.style.backgroundColor = '#000000'
  } else {
    document.body.removeAttribute('arco-theme')
    document.documentElement.removeAttribute('arco-theme')
    document.body.style.backgroundColor = ''
  }
  localStorage.setItem('theme', val)
}

onMounted(() => {
  applyTheme(theme.value)
})

const handleMenuClick = (key) => {
  if (key === 'ApiDocs') {
    window.open('/api-docs', '_blank')
    return
  }
  console.log('Menu click:', key)
  router.push({ name: key })
}

const handleUserAction = (val) => {
  if (val === 'logout') {
    localStorage.removeItem('token')
    router.push('/login')
  }
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
}

.sider-content {
  flex: 1;
  overflow-y: auto;
}

.sider-footer {
  padding: 16px 0;
  border-top: 1px solid var(--arco-color-border-1);
  background: var(--arco-color-bg-2);
}

.footer-actions {
  margin-bottom: 8px;
  width: 100%;
  display: flex;
  justify-content: center;
}

.collapse-btn {
  width: 100%;
  display: flex;
  justify-content: center;
}

.logo {
  height: 64px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 18px;
  font-weight: bold;
  background: var(--arco-color-bg-2);
  border-bottom: 1px solid var(--arco-color-border-1);
  img {
    width: 32px;
    margin-right: 10px;
  }
}

.content {
  padding: 20px;
  overflow-y: auto;
  background-color: var(--arco-color-bg-1);
}
</style>
