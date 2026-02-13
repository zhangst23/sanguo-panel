<template>
  <div class="php-container">
    <div class="header-section">
      <a-typography-title :heading="2">PHP 管理</a-typography-title>
    </div>

    <a-tabs v-model:active-key="activeTab">
      <a-tab-pane key="1" title="版本管理">
        <a-table :data="versions" :loading="loading">
          <template #columns>
            <a-table-column title="版本" data-index="version">
              <template #cell="{ record }">
                PHP {{ record.version }}
                <a-tag v-if="record.is_default" color="green" size="small" style="margin-left: 8px;">默认</a-tag>
              </template>
            </a-table-column>
            <a-table-column title="状态" data-index="status">
              <template #cell="{ record }">
                <a-tag :color="record.status === 'installed' ? 'arcoblue' : 'gray'">
                  {{ record.status === 'installed' ? '已安装' : '未安装' }}
                </a-tag>
              </template>
            </a-table-column>
            <a-table-column title="操作">
              <template #cell="{ record }">
                <a-space>
                  <template v-if="record.status === 'installed'">
                    <a-button type="text" size="small" @click="handleExtensions(record)">管理扩展</a-button>
                    <a-button type="text" size="small" @click="handleEditIni(record)">php.ini</a-button>
                    <a-button type="text" size="small" @click="handleLog(record)">日志</a-button>
                  </template>
                  <a-button type="outline" size="small" v-else @click="handleInstall(record)" :loading="installing === record.version">安装</a-button>
                </a-space>
              </template>
            </a-table-column>
          </template>
        </a-table>
      </a-tab-pane>

      <a-tab-pane key="2" title="性能优化">
        <a-row :gutter="20">
          <a-col :span="24">
            <a-card title="OPcache 优化模板">
              <a-radio-group v-model="selectedTemplate" type="button" @change="applyTemplate">
                <a-radio value="speed">极速模式 (推荐)</a-radio>
                <a-radio value="stable">稳定模式</a-radio>
                <a-radio value="compatible">兼容模式</a-radio>
              </a-radio-group>
              <div style="margin-top: 20px;">
                <a-descriptions title="模板详情" :column="1" bordered>
                  <a-descriptions-item label="opcache.memory_consumption">{{ templateDetails[selectedTemplate].memory }}</a-descriptions-item>
                  <a-descriptions-item label="opcache.revalidate_freq">{{ templateDetails[selectedTemplate].freq }}</a-descriptions-item>
                  <a-descriptions-item label="适用场景">{{ templateDetails[selectedTemplate].desc }}</a-descriptions-item>
                </a-descriptions>
              </div>
            </a-card>
          </a-col>
        </a-row>
      </a-tab-pane>

      <a-tab-pane key="3" title="常用设置">
        <a-card title="php.ini 可视化配置">
          <a-form :model="phpConfig" layout="vertical" style="max-width: 600px;">
            <a-form-item label="memory_limit (内存限制)">
              <a-input v-model="phpConfig.memory_limit" placeholder="256M" />
            </a-form-item>
            <a-form-item label="upload_max_filesize (最大上传文件)">
              <a-input v-model="phpConfig.upload_max_filesize" placeholder="64M" />
            </a-form-item>
            <a-form-item label="post_max_size (最大 POST 大小)">
              <a-input v-model="phpConfig.post_max_size" placeholder="64M" />
            </a-form-item>
            <a-form-item label="max_execution_time (最大执行时间)">
              <a-input-number v-model="phpConfig.max_execution_time" placeholder="300" />
            </a-form-item>
            <a-form-item label="disable_functions (禁用函数)">
              <a-textarea v-model="phpConfig.disable_functions" placeholder="exec,shell_exec,system" />
            </a-form-item>
            <a-button type="primary" @click="handleSaveConfig">保存配置并重载 PHP</a-button>
          </a-form>
        </a-card>
      </a-tab-pane>
    </a-tabs>

    <!-- 扩展管理弹窗 -->
    <a-modal v-model:visible="extModalVisible" :title="`PHP ${currentVersion?.version} 扩展管理`" width="600px">
      <a-table :data="extensions" :loading="extLoading" :pagination="false">
        <template #columns>
          <a-table-column title="扩展名称" data-index="name">
            <template #cell="{ record }">
              {{ record.name }}
              <a-tag v-if="isCoreExtension(record.name)" color="blue" size="mini" style="margin-left: 8px;">核心</a-tag>
            </template>
          </a-table-column>
          <a-table-column title="描述" data-index="description"></a-table-column>
          <a-table-column title="状态">
            <template #cell="{ record }">
              <a-switch 
                :model-value="isCoreExtension(record.name) ? true : record.installed" 
                @change="(val) => handleToggleExtension(record, val)"
                :loading="extActionLoading === record.name"
                :disabled="isCoreExtension(record.name)"
              />
            </template>
          </a-table-column>
        </template>
      </a-table>
    </a-modal>

    <!-- 日志弹窗 -->
    <a-modal v-model:visible="logModalVisible" :title="`PHP ${currentVersion?.version} 错误日志`" width="800px">
      <div class="log-container">
        <pre>{{ errorLog }}</pre>
      </div>
      <template #footer>
        <a-button @click="fetchErrorLog">刷新</a-button>
        <a-button type="primary" status="danger" @click="handleClearLog">清空日志</a-button>
      </template>
    </a-modal>
  </div>
</template>

<script setup>
import { ref, onMounted, reactive } from 'vue'
import request from '@/utils/request'
import { Message } from '@arco-design/web-vue'

const loading = ref(false)
const installing = ref(null)
const versions = ref([])
const activeTab = ref('1')
const selectedTemplate = ref('speed')
const phpConfig = reactive({
  memory_limit: '',
  upload_max_filesize: '',
  post_max_size: '',
  max_execution_time: 300,
  disable_functions: ''
})

// 扩展管理状态
const extModalVisible = ref(false)
const extLoading = ref(false)
const extActionLoading = ref(null)
const extensions = ref([])
const currentVersion = ref(null)

// 日志状态
const logModalVisible = ref(false)
const errorLog = ref('')

// 核心扩展列表（禁止关闭）
const coreExtensions = ['mysqli', 'redis', 'opcache', 'exif', 'curl']

const isCoreExtension = (name) => {
  return coreExtensions.includes(name.toLowerCase())
}

const templateDetails = {
  speed: { memory: '256', freq: '60', desc: '追求最高性能，减少文件检查频率' },
  stable: { memory: '128', freq: '2', desc: '性能与稳定平衡，适合生产环境' },
  compatible: { memory: '64', freq: '0', desc: '最强兼容性，每次请求都检查文件更新' }
}

const fetchVersions = async () => {
  loading.value = true
  try {
    const res = await request.get('/php/versions')
    versions.value = res
  } catch (error) {
    console.error(error)
  } finally {
    loading.value = false
  }
}

const handleInstall = async (record) => {
  installing.value = record.version
  try {
    await request.post(`/php/install/${record.version}`)
    Message.success(`PHP ${record.version} 安装任务已提交`)
    fetchVersions()
  } catch (error) {
    console.error(error)
  } finally {
    installing.value = null
  }
}

const handleExtensions = async (record) => {
  currentVersion.value = record
  extModalVisible.value = true
  extLoading.value = true
  try {
    const res = await request.get(`/php/${record.version}/extensions`)
    extensions.value = res
  } catch (error) {
    console.error(error)
  } finally {
    extLoading.value = false
  }
}

const handleToggleExtension = async (extension, enabled) => {
  extActionLoading.value = extension.name
  try {
    await request.post(`/php/${currentVersion.value.version}/extensions/toggle`, {
      extension: extension.name,
      enabled
    })
    Message.success(`${extension.name} ${enabled ? '安装' : '卸载'}成功`)
    extension.installed = enabled
  } catch (error) {
    console.error(error)
  } finally {
    extActionLoading.value = null
  }
}

const handleEditIni = (record) => {
  currentVersion.value = record
  fetchConfig(record.version)
  // 切换到常用设置页签
  activeTab.value = '3'
}

const handleLog = (record) => {
  currentVersion.value = record
  logModalVisible.value = true
  fetchErrorLog()
}

const fetchErrorLog = async () => {
  try {
    const res = await request.get(`/php/${currentVersion.value.version}/log`)
    errorLog.value = res.log
  } catch (error) {
    console.error(error)
  }
}

const handleClearLog = async () => {
  try {
    await request.post(`/php/${currentVersion.value.version}/log/clear`)
    Message.success('日志已清空')
    errorLog.value = ''
  } catch (error) {
    console.error(error)
  }
}

const fetchConfig = async (version) => {
  try {
    const res = await request.get(`/php/${version}/config`)
    Object.assign(phpConfig, res)
  } catch (error) {
    console.error(error)
  }
}

const handleSaveConfig = async () => {
  const version = currentVersion.value?.version || '8.2'
  try {
    await request.post(`/php/${version}/config`, phpConfig)
    Message.success('配置已保存并重载 PHP')
  } catch (error) {
    console.error(error)
  }
}

const applyTemplate = async () => {
  const version = currentVersion.value?.version || '8.2'
  try {
    await request.post(`/php/${version}/config/optimize`, { template: selectedTemplate.value })
    Message.success('模板应用成功')
  } catch (error) {
    console.error(error)
  }
}

onMounted(() => {
  fetchVersions()
  fetchConfig('8.2')
})
</script>

<style scoped>
.php-container {
  padding: 20px;
}
.header-section {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}
</style>
