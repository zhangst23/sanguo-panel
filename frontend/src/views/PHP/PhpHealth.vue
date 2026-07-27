<template>
  <a-card title="Health (健康检查)" :bordered="false">
    <a-spin :loading="loading" style="width: 100%;">
      <a-space direction="vertical" fill>
        <a-progress
          :percent="health.score"
          :status="health.status === 'healthy' ? 'success' : (health.status === 'warning' ? 'warning' : 'error')"
          :color="health.status === 'healthy' ? '#00b42a' : (health.status === 'warning' ? '#ff7d00' : '#f53f3f')"
        />
        <a-descriptions :column="2" bordered size="medium">
          <a-descriptions-item label="总体状态">
            <a-tag :color="health.status === 'healthy' ? 'green' : (health.status === 'warning' ? 'orange' : 'red')">
              {{ statusText }}
            </a-tag>
          </a-descriptions-item>
          <a-descriptions-item label="PHP 版本">{{ health.php_version || '-' }}</a-descriptions-item>
          <a-descriptions-item label="Worker 运行">
            <a-tag :color="health.worker_running ? 'green' : 'red'">
              {{ health.worker_running ? `运行中 (${health.worker_count})` : '未运行' }}
            </a-tag>
          </a-descriptions-item>
          <a-descriptions-item label="OPcache">
            <a-tag :color="health.opcache_enabled ? 'green' : 'red'">
              {{ health.opcache_enabled ? '已启用' : '未启用' }}
            </a-tag>
          </a-descriptions-item>
        </a-descriptions>
        <a-divider orientation="left">关键扩展</a-divider>
        <a-space wrap>
          <a-tag v-for="(ok, name) in health.extensions || {}" :key="name" :color="ok ? 'green' : 'red'">
            {{ name }}: {{ ok ? 'OK' : '缺失' }}
          </a-tag>
        </a-space>
      </a-space>
    </a-spin>
  </a-card>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import request from '@/utils/request'

const loading = ref(false)
const health = ref({
  score: 0, status: 'unknown', php_version: '', worker_running: false,
  worker_count: 0, opcache_enabled: false, extensions: {},
})

const statusText = computed(() => {
  const map = { healthy: '健康', warning: '警告', critical: '严重', unknown: '未知' }
  return map[health.value.status] || health.value.status
})

const fetchHealth = async () => {
  loading.value = true
  try {
    health.value = await request.get('/php/health')
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
}

onMounted(fetchHealth)
</script>
