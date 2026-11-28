<template>
  <div class="quick-speed-tools">
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
import { ref, onMounted } from 'vue'
import { Message } from '@arco-design/web-vue'
import {
  IconThunderbolt,
  IconTool,
  IconDelete,
  IconStorage,
  IconLock,
  IconHeart,
} from '@arco-design/web-vue/es/icon'
import request from '@/utils/request'

const iconMap = {
  Thunderbolt: IconThunderbolt,
  Tool: IconTool,
  Delete: IconDelete,
  Storage: IconStorage,
  Lock: IconLock,
  HeartHealth: IconHeart,
}

const tools = ref([])
const loadingToolId = ref('')
const resultVisible = ref(false)
const resultTitle = ref('')
const resultContent = ref('')

const fetchTools = async () => {
  try {
    const res = await request.get('/tools/list')
    tools.value = res || []
  } catch (error) {
    console.error('获取工具列表失败:', error)
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

onMounted(fetchTools)
</script>

<style scoped>
.quick-speed-tools {
  padding: 4px 0;
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
</style>
