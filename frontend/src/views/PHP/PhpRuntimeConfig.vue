<template>
  <a-card title="Runtime Config (php.ini)" :bordered="false">
    <a-space style="margin-bottom: 16px;">
      <a-select v-model="version" style="width: 200px;" @change="onVersionChange">
        <a-option v-for="v in versions" :key="v.version" :value="v.version">{{ v.version }}</a-option>
      </a-select>
      <a-button @click="showRaw"><icon-edit /> 编辑原始 php.ini</a-button>
    </a-space>
    <a-form :model="iniForm" layout="vertical">
      <a-form-item label="内存限制 (memory_limit)">
        <a-input v-model="iniForm.memory_limit" />
      </a-form-item>
      <a-form-item label="POST 最大尺寸 (post_max_size)">
        <a-input v-model="iniForm.post_max_size" />
      </a-form-item>
      <a-form-item label="上传文件限制 (upload_max_filesize)">
        <a-input v-model="iniForm.upload_max_filesize" />
      </a-form-item>
      <a-form-item label="最大执行时间 (max_execution_time)">
        <a-input-number v-model="iniForm.max_execution_time" :min="0" style="width: 200px;" />
      </a-form-item>
      <a-form-item label="禁用函数 (disable_functions)">
        <a-input v-model="iniForm.disable_functions" placeholder="exec,shell_exec,system" />
      </a-form-item>
      <a-form-item>
        <a-button type="primary" :loading="saving" @click="saveIni">保存 php.ini 配置</a-button>
      </a-form-item>
    </a-form>

    <a-modal v-model:visible="rawVisible" title="编辑 php.ini 原始内容" @ok="saveRaw" @cancel="rawVisible = false">
      <a-textarea v-model="iniRaw" :auto-size="{ minRows: 14, maxRows: 22 }" />
    </a-modal>
  </a-card>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import request from '@/utils/request'
import { Message } from '@arco-design/web-vue'

const loading = ref(false)
const saving = ref(false)
const versions = ref([])
const version = ref('')
const rawVisible = ref(false)
const iniRaw = ref('')

const iniForm = reactive({
  memory_limit: '',
  post_max_size: '',
  upload_max_filesize: '',
  max_execution_time: 300,
  disable_functions: '',
})

const fetchVersions = async () => {
  loading.value = true
  try {
    const res = await request.get('/php/versions')
    versions.value = res
    const def = res.find((v) => v.is_default) || res.find((v) => v.status === 'installed')
    if (def) {
      version.value = def.version
      await fetchIni()
    }
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
}

const onVersionChange = () => fetchIni()

const fetchIni = async () => {
  if (!version.value) return
  try {
    const res = await request.get(`/php/ini/${version.value}`)
    iniForm.memory_limit = res.memory_limit || ''
    iniForm.post_max_size = res.post_max_size || ''
    iniForm.upload_max_filesize = res.upload_max_filesize || ''
    iniForm.max_execution_time = res.max_execution_time || 300
    iniForm.disable_functions = res.disable_functions || ''
  } catch (e) {
    console.error(e)
  }
}

const saveIni = async () => {
  saving.value = true
  try {
    await request.post(`/php/ini/${version.value}`, { ...iniForm })
    Message.success('保存成功')
  } catch (e) {
    console.error(e)
  } finally {
    saving.value = false
  }
}

const showRaw = async () => {
  try {
    const res = await request.get(`/php/ini/${version.value}/raw`)
    iniRaw.value = res.content || ''
    rawVisible.value = true
  } catch (e) {
    console.error(e)
  }
}

const saveRaw = async () => {
  try {
    await request.post(`/php/ini/${version.value}/raw`, { content: iniRaw.value })
    Message.success('保存成功')
    rawVisible.value = false
  } catch (e) {
    console.error(e)
  }
}

onMounted(fetchVersions)
</script>
