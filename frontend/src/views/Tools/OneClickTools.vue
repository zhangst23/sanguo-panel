<template>
  <div class="tools-container">
    <a-typography-title :heading="2">AI工具</a-typography-title>
   

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

      <!-- 一键提速工具 -->
      <a-tab-pane key="tools" title="一键提速工具">
        <a-row :gutter="16">
          <a-col :xs="24" :md="8" v-for="tool in tools" :key="tool.id">
            <a-card hoverable class="tool-card" :bordered="false">
              <div class="tool-header">
                <component :is="iconMap[tool.icon]" :size="26" class="tool-icon" />
                <div class="tool-title">{{ tool.name }}</div>
              </div>
              <div class="tool-desc">{{ tool.description }}</div>
              <a-button
                long
                type="primary"
                :loading="loadingToolId === tool.id"
                @click="runTool(tool)"
              >
                立即执行
              </a-button>
            </a-card>
          </a-col>
        </a-row>
      </a-tab-pane>
    </a-tabs>

    <!-- 工具执行结果弹窗 -->
    <a-modal
      v-model:visible="resultVisible"
      :title="resultTitle"
      :footer="false"
      :width="560"
    >
      <a-typography-paragraph v-if="resultContent">
        {{ resultContent }}
      </a-typography-paragraph>
      <a-empty v-else description="暂无结果" />
    </a-modal>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, h } from 'vue'
import { Message } from '@arco-design/web-vue'
import {
  IconThunderbolt,
  IconTool,
  IconDelete,
  IconStorage,
  IconLock,
  IconHeart,
  IconSearch,
  IconBulb
} from '@arco-design/web-vue/es/icon'
import request from '@/utils/request'

const activeTab = ref('ai')

const iconMap = {
  Thunderbolt: IconThunderbolt,
  Tool: IconTool,
  Delete: IconDelete,
  Storage: IconStorage,
  Lock: IconLock,
  HeartHealth: IconHeart
}

const tools = ref([])
const loadingToolId = ref('')
const resultVisible = ref(false)
const resultTitle = ref('')
const resultContent = ref('')

// AI 修复
const siteList = ref([])
const aiForm = reactive({ site_id: undefined, issue_type: undefined })
const aiResult = ref('')
const diagnosing = ref(false)
const fixing = ref(false)

const issueOptions = [
  { value: '500', label: '网站500错误' },
  { value: 'wp_admin', label: 'wp-admin无法访问' },
  { value: 'ssl', label: 'SSL证书故障' },
  { value: 'db', label: '数据库连接异常' },
  { value: 'cache_perm', label: '缓存/权限异常' },
  { value: 'perf', label: '性能问题' }
]

const fetchTools = async () => {
  try {
    const res = await request.get('/tools/list')
    tools.value = res || []
  } catch (error) {
    console.error('获取工具列表失败:', error)
  }
}

const fetchSites = async () => {
  try {
    const res = await request.get('/sites/')
    siteList.value = res || []
  } catch (error) {
    console.error('获取站点列表失败:', error)
  }
}

const runTool = async (tool) => {
  loadingToolId.value = tool.id
  try {
    const res = await request.post(`/tools/execute/${tool.id}`)
    resultTitle.value = `${tool.name} - 执行结果`
    resultContent.value = res && res.message ? res.message : '执行完成'
    resultVisible.value = true
  } catch (error) {
    Message.error('执行失败: ' + (error.response?.data?.detail || error.message))
  } finally {
    loadingToolId.value = ''
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

onMounted(() => {
  fetchTools()
  fetchSites()
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
.tool-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 10px;
}
.tool-icon {
  color: rgb(var(--primary-6));
}
.tool-title {
  font-size: 16px;
  font-weight: 600;
}
.tool-desc {
  color: var(--color-text-3);
  min-height: 44px;
  margin-bottom: 16px;
}
.ai-result {
  font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace;
  font-size: 13px;
  line-height: 1.7;
  white-space: pre;
}
</style>
