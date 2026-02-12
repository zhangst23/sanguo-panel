<template>
  <div class="mariadb-container">
    <a-typography-title :heading="2">MariaDB Management</a-typography-title>

    <a-row :gutter="20">
      <!-- Service Status Card -->
      <a-col :span="24" style="margin-bottom: 20px">
        <a-card title="Service Status" hoverable>
          <template #extra>
            <a-tag :color="serviceStatus === 'running' ? 'green' : 'red'">{{ serviceStatus.toUpperCase() }}</a-tag>
          </template>
          <a-space size="large">
            <a-statistic title="Port" :value="3306" />
            <a-statistic title="Connections" :value="12" />
            <a-space style="margin-left: 40px">
              <a-button type="primary" @click="handleServiceAction('restart')" :loading="serviceLoading">
                <template #icon><icon-refresh /></template>
                Restart Service
              </a-button>
            </a-space>
          </a-space>
        </a-card>
      </a-col>

      <!-- Shared Databases Management -->
      <a-col :span="24">
        <a-card title="Shared Database Instances">
          <template #extra>
            <a-button type="primary" @click="showCreateModal = true">
              <template #icon><icon-plus /></template>
              Add Instance
            </a-button>
          </template>
          <a-table :data="databases" :columns="columns" :loading="loading">
            <template #status="{ record }">
              <a-tag :color="record.status === 'active' ? 'green' : 'red'">{{ record.status }}</a-tag>
            </template>
            <template #actions="{ record }">
              <a-space>
                <a-button type="text" size="small">Edit</a-button>
                <a-button type="text" size="small" status="danger">Delete</a-button>
              </a-space>
            </template>
          </a-table>
        </a-card>
      </a-col>
    </a-row>

    <!-- Add Instance Modal -->
    <a-modal v-model:visible="showCreateModal" title="Add Shared Database Instance" @ok="handleCreate" @cancel="resetForm">
      <a-form :model="form">
        <a-form-item field="name" label="Instance Name" required>
          <a-input v-model="form.name" placeholder="e.g. Local MariaDB" />
        </a-form-item>
        <a-form-item field="db_host" label="Host" required>
          <a-input v-model="form.db_host" placeholder="localhost" />
        </a-form-item>
        <a-form-item field="db_port" label="Port" required>
          <a-input-number v-model="form.db_port" :default-value="3306" />
        </a-form-item>
        <a-form-item field="db_name" label="Database Name" required>
          <a-input v-model="form.db_name" placeholder="sanguo_shared" />
        </a-form-item>
        <a-form-item field="db_user" label="Username" required>
          <a-input v-model="form.db_user" />
        </a-form-item>
        <a-form-item field="db_password" label="Password" required>
          <a-input-password v-model="form.db_password" />
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import request from '@/utils/request'
import { Message } from '@arco-design/web-vue'

const serviceStatus = ref('unknown')
const serviceLoading = ref(false)
const loading = ref(false)
const databases = ref([])
const showCreateModal = ref(false)

const form = reactive({
  name: '',
  db_host: 'localhost',
  db_port: 3306,
  db_name: '',
  db_user: '',
  db_password: '',
  charset: 'utf8mb4',
  collation: 'utf8mb4_unicode_ci'
})

const columns = [
  { title: 'Name', dataIndex: 'name' },
  { title: 'Host', dataIndex: 'db_host' },
  { title: 'Database', dataIndex: 'db_name' },
  { title: 'User', dataIndex: 'db_user' },
  { title: 'Status', slotName: 'status' },
  { title: 'Actions', slotName: 'actions' },
]

const fetchServiceStatus = async () => {
  try {
    const res = await request.get('/services/mariadb/status')
    serviceStatus.value = res.status
  } catch (error) {
    console.error(error)
  }
}

const fetchDatabases = async () => {
  loading.value = true
  try {
    databases.value = await request.get('/sites/databases/shared')
  } catch (error) {
    console.error(error)
  } finally {
    loading.value = false
  }
}

const handleServiceAction = async (action) => {
  serviceLoading.value = true
  try {
    await request.post(`/services/mariadb/${action}`)
    Message.success(`MariaDB ${action}ed successfully`)
    await fetchServiceStatus()
  } catch (error) {
    console.error(error)
  } finally {
    serviceLoading.value = false
  }
}

const handleCreate = async () => {
  try {
    await request.post('/sites/databases/shared', form)
    Message.success('Database instance added successfully')
    showCreateModal.value = false
    resetForm()
    fetchDatabases()
  } catch (error) {
    console.error(error)
  }
}

const resetForm = () => {
  Object.assign(form, {
    name: '',
    db_host: 'localhost',
    db_port: 3306,
    db_name: '',
    db_user: '',
    db_password: '',
    charset: 'utf8mb4',
    collation: 'utf8mb4_unicode_ci'
  })
}

onMounted(() => {
  fetchServiceStatus()
  fetchDatabases()
})
</script>

<style scoped>
.mariadb-container {
  padding: 0;
}
</style>
