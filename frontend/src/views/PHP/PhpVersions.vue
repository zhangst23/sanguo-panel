<template>
  <a-card title="PHP 版本 (Versions)" :bordered="false">
    <a-table :data="versions" :loading="loading" :pagination="false" size="medium">
      <template #columns>
        <a-table-column title="版本" data-index="version" />
        <a-table-column title="状态">
          <template #cell="{ record }">
            <a-tag :color="record.status === 'installed' ? 'green' : 'gray'">
              {{ record.status === 'installed' ? '已安装' : '未安装' }}
            </a-tag>
          </template>
        </a-table-column>
        <a-table-column title="默认版本">
          <template #cell="{ record }">
            <a-tag v-if="record.is_default" color="arcoblue">默认</a-tag>
            <span v-else>-</span>
          </template>
        </a-table-column>
        <a-table-column title="操作">
          <template #cell="{ record }">
            <a-button
              type="text"
              size="small"
              :disabled="record.is_default || record.status !== 'installed'"
              @click="setDefault(record)"
            >设为默认</a-button>
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

const fetchVersions = async () => {
  loading.value = true
  try {
    versions.value = await request.get('/php/versions')
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
}

const setDefault = async (record) => {
  try {
    await request.post(`/php/versions/${record.version}/default`)
    Message.success(`已将 PHP ${record.version} 设为默认`)
    await fetchVersions()
  } catch (e) {
    console.error(e)
  }
}

onMounted(fetchVersions)
</script>
