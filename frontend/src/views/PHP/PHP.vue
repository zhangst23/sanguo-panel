<template>
  <div class="php-runtime">
    <div class="php-subnav">
      <button
        v-for="t in subTabs"
        :key="t.key"
        :class="['subnav-item', { active: active === t.key }]"
        @click="active = t.key"
      >
        <span class="dot" :style="{ background: t.color }"></span>
        <span class="subnav-title">{{ t.title }}</span>
        <span class="subnav-sub">{{ t.sub }}</span>
      </button>
    </div>

    <div class="php-subcontent">
      <component :is="compMap[active]" />
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import PhpVersions from './PhpVersions.vue'
import PhpExtensions from './PhpExtensions.vue'
import PhpRuntimeConfig from './PhpRuntimeConfig.vue'
import PhpOpcache from './PhpOpcache.vue'
import PhpWorkerPool from './PhpWorkerPool.vue'
import PhpWorkerMonitor from './PhpWorkerMonitor.vue'
import PhpHealth from './PhpHealth.vue'
import PhpAutoScaling from './PhpAutoScaling.vue'
import PhpAiOptimizer from './PhpAiOptimizer.vue'

const active = ref('versions')

const subTabs = [
  { key: 'versions', title: 'Versions', sub: 'PHP 版本', color: '#165DFF' },
  { key: 'extensions', title: 'Extensions', sub: '扩展管理', color: '#722ED1' },
  { key: 'config', title: 'Runtime Config', sub: 'php.ini', color: '#0FC6C2' },
  { key: 'opcache', title: 'Opcache', sub: '字节码缓存', color: '#F77234' },
  { key: 'workerpool', title: 'Worker Pool', sub: 'Worker 配置', color: '#3491FA' },
  { key: 'workermonitor', title: 'Worker Monitor', sub: '实时监控', color: '#14C9C9' },
  { key: 'health', title: 'Health', sub: '健康检查', color: '#00B42A' },
  { key: 'autoscaling', title: 'Auto Scaling', sub: '自动伸缩', color: '#FF7D00' },
  { key: 'ai', title: 'AI Optimizer', sub: 'AI 优化建议', color: '#F5319D' },
]

const compMap = {
  versions: PhpVersions,
  extensions: PhpExtensions,
  config: PhpRuntimeConfig,
  opcache: PhpOpcache,
  workerpool: PhpWorkerPool,
  workermonitor: PhpWorkerMonitor,
  health: PhpHealth,
  autoscaling: PhpAutoScaling,
  ai: PhpAiOptimizer,
}

const currentComp = computed(() => compMap[active.value])
</script>

<style scoped>
.php-runtime {
  padding: 0;
}
.php-subnav {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  margin-bottom: 20px;
}
.subnav-item {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 4px;
  padding: 12px 14px;
  border: 1px solid var(--color-border-2, #e5e6eb);
  border-radius: 8px;
  background: var(--color-bg-2, #fff);
  cursor: pointer;
  text-align: left;
  transition: all 0.2s;
}
.subnav-item:hover {
  border-color: rgb(var(--primary-6, #165dff));
}
.subnav-item.active {
  border-color: rgb(var(--primary-6, #165dff));
  box-shadow: 0 0 0 2px rgba(22, 93, 255, 0.15);
  background: rgba(22, 93, 255, 0.04);
}
.dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  display: inline-block;
}
.subnav-title {
  font-weight: 600;
  font-size: 14px;
  color: var(--color-text-1, #1d2129);
}
.subnav-sub {
  font-size: 12px;
  color: var(--color-text-3, #86909c);
}
</style>
