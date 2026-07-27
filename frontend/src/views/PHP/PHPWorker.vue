<template>
  <div class="php-worker-container">
    <a-row :gutter="20">
      <a-col :span="10">
        <a-card title="运行状态">
          <template #extra>
            <a-tag :color="worker.running ? 'green' : 'red'">
              {{ worker.running ? '运行中' : '已停止' }}
            </a-tag>
          </template>
          <a-descriptions :column="1" bordered size="medium">
            <a-descriptions-item label="PHP 版本">{{ worker.version || '-' }}</a-descriptions-item>
            <a-descriptions-item label="Worker 进程数">{{ worker.count }}</a-descriptions-item>
            <a-descriptions-item label="内存占用">{{ worker.memory_mb }} MB</a-descriptions-item>
          </a-descriptions>
          <a-divider />
          <a-button type="primary" :loading="loading" @click="handleRestart">
            <template #icon><icon-refresh /></template>
            重启 PHP Worker
          </a-button>
        </a-card>
      </a-col>
      <a-col :span="14">
        <a-card title="已安装 PHP / LSAPI 版本">
          <a-table :data="versions" :loading="loading" :pagination="false">
            <template #columns>
              <a-table-column title="版本" data-index="version" />
              <a-table-column title="LSAPI 名称" data-index="lsapi_name" />
              <a-table-column title="状态">
                <template #cell="{ record }">
                  <a-tag :color="record.installed ? 'green' : 'gray'">
                    {{ record.installed ? '已安装' : '未安装' }}
                  </a-tag>
                </template>
              </a-table-column>
            </template>
          </a-table>
        </a-card>
      </a-col>
    </a-row>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import request from '@/utils/request'
import { Message } from '@arco-design/web-vue'

const loading = ref(false)
const versions = ref([])
const worker = ref({
  running: false,
  version: '',
  count: 0,
  memory_mb: 0
})

const fetchWorker = async () => {
  try {
    const res = await request.get('/php/worker')
    worker.value = res
  } catch (error) {
    console.error(error)
  }
}

const fetchVersions = async () => {
  try {
    const res = await request.get('/php/versions')
    versions.value = res
  } catch (error) {
    console.error(error)
  }
}

const handleRestart = async () => {
  loading.value = true
  try {
    await request.post('/litespeed/action/restart')
    Message.success('PHP Worker 已重启')
    await fetchWorker()
  } catch (error) {
    console.error(error)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchWorker()
  fetchVersions()
})
</script>

<style scoped>
.php-worker-container {
  padding: 0;
}
</style>
