<template>
  <div class="litespeed-container">
    <a-card title="虚拟主机列表">
      <template #extra>
        <a-button size="small" @click="fetchVHosts">
          <template #icon><icon-refresh /></template>
          刷新
        </a-button>
      </template>

      <a-table :data="vhosts" :loading="loading">
        <template #columns>
          <a-table-column title="主机名" data-index="name" />
          <a-table-column title="绑定域名" data-index="domain" />
          <a-table-column title="根目录" data-index="root" />
          <a-table-column title="操作">
            <template #cell="{ record }">
              <a-space>
                <a-button type="text" size="small" @click="openConfig(record, false)">配置预览</a-button>
                <a-button type="text" size="small" @click="openConfig(record, true)">编辑</a-button>
              </a-space>
            </template>
          </a-table-column>
        </template>
      </a-table>
    </a-card>

    <a-modal
      v-model:visible="configModalVisible"
      :title="modalTitle"
      :width="760"
      :ok-text="configEditable ? '保存并重载' : '关闭'"
      :ok-loading="saving"
      @ok="handleConfigOk"
    >
      <a-alert v-if="configEditable" type="warning" show-icon style="margin-bottom: 12px">
        保存前会自动备份原配置，保存后重载 OpenLiteSpeed。请确保配置语法正确。
      </a-alert>
      <a-spin :loading="configLoading" style="width: 100%">
        <a-textarea
          v-model="configContent"
          :auto-size="{ minRows: 18, maxRows: 30 }"
          :readonly="!configEditable"
          class="config-editor"
          placeholder="正在读取配置…"
        />
      </a-spin>
    </a-modal>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import request from '@/utils/request'
import { Message } from '@arco-design/web-vue'
import { IconRefresh } from '@arco-design/web-vue/es/icon'

const loading = ref(false)
const vhosts = ref([])

const configModalVisible = ref(false)
const configEditable = ref(false)
const configLoading = ref(false)
const configContent = ref('')
const currentVhost = ref(null)
const saving = ref(false)

const modalTitle = computed(
  () => `${configEditable.value ? '编辑' : '预览'}配置 — ${currentVhost.value?.name || ''}`
)

const fetchVHosts = async () => {
  loading.value = true
  try {
    vhosts.value = await request.get('/litespeed/vhosts')
  } catch (error) {
    console.error(error)
  } finally {
    loading.value = false
  }
}

const openConfig = async (record, editable) => {
  currentVhost.value = record
  configEditable.value = editable
  configContent.value = ''
  configModalVisible.value = true
  configLoading.value = true
  try {
    const res = await request.get(
      `/litespeed/vhosts/${encodeURIComponent(record.name)}/config`
    )
    configContent.value = res.content || ''
  } catch (error) {
    console.error(error)
    Message.error('读取配置失败')
  } finally {
    configLoading.value = false
  }
}

const handleConfigOk = async () => {
  if (!configEditable.value) {
    configModalVisible.value = false
    return
  }
  saving.value = true
  try {
    await request.put(
      `/litespeed/vhosts/${encodeURIComponent(currentVhost.value.name)}/config`,
      { content: configContent.value }
    )
    Message.success('配置已保存并重载 OLS')
    configModalVisible.value = false
  } catch (error) {
    console.error(error)
  } finally {
    saving.value = false
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
.config-editor {
  font-family: monospace;
  font-size: 13px;
}
</style>
