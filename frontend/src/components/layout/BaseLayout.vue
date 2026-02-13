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
        <span v-if="!collapsed">三国WP面板</span>
        <span v-else>SG</span>
      </div>
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
    </a-layout-sider>
    <a-layout>
      <a-layout-header class="header">
        <div class="header-left">
          <a-button type="text" @click="onCollapse(!collapsed)">
            <icon-menu-fold v-if="!collapsed" />
            <icon-menu-unfold v-else />
          </a-button>
        </div>
        <div class="header-right">
          <a-space size="large">
            <a-badge :count="3">
              <a-button type="text"><icon-notification /></a-button>
            </a-badge>
            <a-dropdown @select="handleUserAction">
              <a-avatar :size="32" style="cursor: pointer; background-color: var(--arco-blue-6)">
                A
              </a-avatar>
              <template #content>
                <a-doption value="profile">Profile</a-doption>
                <a-doption value="logout">Logout</a-doption>
              </template>
            </a-dropdown>
          </a-space>
        </div>
      </a-layout-header>
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
  IconNotification
} from '@arco-design/web-vue/es/icon'

const router = useRouter()
const route = useRoute()
const collapsed = ref(false)

const selectedKey = computed(() => route.name)

const onCollapse = (val) => {
  collapsed.value = val
}

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
}

.logo {
  height: 64px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 18px;
  font-weight: bold;
  background: #001529;
  img {
    width: 32px;
    margin-right: 10px;
  }
}

.header {
  height: 64px;
  background: #fff;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
  box-shadow: 0 1px 4px rgba(0, 21, 41, 0.08);
  z-index: 100;
}

.content {
  padding: 20px;
  overflow-y: auto;
  background-color: var(--arco-gray-2);
}
</style>
