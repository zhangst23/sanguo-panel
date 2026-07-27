<template>
  <div class="log-container">
    <a-card title="OpenLiteSpeed 错误日志">
      <template #extra>
        <a-button :loading="loading" @click="loadLog">
          <template #icon><icon-refresh /></template>
          刷新
        </a-button>
      </template>
      <a-spin :loading="loading">
        <pre class="log-view">{{ log || '暂无日志' }}</pre>
      </a-spin>
    </a-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import request from '@/utils/request'

const loading = ref(false)
const log = ref('')

const loadLog = async () => {
  loading.value = true
  try {
    const res = await request.get('/litespeed/log')
    log.value = res.log || ''
  } catch (error) {
    console.error(error)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadLog()
})
</script>

<style scoped>
.log-container {
  padding: 0;
}
.log-view {
  background: var(--color-fill-1);
  padding: 12px;
  border-radius: 4px;
  max-height: 60vh;
  overflow: auto;
  font-family: monospace;
  font-size: 12px;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-all;
}
</style>
