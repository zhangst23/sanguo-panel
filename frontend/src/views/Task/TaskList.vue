<template>
  <div class="task-container">
    <a-typography-title :heading="2">操作日志</a-typography-title>
    
    <a-card>
      <template #extra>
        <a-button type="outline" @click="fetchTasks" :loading="loading">
          <template #icon><icon-refresh /></template>
          刷新
        </a-button>
      </template>
      
      <a-table :data="tasks" :loading="loading">
        <template #columns>
          <a-table-column title="记录ID" :width="90">
            <template #cell="{ record }">
              <span class="record-id">{{ record.id }}</span>
            </template>
          </a-table-column>
          <a-table-column title="操作类型" data-index="type">
            <template #cell="{ record }">
              <a-tag color="arcoblue">{{ record.type }}</a-tag>
            </template>
          </a-table-column>
          <a-table-column title="状态" data-index="status">
            <template #cell="{ record }">
              <a-tag :color="getStatusColor(record.status)">
                {{ record.status }}
              </a-tag>
            </template>
          </a-table-column>
          <a-table-column title="进度" data-index="progress">
            <template #cell="{ record }">
              <a-progress :percent="record.progress / 100" />
            </template>
          </a-table-column>
          <a-table-column title="详情" data-index="message" ellipsis />
          <a-table-column title="开始时间" :width="150">
            <template #cell="{ record }">
              {{ formatDateTime(record.started_at) }}
            </template>
          </a-table-column>
          <a-table-column title="完成时间" :width="150">
            <template #cell="{ record }">
              {{ formatDateTime(record.completed_at) }}
            </template>
          </a-table-column>
          <a-table-column title="操作">
            <template #cell="{ record }">
              <a-space>
                <a-button type="text" size="small" v-if="record.status === 'failed'" @click="showError(record)">
                  查看错误
                </a-button>
                <a-button type="text" size="small" status="danger" @click="handleDelete(record)">
                  删除
                </a-button>
              </a-space>
            </template>
          </a-table-column>
        </template>
      </a-table>
    </a-card>

    <a-modal v-model:visible="errorVisible" title="操作错误详情" :footer="false">
      <a-alert type="error">{{ errorMessage }}</a-alert>
    </a-modal>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { Message } from '@arco-design/web-vue'
import { IconRefresh } from '@arco-design/web-vue/es/icon'
import request from '@/utils/request'

const tasks = ref([])
const loading = ref(false)
const errorVisible = ref(false)
const errorMessage = ref('')

// 时间统一显示为 YYYY-MM-DD HH:mm
const formatDateTime = (value) => {
  if (!value) return '-'
  // 后端返回的是不带时区的 UTC 时间，补上 Z 后再按浏览器本地时区显示
  const raw = String(value).replace(' ', 'T')
  const iso = /(?:Z|[+-]\d{2}:?\d{2})$/.test(raw) ? raw : `${raw}Z`
  const d = new Date(iso)
  if (isNaN(d.getTime())) return value
  const pad = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

const fetchTasks = async () => {
  loading.value = true
  try {
    const res = await request.get('/tasks/')
    tasks.value = res
  } catch (error) {
    console.error(error)
  } finally {
    loading.value = false
  }
}

const getStatusColor = (status) => {
  switch (status) {
    case 'completed': return 'green'
    case 'running': return 'blue'
    case 'failed': return 'red'
    case 'cancelled': return 'gray'
    default: return 'orange'
  }
}

const showError = (record) => {
  errorMessage.value = record.error || '未知错误'
  errorVisible.value = true
}

const handleDelete = async (record) => {
  try {
    // Assuming backend will have delete endpoint
    await request.delete(`/tasks/${record.task_uuid}`)
    Message.success('任务记录已删除')
    fetchTasks()
  } catch (error) {
    Message.error('删除失败')
  }
}

onMounted(() => {
  // 仅在打开页面时加载一次，之后由“刷新”按钮手动触发
  fetchTasks()
})
</script>

<style scoped>
.task-container {
  padding: 0;
}
.record-id {
  white-space: nowrap;
}
</style>
