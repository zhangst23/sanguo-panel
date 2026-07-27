<template>
  <a-card title="OPcache (字节码缓存)" :bordered="false">
    <a-spin :loading="loading" style="width: 100%;">
      <a-result v-if="!loading && !data.enabled" status="warning" title="OPcache 未启用">
        <template #subtitle>建议在 Runtime Config 或 php.ini 中开启 opcache.enable=1</template>
      </a-result>
      <template v-else>
        <a-descriptions :column="2" bordered size="medium">
          <a-descriptions-item label="启用状态">
            <a-tag :color="data.enabled ? 'green' : 'red'">{{ data.enabled ? '已启用' : '未启用' }}</a-tag>
          </a-descriptions-item>
          <a-descriptions-item label="内存限制">{{ data.memory_consumption }} MB</a-descriptions-item>
          <a-descriptions-item label="已用内存">{{ data.used_memory }} MB</a-descriptions-item>
          <a-descriptions-item label="空闲内存">{{ data.free_memory }} MB</a-descriptions-item>
          <a-descriptions-item label="缓存脚本数">{{ data.num_cached_scripts }}</a-descriptions-item>
          <a-descriptions-item label="revalidate 频率">{{ data.revalidate_freq }} 秒</a-descriptions-item>
          <a-descriptions-item label="命中率">
            <a-tag v-if="data.hit_rate !== null" :color="data.hit_rate >= 95 ? 'green' : 'orange'">
              {{ data.hit_rate }}%
            </a-tag>
            <span v-else>无</span>
          </a-descriptions-item>
        </a-descriptions>
      </template>
    </a-spin>
  </a-card>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import request from '@/utils/request'
import { get_default_version } from './phpVersion'

const loading = ref(false)
const data = ref({
  enabled: false, memory_consumption: 0, revalidate_freq: 0,
  hit_rate: null, used_memory: 0, free_memory: 0, num_cached_scripts: 0,
})

const fetchOpcache = async () => {
  loading.value = true
  try {
    const v = await get_default_version()
    data.value = await request.get(`/php/${v}/opcache`)
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
}

onMounted(fetchOpcache)
</script>
