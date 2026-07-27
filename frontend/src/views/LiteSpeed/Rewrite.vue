<template>
  <div class="rewrite-container">
    <a-card title="重写规则 (Rewrite Rules)">
      <a-space direction="vertical" fill :size="16">
        <a-select v-model="selectedVhost" placeholder="选择虚拟主机" style="width: 320px;" @change="loadRules">
          <a-option v-for="v in vhosts" :key="v.name" :value="v.name">{{ v.name }}</a-option>
        </a-select>
        <a-textarea
          v-model="rules"
          placeholder="例如：&#10;RewriteRule ^/old/(.*)$ /new/$1 [R=301,L]"
          :auto-size="{ minRows: 16, maxRows: 30 }"
        />
        <a-space>
          <a-button type="primary" :loading="loading" :disabled="!selectedVhost" @click="saveRules">保存并重载</a-button>
          <a-button :loading="loading" :disabled="!selectedVhost" @click="loadRules">重新加载</a-button>
        </a-space>
      </a-space>
    </a-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import request from '@/utils/request'
import { Message } from '@arco-design/web-vue'

const loading = ref(false)
const vhosts = ref([])
const selectedVhost = ref('')
const rules = ref('')

const fetchVHosts = async () => {
  try {
    const res = await request.get('/litespeed/vhosts')
    vhosts.value = res
    if (res.length) {
      selectedVhost.value = res[0].name
      await loadRules()
    }
  } catch (error) {
    console.error(error)
  }
}

const loadRules = async () => {
  if (!selectedVhost.value) return
  loading.value = true
  try {
    const res = await request.get(`/litespeed/vhosts/${selectedVhost.value}/rewrite`)
    rules.value = res.rules || ''
  } catch (error) {
    console.error(error)
  } finally {
    loading.value = false
  }
}

const saveRules = async () => {
  if (!selectedVhost.value) return
  loading.value = true
  try {
    await request.post(`/litespeed/vhosts/${selectedVhost.value}/rewrite`, { rules: rules.value })
    Message.success('重写规则已保存')
  } catch (error) {
    console.error(error)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchVHosts()
})
</script>

<style scoped>
.rewrite-container {
  padding: 0;
}
</style>
