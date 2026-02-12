<template>
  <div class="redis-container">
    <a-typography-title :heading="2">Redis & Cache Management</a-typography-title>
    
    <a-row :gutter="20">
      <!-- Redis Service -->
      <a-col :span="12">
        <a-card title="Redis Service" hoverable>
          <template #extra>
            <a-tag color="green">RUNNING</a-tag>
          </template>
          <a-space direction="vertical" size="large" fill>
            <a-row>
              <a-col :span="12">
                <a-statistic title="Memory Used" :value="4.2" unit="MB" />
              </a-col>
              <a-col :span="12">
                <a-statistic title="Uptime" :value="15" unit="Days" />
              </a-col>
            </a-row>
            <a-space>
              <a-button type="primary" @click="handleAction('redis', 'restart')" :loading="loading.redis">
                <template #icon><icon-refresh /></template>
                Restart
              </a-button>
              <a-button status="danger" @click="handleFlush" :loading="loading.flush">
                <template #icon><icon-delete /></template>
                Flush All Keys
              </a-button>
            </a-space>
          </a-space>
        </a-card>
      </a-col>

      <!-- Object Cache Status -->
      <a-col :span="12">
        <a-card title="Object Cache (LSCache)" hoverable>
          <template #extra>
            <a-tag color="blue">ENABLED</a-tag>
          </template>
          <a-space direction="vertical" size="large" fill>
            <div class="info-item">
              <span>Cache Engine:</span>
              <a-tag>LiteSpeed Native</a-tag>
            </div>
            <div class="info-item">
              <span>Hit Rate:</span>
              <a-progress :percent="0.85" size="small" />
            </div>
            <a-button type="outline" long @click="handlePurge" :loading="loading.purge">
              Purge All LSCache
            </a-button>
          </a-space>
        </a-card>
      </a-col>
    </a-row>
  </div>
</template>

<script setup>
import { reactive } from 'vue'
import request from '@/utils/request'
import { Message } from '@arco-design/web-vue'

const loading = reactive({
  redis: false,
  flush: false,
  purge: false
})

const handleAction = async (service, action) => {
  loading[service] = true
  try {
    await request.post(`/services/${service}/${action}`)
    Message.success(`${service} ${action}ed successfully`)
  } catch (error) {
    console.error(error)
  } finally {
    loading[service] = false
  }
}

const handleFlush = async () => {
  loading.flush = true
  try {
    // Mock flush command
    await new Promise(resolve => setTimeout(resolve, 1000))
    Message.success('Redis flushed successfully')
  } catch (error) {
    console.error(error)
  } finally {
    loading.flush = false
  }
}

const handlePurge = async () => {
  loading.purge = true
  try {
    // Mock purge command
    await new Promise(resolve => setTimeout(resolve, 1000))
    Message.success('LSCache purged successfully')
  } catch (error) {
    console.error(error)
  } finally {
    loading.purge = false
  }
}
</script>

<style scoped>
.info-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}
</style>
