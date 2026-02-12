<template>
  <div class="database-adv-container">
    <a-typography-title :heading="2">Database Advanced Management</a-typography-title>
    
    <a-tabs default-active-key="1">
      <!-- Slow Queries -->
      <a-tab-pane key="1" title="Slow Queries">
        <a-card>
          <template #extra>
            <a-button type="primary" size="small" @click="fetchSlowQueries">Refresh</a-button>
          </template>
          <a-table :data="slowQueries" :columns="slowQueryColumns" :loading="loading">
            <template #query="{ record }">
              <div class="query-code"><code>{{ record.query }}</code></div>
            </template>
          </a-table>
        </a-card>
      </a-tab-pane>

      <!-- Optimization -->
      <a-tab-pane key="2" title="Optimization & Tables">
        <a-row :gutter="20">
          <a-col :span="24" style="margin-bottom: 20px">
            <a-card>
              <a-space>
                <span>Select Database Instance:</span>
                <a-select v-model="selectedDb" @change="fetchTableStatus" style="width: 300px">
                  <a-option v-for="db in databases" :key="db.id" :value="db.db_name">{{ db.db_name }}</a-option>
                </a-select>
                <a-button type="primary" status="success" :disabled="!selectedDb" @click="handleOptimize" :loading="optimizing">
                  One-Click Optimize
                </a-button>
              </a-space>
            </a-card>
          </a-col>

          <a-col :span="24" v-if="selectedDb">
            <a-card title="Table Status">
              <a-table :data="tables" :columns="tableColumns" :loading="loading">
                <template #overhead="{ record }">
                  <a-tag v-if="record.overhead !== '0KB'" color="red">{{ record.overhead }}</a-tag>
                  <span v-else>Clean</span>
                </template>
              </a-table>
            </a-card>
          </a-col>
        </a-row>
      </a-tab-pane>
    </a-tabs>

    <!-- Optimization Results Modal -->
    <a-modal v-model:visible="showResultModal" title="Optimization Results" :footer="false">
      <div v-if="optimizationResult">
        <a-alert type="success" style="margin-bottom: 20px">
          {{ optimizationResult.message }} (Space Reclaimed: {{ optimizationResult.space_reclaimed }})
        </a-alert>
        <a-list size="small">
          <a-list-item v-for="(action, index) in optimizationResult.actions" :key="index">
            <template #extra>
              <icon-check-circle-fill style="color: #00b42a" />
            </template>
            {{ action }}
          </a-list-item>
        </a-list>
      </div>
    </a-modal>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import request from '@/utils/request'
import { Message } from '@arco-design/web-vue'
import { IconCheckCircleFill } from '@arco-design/web-vue/es/icon'

const loading = ref(false)
const slowQueries = ref([])
const databases = ref([])
const selectedDb = ref(null)
const tables = ref([])
const optimizing = ref(false)
const showResultModal = ref(false)
const optimizationResult = ref(null)

const slowQueryColumns = [
  { title: 'Time', dataIndex: 'timestamp', width: 180 },
  { title: 'Execution', dataIndex: 'execution_time', width: 100 },
  { title: 'SQL Query', slotName: 'query' },
]

const tableColumns = [
  { title: 'Table Name', dataIndex: 'name' },
  { title: 'Engine', dataIndex: 'engine' },
  { title: 'Rows', dataIndex: 'rows' },
  { title: 'Data Size', dataIndex: 'data_length' },
  { title: 'Index Size', dataIndex: 'index_length' },
  { title: 'Overhead', slotName: 'overhead' },
]

const fetchSlowQueries = async () => {
  loading.value = true
  try {
    slowQueries.value = await request.get('/database/slow-queries')
  } catch (error) {
    console.error(error)
  } finally {
    loading.value = false
  }
}

const fetchDatabases = async () => {
  try {
    const res = await request.get('/sites/') // Reuse sites list to get shared databases
    databases.value = res.filter(s => s.db_name)
    if (databases.value.length > 0) {
      selectedDb.value = databases.value[0].db_name
      fetchTableStatus()
    }
  } catch (error) {
    console.error(error)
  }
}

const fetchTableStatus = async () => {
  if (!selectedDb.value) return
  loading.value = true
  try {
    tables.value = await request.get(`/database/tables/${selectedDb.value}`)
  } catch (error) {
    console.error(error)
  } finally {
    loading.value = false
  }
}

const handleOptimize = async () => {
  optimizing.value = true
  try {
    const res = await request.post(`/database/optimize?db_name=${selectedDb.value}`)
    optimizationResult.value = res
    showResultModal.value = true
    fetchTableStatus()
  } catch (error) {
    console.error(error)
  } finally {
    optimizing.value = false
  }
}

onMounted(() => {
  fetchSlowQueries()
  fetchDatabases()
})
</script>

<style scoped>
.query-code {
  background: #f2f3f5;
  padding: 8px;
  border-radius: 4px;
  max-height: 100px;
  overflow-y: auto;
}
.query-code code {
  font-family: monospace;
  font-size: 12px;
  word-break: break-all;
  white-space: pre-wrap;
}
</style>
