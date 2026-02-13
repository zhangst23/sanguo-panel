<template>
  <div class="task-container">
    <a-typography-title :heading="2">任务列表</a-typography-title>
    
    <a-card>
      <template #extra>
        <a-button type="outline" @click="fetchTasks">
          <template #icon><icon-refresh /></template>
          刷新
        </a-button>
      </template>
      
      <a-table :data="tasks" :loading="loading">
        <template #columns>
          <a-table-column title="任务ID" data-index="task_uuid" :width="120" />
          <a-table-column title="类型" data-index="type">
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
          <a-table-column title="消息" data-index="message" />
          <a-table-column title="开始时间" data-index="started_at" />
          <a-table-column title="完成时间" data-index="completed_at" />
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

    <a-modal v-model:visible="errorVisible" title="任务错误详情" :footer="false">
      <a-alert type="error">{{ errorMessage }}</a-alert>
    </a-modal>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { Message } from '@arco-design/web-vue'
import { IconRefresh } from '@arco-design/web-vue/es/icon'
import request from '@/utils/request'

const tasks = ref([])
const loading = ref(false)
const errorVisible = ref(false)
const errorMessage = ref('')
let pollTimer = null

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
  fetchTasks()
  pollTimer = setInterval(fetchTasks, 5000)
})

onUnmounted(() => {
  if (pollTimer) clearInterval(pollTimer)
})
</script>

<style scoped>
.task-container {
  padding: 0 0 20px 0;
}
</style>
