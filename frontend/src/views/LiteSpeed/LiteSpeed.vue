<template>
  <div class="litespeed-container">
    <a-typography-title :heading="2">LiteSpeed Management</a-typography-title>
    
    <a-row :gutter="20">
      <a-col :span="12">
        <a-card title="Service Status" hoverable>
          <template #extra>
            <a-tag :color="status === 'running' ? 'green' : 'red'">{{ status.toUpperCase() }}</a-tag>
          </template>
          <a-space direction="vertical" size="large" fill>
            <div class="status-item">
              <span>Main Process:</span>
              <a-tag color="blue">Running</a-tag>
            </div>
            <div class="status-item">
              <span>Version:</span>
              <a-tag>OpenLiteSpeed 1.7.19</a-tag>
            </div>
            <a-space>
              <a-button type="primary" @click="handleAction('restart')" :loading="loading">
                <template #icon><icon-refresh /></template>
                Restart
              </a-button>
              <a-button @click="handleAction('reload')" :loading="loading">
                <template #icon><icon-sync /></template>
                Reload Config
              </a-button>
            </a-space>
          </a-space>
        </a-card>
      </a-col>
    </a-row>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import request from '@/utils/request'
import { Message } from '@arco-design/web-vue'

const status = ref('unknown')
const loading = ref(false)

const fetchStatus = async () => {
  try {
    const res = await request.get('/services/lsws/status')
    status.value = res.status
  } catch (error) {
    console.error(error)
  }
}

const handleAction = async (action) => {
  loading.value = true
  try {
    await request.post(`/services/lsws/${action}`)
    Message.success(`LiteSpeed ${action}ed successfully`)
    await fetchStatus()
  } catch (error) {
    console.error(error)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchStatus()
})
</script>

<style scoped>
.status-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}
</style>
