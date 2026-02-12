<template>
  <div class="backup-container">
    <a-typography-title :heading="2">Backup Management</a-typography-title>
    
    <a-tabs default-active-key="1">
      <!-- Backup Records -->
      <a-tab-pane key="1" title="Backup Records">
        <a-card style="margin-top: 20px">
          <template #extra>
            <a-button type="primary" @click="showManualModal = true">
              <template #icon><icon-plus /></template>
              Create Manual Backup
            </a-button>
          </template>
          <a-table :data="backups" :columns="columns" :loading="loading">
            <template #type="{ record }">
              <a-tag :color="record.type === 'Site' ? 'blue' : 'orange'">{{ record.type }}</a-tag>
            </template>
            <template #actions="{ record }">
              <a-space>
                <a-button type="text" size="small">Download</a-button>
                <a-button type="text" size="small" status="danger">Delete</a-button>
              </a-space>
            </template>
          </a-table>
        </a-card>
      </a-tab-pane>

      <!-- Scheduled Backup -->
      <a-tab-pane key="2" title="Scheduled Backup">
        <a-card style="margin-top: 20px">
          <a-form :model="scheduleForm" layout="vertical">
            <a-form-item field="enabled" label="Enable Auto Backup">
              <a-switch v-model="scheduleForm.enabled" />
            </a-form-item>
            <a-form-item field="frequency" label="Frequency">
              <a-select v-model="scheduleForm.frequency">
                <a-option value="daily">Daily</a-option>
                <a-option value="weekly">Weekly</a-option>
                <a-option value="monthly">Monthly</a-option>
              </a-select>
            </a-form-item>
            <a-form-item field="retention" label="Retention (Count)">
              <a-input-number v-model="scheduleForm.retention" :min="1" :max="30" />
            </a-form-item>
            <a-form-item field="storage" label="Storage Location">
              <a-select v-model="scheduleForm.storage">
                <a-option value="local">Local Disk</a-option>
                <a-option value="s3">Amazon S3</a-option>
                <a-option value="oss">Aliyun OSS</a-option>
              </a-select>
            </a-form-item>
            <a-button type="primary" @click="saveSchedule">Save Schedule</a-button>
          </a-form>
        </a-card>
      </a-tab-pane>
    </a-tabs>

    <!-- Manual Backup Modal -->
    <a-modal v-model:visible="showManualModal" title="Create Manual Backup" @ok="handleManualBackup">
      <a-form :model="manualForm" layout="vertical">
        <a-form-item field="target" label="Backup Target" required>
          <a-radio-group v-model="manualForm.target">
            <a-radio value="site">Specific Site</a-radio>
            <a-radio value="database">Specific Database</a-radio>
            <a-radio value="full">Full System</a-radio>
          </a-radio-group>
        </a-form-item>
        <a-form-item field="id" label="Select Item" v-if="manualForm.target !== 'full'">
          <a-select v-model="manualForm.id">
            <a-option v-for="item in items" :key="item.id" :value="item.id">{{ item.name }}</a-option>
          </a-select>
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { Message } from '@arco-design/web-vue'

const loading = ref(false)
const showManualModal = ref(false)
const backups = ref([
  { id: 1, name: 'backup_site1_20260212.tar.gz', type: 'Site', size: '124MB', date: '2026-02-12 02:00:00' },
  { id: 2, name: 'backup_db1_20260212.sql.gz', type: 'Database', size: '12MB', date: '2026-02-12 02:05:00' }
])

const columns = [
  { title: 'File Name', dataIndex: 'name' },
  { title: 'Type', slotName: 'type' },
  { title: 'Size', dataIndex: 'size' },
  { title: 'Date', dataIndex: 'date' },
  { title: 'Actions', slotName: 'actions' },
]

const scheduleForm = reactive({
  enabled: true,
  frequency: 'daily',
  retention: 7,
  storage: 'local'
})

const manualForm = reactive({
  target: 'site',
  id: null
})

const items = ref([
  { id: 1, name: 'example.com' },
  { id: 2, name: 'mysite.org' }
])

const saveSchedule = () => {
  Message.success('Backup schedule saved')
}

const handleManualBackup = async () => {
  Message.info('Backup process started in background...')
  showManualModal.value = false
  // Mock backup
  setTimeout(() => {
    Message.success('Manual backup completed')
  }, 2000)
}
</script>
