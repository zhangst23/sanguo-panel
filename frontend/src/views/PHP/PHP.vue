<template>
  <div class="php-container">
    <a-card title="版本管理" :bordered="false" style="margin-bottom: 20px;">
      <a-table :data="versions" :loading="loading" :pagination="false">
        <template #columns>
          <a-table-column title="版本" data-index="version" />
          <a-table-column title="LSAPI 名称" data-index="lsapi_name" />
          <a-table-column title="状态">
            <template #cell="{ record }">
              <a-tag :color="record.installed ? 'green' : 'gray'">
                {{ record.installed ? '已安装' : '未安装' }}
              </a-tag>
            </template>
          </a-table-column>
          <a-table-column title="操作">
            <template #cell="{ record }">
              <a-button
                type="text"
                size="small"
                :disabled="!record.installed"
                @click="() => showPhpIni(record)"
              >php.ini</a-button>
              <a-button type="text" size="small" @click="() => handleInstall(record)">安装</a-button>
            </template>
          </a-table-column>
        </template>
      </a-table>
    </a-card>

    <a-card title="性能优化" :bordered="false" style="margin-bottom: 20px;">
      <a-radio-group v-model="perfMode" type="button" @change="onPerfChange">
        <a-radio value="high">高性能</a-radio>
        <a-radio value="balanced">均衡</a-radio>
        <a-radio value="safe">安全优先</a-radio>
      </a-radio-group>
      <a-descriptions :column="1" bordered style="margin-top: 16px;" size="medium">
        <a-descriptions-item label="内存限制">{{ perfPreset.memory_limit }}</a-descriptions-item>
        <a-descriptions-item label="POST 最大尺寸">{{ perfPreset.post_max_size }}</a-descriptions-item>
        <a-descriptions-item label="上传文件限制">{{ perfPreset.upload_max_filesize }}</a-descriptions-item>
        <a-descriptions-item label="最大执行时间">{{ perfPreset.max_execution_time }} 秒</a-descriptions-item>
        <a-descriptions-item label="禁用函数">{{ perfPreset.disable_functions }}</a-descriptions-item>
      </a-descriptions>
    </a-card>

    <a-card title="常用设置 (php.ini 可视化配置)" :bordered="false">
      <a-form :model="iniForm" layout="vertical">
        <a-form-item label="当前 PHP 版本">
          <a-select v-model="currentVersion" style="width: 240px;" @change="onVersionChange">
            <a-option v-for="v in versions.filter(v => v.installed)" :key="v.version" :value="v.version">
              {{ v.version }}
            </a-option>
          </a-select>
        </a-form-item>
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
          <a-button type="primary" @click="saveIni">保存 php.ini 配置</a-button>
        </a-form-item>
      </a-form>
    </a-card>

    <a-modal v-model:visible="iniModalVisible" title="编辑 php.ini 原始内容" @ok="saveRawIni" @cancel="iniModalVisible = false">
      <a-textarea v-model="iniRaw" :auto-size="{ minRows: 12, maxRows: 20 }" />
    </a-modal>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed } from 'vue'
import request from '@/utils/request'
import { Message } from '@arco-design/web-vue'

const loading = ref(false)
const versions = ref([])
const currentVersion = ref('')
const perfMode = ref('balanced')
const iniModalVisible = ref(false)
const iniRaw = ref('')

const iniForm = reactive({
  memory_limit: '',
  post_max_size: '',
  upload_max_filesize: '',
  max_execution_time: 300,
  disable_functions: ''
})

const presets = {
  high: {
    memory_limit: '512M',
    post_max_size: '128M',
    upload_max_filesize: '128M',
    max_execution_time: 600,
    disable_functions: ''
  },
  balanced: {
    memory_limit: '256M',
    post_max_size: '64M',
    upload_max_filesize: '64M',
    max_execution_time: 300,
    disable_functions: 'exec,shell_exec,system'
  },
  safe: {
    memory_limit: '128M',
    post_max_size: '32M',
    upload_max_filesize: '32M',
    max_execution_time: 120,
    disable_functions: 'exec,shell_exec,system,passthru,popen,proc_open'
  }
}

const perfPreset = computed(() => presets[perfMode.value])

const fetchVersions = async () => {
  loading.value = true
  try {
    const res = await request.get('/php/versions')
    versions.value = res
    if (res.length && res[0].installed) {
      currentVersion.value = res[0].version
      onVersionChange()
    }
  } catch (error) {
    console.error(error)
  } finally {
    loading.value = false
  }
}

const onVersionChange = async () => {
  await fetchPhpIni(currentVersion.value)
}

const fetchPhpIni = async (version) => {
  try {
    const res = await request.get(`/php/ini/${version}`)
    iniForm.memory_limit = res.memory_limit || ''
    iniForm.post_max_size = res.post_max_size || ''
    iniForm.upload_max_filesize = res.upload_max_filesize || ''
    iniForm.max_execution_time = res.max_execution_time || 300
    iniForm.disable_functions = res.disable_functions || ''
  } catch (error) {
    console.error(error)
  }
}

const onPerfChange = (mode) => {
  const p = presets[mode]
  iniForm.memory_limit = p.memory_limit
  iniForm.post_max_size = p.post_max_size
  iniForm.upload_max_filesize = p.upload_max_filesize
  iniForm.max_execution_time = p.max_execution_time
  iniForm.disable_functions = p.disable_functions
  Message.info('已套用预设，请点击保存生效')
}

const showPhpIni = async (record) => {
  currentVersion.value = record.version
  await fetchPhpIni(record.version)
  await fetchRawIni(record.version)
  iniModalVisible.value = true
}

const fetchRawIni = async (version) => {
  try {
    const res = await request.get(`/php/ini/${version}/raw`)
    iniRaw.value = res.content || ''
  } catch (error) {
    console.error(error)
  }
}

const saveRawIni = async () => {
  try {
    await request.post(`/php/ini/${currentVersion.value}/raw`, { content: iniRaw.value })
    Message.success('保存成功')
    iniModalVisible.value = false
  } catch (error) {
    console.error(error)
  }
}

const saveIni = async () => {
  try {
    await request.post(`/php/ini/${currentVersion.value}`, { ...iniForm })
    Message.success('保存成功')
  } catch (error) {
    console.error(error)
  }
}

const handleInstall = async (record) => {
  Message.info(`安装 PHP ${record.version} 功能开发中`)
}

onMounted(() => {
  fetchVersions()
})
</script>

<style scoped>
.php-container {
  padding: 0;
}
</style>
