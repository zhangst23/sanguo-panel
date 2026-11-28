<template>
  <div class="tools-container">
    <a-typography-title :heading="2">AI 管理</a-typography-title>


    <a-tabs v-model:active-key="activeTab" class="tools-tabs">
      <!-- AI 修复 -->
      <a-tab-pane key="ai" title="AI 修复">
        <a-row :gutter="16">
          <a-col :xs="24" :md="10">
            <a-card title="AI诊断" :bordered="false" class="tool-card">
              <a-form :model="aiForm" layout="vertical">
                <a-form-item field="site_id" label="网站">
                  <a-select
                    v-model="aiForm.site_id"
                    placeholder="请选择站点"
                    allow-clear
                    allow-search
                  >
                    <a-option v-for="s in siteList" :key="s.id" :value="s.id">
                      {{ s.domain }}
                    </a-option>
                  </a-select>
                </a-form-item>
                <a-form-item field="issue_type" label="问题类型">
                  <a-select v-model="aiForm.issue_type" placeholder="请选择问题类型">
                    <a-option v-for="o in issueOptions" :key="o.value" :value="o.value">
                      {{ o.label }}
                    </a-option>
                  </a-select>
                </a-form-item>
                <a-space>
                  <a-button
                    type="primary"
                    :loading="diagnosing"
                    @click="handleDiagnose"
                  >
                    <template #icon><icon-search /></template>
                    开始诊断
                  </a-button>
                  <a-button
                    type="primary"
                    status="success"
                    :loading="fixing"
                    @click="handleFix"
                  >
                    <template #icon><icon-bulb /></template>
                    AI修复
                  </a-button>
                </a-space>
              </a-form>
            </a-card>
          </a-col>

          <a-col :xs="24" :md="14">
            <a-card title="AI分析结果" :bordered="false" class="tool-card">
              <a-textarea
                v-model="aiResult"
                :auto-size="{ minRows: 16, maxRows: 28 }"
                placeholder="点击“开始诊断”或“AI修复”后，AI 分析结果将显示在此处"
                readonly
                class="ai-result"
              />
            </a-card>
          </a-col>
        </a-row>
      </a-tab-pane>

      <!-- 模型配置 -->
      <a-tab-pane key="model" title="模型">
        <a-row :gutter="16">
          <a-col :xs="24" :md="10">
            <a-card title="模型配置" :bordered="false" class="tool-card">
              <a-form :model="aiSettingsForm" layout="vertical" @submit="handleAISave">
                <a-form-item label="模型" required>
                  <a-input v-model="aiSettingsForm.model" placeholder="请输入模型名称" />
                </a-form-item>
                <a-form-item label="API Key" required>
                  <a-input
                    v-model="aiSettingsForm.api_key"
                    :type="aiSettingsKeyVisible ? 'text' : 'password'"
                    placeholder="请输入 DeepSeek API Key"
                  >
                    <template #suffix>
                      <icon-eye v-if="!aiSettingsKeyVisible" @click="aiSettingsKeyVisible = true" style="cursor:pointer" />
                      <icon-eye-invisible v-else @click="aiSettingsKeyVisible = false" style="cursor:pointer" />
                    </template>
                  </a-input>
                </a-form-item>
                <a-button type="primary" html-type="submit" :loading="aiSettingsSaving">
                  保存
                </a-button>
              </a-form>
            </a-card>
          </a-col>
        </a-row>
      </a-tab-pane>

      <!-- Agent 接入 -->
      <a-tab-pane key="agent" title="Agent接入">
        <AgentAccess />
      </a-tab-pane>
    </a-tabs>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { Message } from '@arco-design/web-vue'
import AgentAccess from './AgentAccess.vue'
import {
  IconSearch,
  IconBulb,
  IconEye,
  IconEyeInvisible
} from '@arco-design/web-vue/es/icon'
import request from '@/utils/request'

const activeTab = ref('ai')

// AI 修复
const siteList = ref([])
const aiForm = reactive({ site_id: undefined, issue_type: undefined })
const aiResult = ref('')
const diagnosing = ref(false)
const fixing = ref(false)

// AI 设置（模型 / DeepSeek API Key）
const aiSettingsForm = reactive({ model: 'DeepSeek-V4-Pro', api_key: '' })
const aiSettingsKeyVisible = ref(false)
const aiSettingsSaving = ref(false)

const issueOptions = [
  { value: '500', label: '网站500错误' },
  { value: 'wp_admin', label: 'wp-admin无法访问' },
  { value: 'ssl', label: 'SSL证书故障' },
  { value: 'db', label: '数据库连接异常' },
  { value: 'cache_perm', label: '缓存/权限异常' },
  { value: 'perf', label: '性能问题' }
]

const fetchSites = async () => {
  try {
    const res = await request.get('/sites/')
    siteList.value = res || []
  } catch (error) {
    console.error('获取站点列表失败:', error)
  }
}

const handleDiagnose = async () => {
  if (!aiForm.site_id || !aiForm.issue_type) {
    Message.warning('请先选择网站和问题类型')
    return
  }
  diagnosing.value = true
  try {
    const res = await request.post('/tools/ai/diagnose', {
      site_id: aiForm.site_id,
      issue_type: aiForm.issue_type
    })
    aiResult.value = res.report || ''
    Message.success('诊断完成')
  } catch (error) {
    Message.error('诊断失败: ' + (error.response?.data?.detail || error.message))
  } finally {
    diagnosing.value = false
  }
}

const handleFix = async () => {
  if (!aiForm.site_id || !aiForm.issue_type) {
    Message.warning('请先选择网站和问题类型')
    return
  }
  fixing.value = true
  try {
    const res = await request.post('/tools/ai/fix', {
      site_id: aiForm.site_id,
      issue_type: aiForm.issue_type
    })
    aiResult.value = res.report || ''
    Message.success('AI 修复方案已生成')
  } catch (error) {
    Message.error('修复失败: ' + (error.response?.data?.detail || error.message))
  } finally {
    fixing.value = false
  }
}

const fetchAIConfig = async () => {
  try {
    const res = await request.get('/system/ai-config')
    aiSettingsForm.model = res.model || 'DeepSeek-V4-Pro'
    aiSettingsForm.api_key = res.has_key ? '••••••••' : ''
  } catch (error) {
    console.error(error)
  }
}

const handleAISave = async () => {
  aiSettingsSaving.value = true
  try {
    await request.post('/system/ai-config', {
      model: aiSettingsForm.model,
      api_key: aiSettingsForm.api_key
    })
    Message.success('AI 配置已保存')
    aiSettingsForm.api_key = '••••••••'
  } catch (error) {
    Message.error(error.response?.data?.detail || '保存失败')
  } finally {
    aiSettingsSaving.value = false
  }
}

onMounted(() => {
  fetchSites()
  fetchAIConfig()
})
</script>

<style scoped>
.tools-container {
  padding: 4px;
}
.page-desc {
  color: var(--color-text-3);
  margin-bottom: 16px;
}
.tools-tabs {
  margin-top: 8px;
}
.tool-card {
  margin-bottom: 16px;
  height: 100%;
}
.ai-result {
  font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace;
  font-size: 13px;
  line-height: 1.7;
  white-space: pre;
}
</style>
