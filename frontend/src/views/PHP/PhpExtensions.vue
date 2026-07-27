<template>
  <a-card title="扩展管理 (Extensions)" :bordered="false">
    <a-space style="margin-bottom: 16px;">
      <a-select v-model="version" style="width: 200px;" @change="fetchExt">
        <a-option v-for="v in versions" :key="v.version" :value="v.version">{{ v.version }}</a-option>
      </a-select>
      <a-button @click="fetchExt"><icon-refresh /> 刷新</a-button>
    </a-space>
    <a-table :data="exts" :loading="loading" :pagination="false" size="medium">
      <template #columns>
        <a-table-column title="扩展" data-index="name" />
        <a-table-column title="状态">
          <template #cell="{ record }">
            <a-tag :color="record.status === 'enabled' ? 'green' : 'gray'">
              {{ record.status === 'enabled' ? '已启用' : '已禁用' }}
            </a-tag>
          </template>
        </a-table-column>
        <a-table-column title="操作">
          <template #cell="{ record }">
            <a-button type="text" size="small" @click="toggle(record)">
              {{ record.status === 'enabled' ? '禁用' : '启用' }}
            </a-button>
          </template>
        </a-table-column>
      </template>
    </a-table>
  </a-card>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import request from '@/utils/request'
import { Message } from '@arco-design/web-vue'

const loading = ref(false)
const versions = ref([])
const version = ref('')
const exts = ref([])

const fetchVersions = async () => {
  try {
    const res = await request.get('/php/versions')
    versions.value = res
    const def = res.find((v) => v.is_default) || res.find((v) => v.status === 'installed')
    if (def) {
      version.value = def.version
      await fetchExt()
    }
  } catch (e) {
    console.error(e)
  }
}

const fetchExt = async () => {
  if (!version.value) return
  loading.value = true
  try {
    exts.value = await request.get(`/php/${version.value}/extensions`)
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
}

const toggle = async (record) => {
  try {
    const res = await request.post(`/php/${version.value}/extensions/${record.name}`)
    record.status = res.enabled ? 'enabled' : 'disabled'
    Message.success(res.msg || '操作成功')
  } catch (e) {
    console.error(e)
  }
}

onMounted(fetchVersions)
</script>
