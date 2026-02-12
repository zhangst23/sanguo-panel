<template>
  <div class="website-list">
    <a-typography-title :heading="2">Websites</a-typography-title>
    <a-card>
      <template #extra>
        <a-button type="primary" @click="showCreateModal = true">
          <template #icon><icon-plus /></template>
          Create Site
        </a-button>
      </template>
      <a-table :data="sites" :columns="columns" :loading="loading">
        <template #status="{ record }">
          <a-tag :color="record.status === 'active' ? 'green' : 'red'">
            {{ record.status }}
          </a-tag>
        </template>
        <template #actions="{ record }">
          <a-space>
            <a-button type="text" size="small">Manage</a-button>
            <a-popconfirm content="Are you sure to delete this site?" @ok="handleDelete(record.id)">
              <a-button type="text" size="small" status="danger">Delete</a-button>
            </a-popconfirm>
          </a-space>
        </template>
      </a-table>
    </a-card>

    <!-- Create Site Modal -->
    <a-modal v-model:visible="showCreateModal" title="Create New Site" @ok="handleCreate" @cancel="resetForm">
      <a-form :model="form" ref="formRef">
        <a-form-item field="domain" label="Domain" required>
          <a-input v-model="form.domain" placeholder="e.g. example.com" />
        </a-form-item>
        <a-form-item field="root_path" label="Root Path" required>
          <a-input v-model="form.root_path" placeholder="e.g. /www/wwwroot/example.com" />
        </a-form-item>
        <a-form-item field="php_version" label="PHP Version">
          <a-select v-model="form.php_version">
            <a-option>8.2</a-option>
            <a-option>8.1</a-option>
            <a-option>7.4</a-option>
          </a-select>
        </a-form-item>
        <a-form-item field="table_prefix" label="DB Table Prefix" required>
          <a-input v-model="form.table_prefix" placeholder="e.g. wp_" />
        </a-form-item>
        <a-form-item field="shared_db_id" label="Shared Database" required>
          <a-select v-model="form.shared_db_id" placeholder="Select shared database">
            <a-option v-for="db in sharedDbs" :key="db.id" :value="db.id">{{ db.name }}</a-option>
          </a-select>
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import request from '@/utils/request'
import { Message } from '@arco-design/web-vue'

const loading = ref(false)
const sites = ref([])
const sharedDbs = ref([])
const showCreateModal = ref(false)
const formRef = ref(null)

const form = reactive({
  domain: '',
  root_path: '',
  php_version: '8.2',
  table_prefix: 'wp_',
  shared_db_id: null,
  notes: ''
})

const columns = [
  { title: 'Domain', dataIndex: 'domain' },
  { title: 'PHP Version', dataIndex: 'php_version' },
  { title: 'Status', slotName: 'status' },
  { title: 'Created At', dataIndex: 'created_at' },
  { title: 'Actions', slotName: 'actions' },
]

const fetchSites = async () => {
  loading.value = true
  try {
    sites.value = await request.get('/sites/')
  } catch (error) {
    console.error(error)
  } finally {
    loading.value = false
  }
}

const fetchSharedDbs = async () => {
  try {
    sharedDbs.value = await request.get('/sites/databases/shared')
    if (sharedDbs.value.length > 0) {
      form.shared_db_id = sharedDbs.value[0].id
    }
  } catch (error) {
    console.error(error)
  }
}

const handleCreate = async () => {
  try {
    await request.post('/sites/', form)
    Message.success('Site created successfully')
    showCreateModal.value = false
    resetForm()
    fetchSites()
  } catch (error) {
    console.error(error)
  }
}

const handleDelete = async (id) => {
  try {
    await request.delete(`/sites/${id}`)
    Message.success('Site deleted successfully')
    fetchSites()
  } catch (error) {
    console.error(error)
  }
}

const resetForm = () => {
  Object.assign(form, {
    domain: '',
    root_path: '',
    php_version: '8.2',
    table_prefix: 'wp_',
    shared_db_id: sharedDbs.value[0]?.id || null,
    notes: ''
  })
}

onMounted(() => {
  fetchSites()
  fetchSharedDbs()
})
</script>
