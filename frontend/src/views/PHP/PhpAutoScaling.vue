<template>
  <a-card title="Auto Scaling (自动伸缩)" :bordered="false">
    <a-form :model="form" layout="vertical" style="max-width: 520px;">
      <a-form-item label="启用自动伸缩">
        <a-switch v-model="form.enabled" />
      </a-form-item>
      <a-form-item label="最小 Worker 数 (min_workers)">
        <a-input-number v-model="form.min_workers" :min="1" :max="100" style="width: 100%;" />
      </a-form-item>
      <a-form-item label="最大 Worker 数 (max_workers)">
        <a-input-number v-model="form.max_workers" :min="1" :max="500" style="width: 100%;" />
      </a-form-item>
      <a-form-item label="CPU 阈值 % (触发扩容)">
        <a-input-number v-model="form.cpu_threshold" :min="10" :max="99" style="width: 100%;" />
      </a-form-item>
      <a-form-item>
        <a-button type="primary" :loading="saving" @click="save">保存策略</a-button>
      </a-form-item>
    </a-form>
    <a-alert type="info">
      自动伸缩策略将持久化保存；实际扩容由面板调度器依据 CPU 阈值在 min/max 范围内动态调整 PHP Worker 数量。
    </a-alert>
  </a-card>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import request from '@/utils/request'
import { Message } from '@arco-design/web-vue'

const saving = ref(false)
const form = reactive({ enabled: false, min_workers: 2, max_workers: 20, cpu_threshold: 70 })

const fetchConf = async () => {
  try {
    const res = await request.get('/php/autoscaling')
    form.enabled = res.enabled
    form.min_workers = res.min_workers
    form.max_workers = res.max_workers
    form.cpu_threshold = res.cpu_threshold
  } catch (e) {
    console.error(e)
  }
}

const save = async () => {
  saving.value = true
  try {
    await request.post('/php/autoscaling', { ...form })
    Message.success('自动伸缩策略已保存')
  } catch (e) {
    console.error(e)
  } finally {
    saving.value = false
  }
}

onMounted(fetchConf)
</script>
