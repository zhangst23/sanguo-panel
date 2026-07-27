<template>
  <a-card title="Worker Monitor (实时监控)" :bordered="false">
    <template #extra>
      <a-space>
        <a-button size="small" @click="fetchWorker"><icon-refresh /> 刷新</a-button>
        <a-button type="primary" size="small" :loading="restarting" @click="restart">
          <template #icon><icon-refresh /></template>重启 Worker
        </a-button>
      </a-space>
    </template>
    <a-descriptions :column="2" bordered size="medium">
      <a-descriptions-item label="运行状态">
        <a-tag :color="worker.running ? 'green' : 'red'">{{ worker.running ? '运行中' : '已停止' }}</a-tag>
      </a-descriptions-item>
      <a-descriptions-item label="PHP 版本">{{ worker.version || '-' }}</a-descriptions-item>
      <a-descriptions-item label="Worker 进程数">{{ worker.count }}</a-descriptions-item>
      <a-descriptions-item label="内存占用">{{ worker.memory_mb }} MB</a-descriptions-item>
    </a-descriptions>
  </a-card>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import request from '@/utils/request'
import { Message } from '@arco-design/web-vue'

const restarting = ref(false)
const worker = ref({ running: false, version: '', count: 0, memory_mb: 0 })

const fetchWorker = async () => {
  try {
    worker.value = await request.get('/php/worker')
  } catch (e) {
    console.error(e)
  }
}

const restart = async () => {
  restarting.value = true
  try {
    await request.post('/litespeed/action/restart')
    Message.success('PHP Worker 已重启')
    await fetchWorker()
  } catch (e) {
    console.error(e)
  } finally {
    restarting.value = false
  }
}

onMounted(fetchWorker)
</script>
