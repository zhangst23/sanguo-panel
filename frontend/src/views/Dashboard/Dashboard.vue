<template>
  <div class="dashboard-container">
    <a-typography-title :heading="2">仪表盘</a-typography-title>
    <a-row :gutter="20">
      <a-col :span="8">
        <a-card title="CPU 使用率" hoverable>
          <a-statistic :value="metrics.cpu.percent" :precision="1" suffix="%" />
          <template #extra>
            <a-tag color="blue">{{ metrics.cpu.count }} 核心</a-tag>
          </template>
        </a-card>
      </a-col>
      <a-col :span="8">
        <a-card title="内存使用率" hoverable>
          <a-statistic :value="metrics.memory.percent" :precision="1" suffix="%" />
          <div style="margin-top: 10px; font-size: 12px; color: var(--arco-gray-6)">
            已用: {{ (metrics.memory.used / 1024 / 1024 / 1024).toFixed(2) }} GB / 
            总量: {{ (metrics.memory.total / 1024 / 1024 / 1024).toFixed(2) }} GB
          </div>
        </a-card>
      </a-col>
      <a-col :span="8">
        <a-card title="磁盘使用率" hoverable>
          <a-statistic :value="metrics.disk.percent" :precision="1" suffix="%" />
          <div style="margin-top: 10px; font-size: 12px; color: var(--arco-gray-6)">
            已用: {{ (metrics.disk.used / 1024 / 1024 / 1024).toFixed(2) }} GB / 
            总量: {{ (metrics.disk.total / 1024 / 1024 / 1024).toFixed(2) }} GB
          </div>
        </a-card>
      </a-col>
    </a-row>
  </div>
</template>

<script setup>
import { reactive, onMounted, onUnmounted } from 'vue'
import request from '@/utils/request'

const metrics = reactive({
  cpu: { percent: 0, count: 0 },
  memory: { total: 0, used: 0, percent: 0 },
  disk: { total: 0, used: 0, percent: 0 }
})

let timer = null

const fetchMetrics = async () => {
  try {
    const res = await request.get('/system/metrics')
    Object.assign(metrics, res)
  } catch (error) {
    console.error(error)
  }
}

onMounted(() => {
  fetchMetrics()
  timer = setInterval(fetchMetrics, 3000)
})

onUnmounted(() => {
  if (timer) clearInterval(timer)
})
</script>

<style scoped>
.dashboard-container {
  padding: 20px;
}
</style>
