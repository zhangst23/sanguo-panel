<template>
  <div class="system-manage-container">
    <a-typography-title :heading="2">系统管理</a-typography-title>

    <a-tabs v-model:active-key="activeTab" @change="onTabChange">
      <a-tab-pane key="status" title="系统状态">
        <SystemStatus />
      </a-tab-pane>
      <a-tab-pane key="redis" title="Redis 管理">
        <RedisManager />
      </a-tab-pane>
      <a-tab-pane key="php" title="PHP Runtime 管理">
        <PHPManager />
      </a-tab-pane>
      <a-tab-pane key="linux" title="Linux 管理">
        <LinuxManager />
      </a-tab-pane>
      <a-tab-pane key="ols" title="OLS 虚拟主机管理">
        <OLSManager />
      </a-tab-pane>
      <a-tab-pane key="lscache" title="LSCache">
        <LSCacheManager />
      </a-tab-pane>
      <a-tab-pane key="rewrite" title="Rewrite">
        <RewriteManager />
      </a-tab-pane>
      <a-tab-pane key="log" title="Log">
        <LogManager />
      </a-tab-pane>
    </a-tabs>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import RedisManager from '@/views/Redis/Redis.vue'
import PHPManager from '@/views/PHP/PHP.vue'
import LinuxManager from '@/views/Linux/Linux.vue'
import OLSManager from '@/views/LiteSpeed/LiteSpeed.vue'
import SystemStatus from '@/views/System/SystemStatus.vue'
import LSCacheManager from '@/views/LiteSpeed/LSCache.vue'
import RewriteManager from '@/views/LiteSpeed/Rewrite.vue'
import LogManager from '@/views/LiteSpeed/Log.vue'

const route = useRoute()
const router = useRouter()

const TAB_KEYS = ['status', 'redis', 'php', 'linux', 'ols', 'lscache', 'rewrite', 'log']
const activeTab = ref(getInitialTab())

function getInitialTab() {
  if (route.query.tab && TAB_KEYS.includes(route.query.tab)) return route.query.tab
  if (route.meta.defaultTab && TAB_KEYS.includes(route.meta.defaultTab)) return route.meta.defaultTab
  return 'status'
}

const onTabChange = (key) => {
  // 同步到路由，便于分享/刷新后保持当前标签
  router.replace({ query: { ...route.query, tab: key } }).catch(() => {})
}

// 复用同一组件实例时，路由切换（侧边栏 Redis/PHP/Linux/Nginx 互切）需同步标签
watch(
  () => route.fullPath,
  () => {
    const t = getInitialTab()
    if (t !== activeTab.value) activeTab.value = t
  }
)
</script>

<style scoped>
.system-manage-container {
  padding: 0;
}
</style>
