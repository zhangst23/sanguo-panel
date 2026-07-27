<template>
  <a-card title="Worker Pool (Worker 配置)" :bordered="false">
    <a-form :model="form" layout="vertical" style="max-width: 520px;">
      <a-form-item label="最大连接数 (maxConns)">
        <a-input-number v-model="form.max_conns" :min="1" :max="1000" style="width: 100%;" />
      </a-form-item>
      <a-form-item label="Worker 进程数 (PHP_LSAPI_CHILDREN)">
        <a-input-number v-model="form.max_workers" :min="1" :max="500" style="width: 100%;" />
      </a-form-item>
      <a-form-item label="实例数 (instances)">
        <a-input-number v-model="form.instances" :min="1" :max="20" style="width: 100%;" />
      </a-form-item>
      <a-form-item label="自动启动 (autoStart)">
        <a-switch v-model="form.auto_start" />
      </a-form-item>
      <a-form-item>
        <a-button type="primary" :loading="saving" @click="save">保存并重载 OLS</a-button>
      </a-form-item>
    </a-form>
  </a-card>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import request from '@/utils/request'
import { Message } from '@arco-design/web-vue'

const saving = ref(false)
const form = reactive({ max_conns: 10, max_workers: 10, instances: 1, auto_start: true })

const fetchPool = async () => {
  try {
    const res = await request.get('/php/worker-pool')
    form.max_conns = res.max_conns
    form.max_workers = res.max_workers
    form.instances = res.instances
    form.auto_start = res.auto_start
  } catch (e) {
    console.error(e)
  }
}

const save = async () => {
  saving.value = true
  try {
    await request.post('/php/worker-pool', { ...form })
    Message.success('Worker Pool 已保存')
  } catch (e) {
    console.error(e)
  } finally {
    saving.value = false
  }
}

onMounted(fetchPool)
</script>
