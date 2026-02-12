<template>
  <div class="system-container">
    <a-typography-title :heading="2">System Management</a-typography-title>
    
    <a-tabs default-active-key="1">
      <!-- Basic Config -->
      <a-tab-pane key="1" title="Basic Configuration">
        <a-card style="margin-top: 20px">
          <a-form :model="configForm" layout="vertical">
            <a-form-item field="panel_name" label="Panel Name">
              <a-input v-model="configForm.panel_name" />
            </a-form-item>
            <a-form-item field="language" label="Language">
              <a-select v-model="configForm.language">
                <a-option value="en-US">English</a-option>
                <a-option value="zh-CN">简体中文</a-option>
              </a-select>
            </a-form-item>
            <a-form-item field="timezone" label="Timezone">
              <a-select v-model="configForm.timezone">
                <a-option value="UTC">UTC</a-option>
                <a-option value="Asia/Shanghai">Asia/Shanghai</a-option>
              </a-select>
            </a-form-item>
            <a-button type="primary" @click="saveConfig" :loading="loading.config">Save Configuration</a-button>
          </a-form>
        </a-card>
      </a-tab-pane>

      <!-- Logs -->
      <a-tab-pane key="2" title="System Logs">
        <a-card style="margin-top: 20px">
          <template #extra>
            <a-space>
              <a-select v-model="logType" style="width: 150px">
                <a-option value="panel">Panel Log</a-option>
                <a-option value="error">Error Log</a-option>
                <a-option value="access">Access Log</a-option>
              </a-select>
              <a-button @click="fetchLogs">Refresh</a-button>
            </a-space>
          </template>
          <pre class="log-viewer">{{ logs }}</pre>
        </a-card>
      </a-tab-pane>

      <!-- Update -->
      <a-tab-pane key="3" title="Update">
        <a-card style="margin-top: 20px">
          <a-result status="info" title="Current Version: v1.0.0-beta">
            <template #subtitle>
              Checking for updates...
            </template>
            <template #extra>
              <a-button type="primary" :loading="loading.update" @click="handleUpdate">Check for Updates</a-button>
            </template>
          </a-result>
        </a-card>
      </a-tab-pane>
    </tabs>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { Message } from '@arco-design/web-vue'

const loading = reactive({
  config: false,
  update: false
})

const configForm = reactive({
  panel_name: 'Sanguo Panel',
  language: 'en-US',
  timezone: 'Asia/Shanghai'
})

const logType = ref('panel')
const logs = ref('Loading logs...')

const fetchLogs = async () => {
  logs.value = `[2026-02-12 10:00:01] INFO: Panel service started
[2026-02-12 10:05:22] INFO: Admin logged in from 127.0.0.1
[2026-02-12 10:15:45] INFO: Site "example.com" created successfully
[2026-02-12 10:30:12] WARNING: Disk usage above 70%
[2026-02-12 10:45:33] INFO: PHP 8.2 restarted`
}

const saveConfig = async () => {
  loading.config = true
  try {
    await new Promise(resolve => setTimeout(resolve, 1000))
    Message.success('Configuration saved')
  } finally {
    loading.config = false
  }
}

const handleUpdate = async () => {
  loading.update = true
  try {
    await new Promise(resolve => setTimeout(resolve, 2000))
    Message.info('You are already using the latest version')
  } finally {
    loading.update = false
  }
}

onMounted(() => {
  fetchLogs()
})
</script>

<style scoped>
.log-viewer {
  background: #1e1e1e;
  color: #d4d4d4;
  padding: 15px;
  border-radius: 4px;
  height: 400px;
  overflow-y: auto;
  font-family: 'Courier New', Courier, monospace;
  white-space: pre-wrap;
}
</style>
