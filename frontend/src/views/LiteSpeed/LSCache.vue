<template>
  <div class="lscache-container">
    <a-card title="LSCache 缓存设置">
      <a-space direction="vertical" fill :size="20">
        <div class="config-item">
          <div>
            <div class="config-title">LSCache 全局开关</div>
            <div class="config-desc">开启后 OpenLiteSpeed 将为动态内容提供缓存加速，显著提升访问速度。</div>
          </div>
          <a-switch v-model="lscache" :loading="loading" @change="toggle" />
        </div>
        <a-alert type="info">
          提示：LSCache 为各虚拟主机提供细粒度缓存策略，可在 OLS 管理后台（:7080）的「缓存」中为具体站点配置例外规则与 TTL。
        </a-alert>
      </a-space>
    </a-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import request from '@/utils/request'
import { Message } from '@arco-design/web-vue'

const loading = ref(false)
const lscache = ref(true)

const fetchFeatures = async () => {
  try {
    const res = await request.get('/litespeed/config/features')
    lscache.value = !!res.lscache
  } catch (error) {
    console.error(error)
  }
}

const toggle = async (enabled) => {
  loading.value = true
  try {
    await request.post('/litespeed/config/features/toggle', { feature: 'lscache', enabled })
    Message.success(`LSCache 已${enabled ? '开启' : '关闭'}`)
  } catch (error) {
    lscache.value = !enabled
    console.error(error)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchFeatures()
})
</script>

<style scoped>
.lscache-container {
  padding: 0;
}
.config-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 0;
  border-bottom: 1px solid var(--color-fill-2);
}
.config-title {
  font-weight: 600;
  margin-bottom: 4px;
}
.config-desc {
  color: var(--color-text-3);
  font-size: 12px;
}
</style>
