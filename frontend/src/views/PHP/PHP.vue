<template>
  <div class="php-container">
    <div class="header-section">
      <a-typography-title :heading="2">PHP 管理</a-typography-title>
      <a-button type="outline" @click="expertMode = !expertMode">
        {{ expertMode ? '简易模式' : '专家模式' }}
      </a-button>
    </div>

    <a-tabs default-active-key="1">
      <a-tab-pane key="1" title="版本管理">
        <a-row :gutter="20">
          <a-col :span="24">
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
                      <a-button type="text" size="small" v-if="record.status === 'installed'">管理扩展</a-button>
                      <a-button type="text" size="small" v-if="record.status === 'installed'">php.ini</a-button>
                      <a-button type="outline" size="small" v-if="record.status === 'not_installed'">安装</a-button>
                    </a-space>
                  </template>
                </a-table-column>
              </template>
            </a-table>
          </a-col>
        </a-row>
      </a-tab-pane>

      <a-tab-pane key="2" title="性能优化" v-if="expertMode">
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

      <a-tab-pane key="3" title="常用设置" v-if="expertMode">
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
            <a-button type="primary">保存配置并重载 PHP</a-button>
          </a-form>
        </a-card>
      </a-tab-pane>
    </a-tabs>
  </div>
</template>

<script setup>
import { ref, onMounted, reactive } from 'vue'
import request from '@/utils/request'
import { Message } from '@arco-design/web-vue'

const loading = ref(false)
const expertMode = ref(false)
const versions = ref([])
const selectedTemplate = ref('speed')
const phpConfig = reactive({
  memory_limit: '',
  upload_max_filesize: '',
  post_max_size: '',
  max_execution_time: 300,
  disable_functions: ''
})

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

const fetchConfig = async (version) => {
  try {
    const res = await request.get(`/php/${version}/config`)
    Object.assign(phpConfig, res)
  } catch (error) {
    console.error(error)
  }
}

const applyTemplate = async () => {
  try {
    await request.post(`/php/8.2/config/optimize`, { template: selectedTemplate.value })
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
