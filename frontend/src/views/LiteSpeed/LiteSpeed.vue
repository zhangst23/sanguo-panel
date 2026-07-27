<template>
  <div class="litespeed-container">
    <a-tabs default-active-key="2">
      <a-tab-pane key="2" >
        <a-table :data="vhosts">
          <template #columns>
            <a-table-column title="主机名" data-index="name"></a-table-column>
            <a-table-column title="绑定域名" data-index="domain"></a-table-column>
            <a-table-column title="根目录" data-index="root"></a-table-column>
            <a-table-column title="操作">
              <template #cell="{ record }">
                <a-button type="text" size="small">配置预览</a-button>
                <a-button type="text" size="small">编辑</a-button>
              </template>
            </a-table-column>
          </template>
        </a-table>
      </a-tab-pane>
    </a-tabs>
  </div>
</template>

<script setup>
import { ref, onMounted, reactive } from 'vue'
import request from '@/utils/request'

const loading = ref(false)
const vhosts = ref([])

const fetchVHosts = async () => {
  try {
    const res = await request.get('/litespeed/vhosts')
    vhosts.value = res
  } catch (error) {
    console.error(error)
  }
}

onMounted(() => {
  fetchVHosts()
})
</script>

<style scoped>
.litespeed-container {
  padding: 20px;
}
.header-section {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}
</style>
