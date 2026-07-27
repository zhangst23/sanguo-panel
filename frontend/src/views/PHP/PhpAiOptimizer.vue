<template>
  <a-card title="AI Optimizer (AI 优化建议)" :bordered="false">
    <a-space direction="vertical" fill>
      <a-button size="small" @click="fetchTips"><icon-bulb /> 重新分析</a-button>
      <a-spin :loading="loading">
        <a-empty v-if="!tips.length" description="暂无建议" />
        <a-list :data="tips" :loading="loading">
          <template #item="{ item }">
            <a-list-item>
              <a-alert :type="levelType(item.level)" :title="item.title" :show-icon="true">
                <template #default>
                  <div>{{ item.detail }}</div>
                  <a-tag v-if="item.suggest" color="arcoblue" style="margin-top: 6px;">建议: {{ item.suggest }}</a-tag>
                </template>
              </a-alert>
            </a-list-item>
          </template>
        </a-list>
      </a-spin>
    </a-space>
  </a-card>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import request from '@/utils/request'

const loading = ref(false)
const tips = ref([])

const levelType = (level) => {
  const map = { high: 'error', medium: 'warning', good: 'success', info: 'info' }
  return map[level] || 'info'
}

const fetchTips = async () => {
  loading.value = true
  try {
    const res = await request.get('/php/ai-optimizer')
    tips.value = res.tips || []
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
}

onMounted(fetchTips)
</script>
