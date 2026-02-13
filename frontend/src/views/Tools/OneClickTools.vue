<template>
  <div class="tools-container">
    <a-typography-title :heading="2">一键提速工具</a-typography-title>
    <a-typography-paragraph>
      将多个优化、修复步骤组合为一个原子化操作，用户点击即可完成全链路加速或故障恢复。
    </a-typography-paragraph>

    <a-row :gutter="20">
      <a-col :span="8" v-for="tool in tools" :key="tool.id" style="margin-bottom: 20px;">
        <a-card hoverable class="tool-card">
          <template #title>
            <a-space>
              <component :is="getIcon(tool.icon)" :style="{ fontSize: '20px', color: '#165DFF' }" />
              <span>{{ tool.name }}</span>
            </a-space>
          </template>
          <p class="tool-desc">{{ tool.description }}</p>
          <template #actions>
            <a-button type="primary" :loading="executingId === tool.id" @click="handleExecute(tool)">
              立即执行
            </a-button>
          </template>
        </a-card>
      </a-col>
    </a-row>

    <!-- 执行进度弹窗 -->
    <a-modal v-model:visible="visible" :title="currentTool?.name" :footer="false" @close="handleClose">
      <div class="execution-content">
        <a-steps direction="vertical" :current="currentStepIndex">
          <a-step v-for="(res, index) in executionResults" :key="index" :title="res.step" :description="res.status === 'success' ? '已完成' : '执行中'">
            <template #icon v-if="index === currentStepIndex && !isFinished">
              <icon-loading />
            </template>
          </a-step>
        </a-steps>
        <div v-if="isFinished" class="finished-report">
          <a-result status="success" title="执行完成">
            <template #extra>
              <a-button type="primary" @click="visible = false">查看报告</a-button>
            </template>
          </a-result>
        </div>
      </div>
    </a-modal>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { 
  IconThunderbolt, 
  IconTool, 
  IconDelete, 
  IconStorage, 
  IconLock, 
  IconHeart,
  IconLoading
} from '@arco-design/web-vue/es/icon'
import request from '@/utils/request'
import { Message } from '@arco-design/web-vue'

const tools = ref([])
const executingId = ref(null)
const visible = ref(false)
const currentTool = ref(null)
const executionResults = ref([])
const currentStepIndex = ref(0)
const isFinished = ref(false)

console.log('OneClick component setup')

const getIcon = (name) => {
  const icons = {
    Thunderbolt: IconThunderbolt,
    Tool: IconTool,
    Delete: IconDelete,
    Storage: IconStorage,
    Lock: IconLock,
    HeartHealth: IconHeart
  }
  return icons[name] || IconTool
}

const fetchTools = async () => {
  console.log('Fetching tools...')
  try {
    const res = await request.get('/tools/list')
    console.log('Tools fetched:', res)
    if (res && res.length > 0) {
      tools.value = res
    } else {
      console.warn('No tools returned from API, loading mock data')
      loadMockData()
    }
  } catch (e) {
    console.error('Fetch tools failed:', e)
    Message.error('获取工具列表失败，使用模拟数据')
    loadMockData()
  }
}

const loadMockData = () => {
  tools.value = [
    { id: 'full_optimize', name: '一键全站极速优化', description: '开启四层缓存、图片转WebP、合并压缩CSS/JS、数据库优化等', icon: 'Thunderbolt' },
    { id: 'env_fix', name: '一键环境修复', description: '检测并修复OLS、MariaDB、Redis服务状态及文件权限', icon: 'Tool' },
    { id: 'clean_junk', name: '一键清理垃圾', description: '清理修订版本、草稿、垃圾评论、过期transient等', icon: 'Delete' },
    { id: 'db_optimize', name: '一键数据库优化', description: '对所有数据表执行 OPTIMIZE 和 REPAIR', icon: 'Storage' },
    { id: 'reset_perm', name: '一键重置权限', description: '将所有站点目录及文件权限重置为安全推荐值', icon: 'Lock' },
    { id: 'fix_wp', name: '一键修复故障', description: '自动修复常见WordPress白屏、内存耗尽、插件冲突等问题', icon: 'HeartHealth' }
  ]
}

const handleExecute = async (tool) => {
  if (!tool) return
  
  Message.info(`准备执行: ${tool.name}`)
  
  currentTool.value = tool
  executingId.value = tool.id
  visible.value = true
  executionResults.value = []
  currentStepIndex.value = 0
  isFinished.value = false

  console.log('Executing tool:', tool.id)

  try {
    const res = await request.post(`/tools/execute/${tool.id}`)
    console.log('Execution response:', res)
    
    if (!res || !res.results) {
      throw new Error('Invalid response from server')
    }
    
    // 模拟流式展示步骤
    for (let i = 0; i < res.results.length; i++) {
      currentStepIndex.value = i
      executionResults.value.push(res.results[i])
      await new Promise(resolve => setTimeout(resolve, 600))
    }
    
    isFinished.value = true
    Message.success(`${tool.name} 执行成功`)
  } catch (e) {
    console.error('Execution failed:', e)
    Message.error('执行失败: ' + (e.message || '未知错误'))
    // 不要立即关闭弹窗，让用户看到报错信息（如果有步骤显示的话）
    if (executionResults.value.length === 0) {
      visible.value = false
    }
  } finally {
    executingId.value = null
  }
}

const handleClose = () => {
  visible.value = false
}

onMounted(() => {
  fetchTools()
})
</script>

<style scoped lang="scss">
.tools-container {
  padding: 0 0 20px 0;
  .tool-card {
    height: 100%;
    .tool-desc {
      color: var(--arco-color-text-3);
      height: 40px;
      overflow: hidden;
      text-overflow: ellipsis;
      display: -webkit-box;
      -webkit-line-clamp: 2;
      -webkit-box-orient: vertical;
    }
  }
  .execution-content {
    padding: 20px;
    max-height: 400px;
    overflow-y: auto;
  }
  .finished-report {
    margin-top: 20px;
    border-top: 1px solid var(--arco-color-border);
    padding-top: 20px;
  }
}
</style>
