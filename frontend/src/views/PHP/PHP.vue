<template>
  <div class="php-container">
    <a-typography-title :heading="2">PHP Management</a-typography-title>
    
    <a-row :gutter="20">
      <a-col :span="12" v-for="version in phpVersions" :key="version">
        <a-card :title="`PHP ${version}`" hoverable style="margin-bottom: 20px">
          <template #extra>
            <a-tag color="green">RUNNING</a-tag>
          </template>
          <a-space direction="vertical" size="large" fill>
            <div class="status-item">
              <span>Service Name:</span>
              <a-tag>lsphp{{ version.replace('.', '') }}</a-tag>
            </div>
            <a-space>
              <a-button type="primary" @click="handleAction(version, 'restart')" :loading="loading[version]">
                <template #icon><icon-refresh /></template>
                Restart
              </a-button>
              <a-button @click="handleAction(version, 'reload')" :loading="loading[version]">
                <template #icon><icon-sync /></template>
                Reload
              </a-button>
            </a-space>
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

const phpVersions = ['8.2', '8.1', '7.4']
const loading = reactive({
  '8.2': false,
  '8.1': false,
  '7.4': false
})

const handleAction = async (version, action) => {
  const serviceName = `lsphp${version.replace('.', '')}`
  loading[version] = true
  try {
    await request.post(`/services/${serviceName}/${action}`)
    Message.success(`PHP ${version} ${action}ed successfully`)
  } catch (error) {
    console.error(error)
  } finally {
    loading[version] = false
  }
}
</script>

<style scoped>
.status-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>
