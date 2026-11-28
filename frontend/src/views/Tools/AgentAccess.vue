<template>
  <div class="agent-access">
    <!-- MCP 接入 -->
    <a-card title="MCP 接入" class="agent-card">
      <template #extra>
        <a-tag color="green">匿名只读 · 需面板 Token</a-tag>
      </template>
      <div class="agent-hint">
        填一个地址，多出 {{ info.tools.length || 3 }} 个工具。支持 Claude 桌面版、Cursor、OpenCode 等远程 MCP 客户端。
      </div>
      <div class="code-block">
        <div class="code-head">
          <span>客户端配置（mcpServers）</span>
          <a-button size="small" type="text" @click="copyText(mcpConfig, '配置已复制')">
            <template #icon><icon-copy /></template>
            复制
          </a-button>
        </div>
        <pre>{{ mcpConfig }}</pre>
      </div>

      <a-table
        :columns="toolColumns"
        :data="info.tools"
        :pagination="false"
        row-key="name"
        size="small"
        style="margin-top: 16px"
      />
      <div class="agent-hint">MCP 工具仅提供查询能力，不会修改站点或系统配置。</div>
    </a-card>

    <!-- Skill 接入 -->
    <a-card title="Skill 接入" class="agent-card">
      <div class="agent-hint">装一次，以后不用再更新。Claude Code、Codex、Gemini CLI、OpenCode 这类支持 Agent Skills 的工具都能装。</div>
      <a-steps :current="3" size="small" class="agent-steps">
        <a-step title="复制安装提示词发给你的 Agent" />
        <a-step title="开一个新会话" />
        <a-step title="问一句试试" />
      </a-steps>

      <div class="code-block">
        <div class="code-head">
          <span>安装提示词</span>
          <a-button size="small" type="text" @click="copyText(prompt, '提示词已复制')">
            <template #icon><icon-copy /></template>
            复制
          </a-button>
        </div>
        <pre>{{ prompt }}</pre>
      </div>

      <div class="agent-hint">
        Skill 说明文件地址：
        <a-link @click="copyText(info.skill_url, '地址已复制')">{{ info.skill_url || '加载中...' }}</a-link>
      </div>

      <div class="agent-hint">装好后可以这样问：</div>
      <ul class="agent-questions">
        <li>服务器现在正常吗？</li>
        <li>我有哪些站点？</li>
        <li>最近面板做过哪些操作？</li>
      </ul>
    </a-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { Message } from '@arco-design/web-vue'
import { IconCopy } from '@arco-design/web-vue/es/icon'
import request from '@/utils/request'

const info = ref({ mcp_url: '', skill_url: '', tools: [] })
const prompt = ref('')

const toolColumns = [
  { title: '工具名', dataIndex: 'name', width: 160 },
  { title: '说明', dataIndex: 'description' },
]

const mcpConfig = computed(() => JSON.stringify({
  mcpServers: {
    'sanguo-panel': {
      type: 'http',
      url: info.value.mcp_url || `${window.location.origin}/api/v1/agent/mcp`,
      headers: { Authorization: 'Bearer <你的面板 Token>' },
    },
  },
}, null, 2))

const copyText = async (text, successText) => {
  if (!text) return
  try {
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(text)
    } else {
      const textarea = document.createElement('textarea')
      textarea.value = text
      textarea.style.position = 'fixed'
      textarea.style.opacity = '0'
      document.body.appendChild(textarea)
      textarea.select()
      document.execCommand('copy')
      document.body.removeChild(textarea)
    }
    Message.success(successText)
  } catch (error) {
    Message.error('复制失败，请手动复制')
  }
}

const fetchInfo = async () => {
  try {
    info.value = await request.get('/agent/info')
  } catch (error) {
    Message.error(error.response?.data?.detail || '加载接入信息失败')
  }
}

const fetchPrompt = async () => {
  try {
    const res = await request.get('/agent/skill/prompt')
    prompt.value = res.prompt || ''
  } catch (error) {
    Message.error(error.response?.data?.detail || '加载安装提示词失败')
  }
}

onMounted(() => {
  fetchInfo()
  fetchPrompt()
})
</script>

<style scoped>
.agent-access {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.agent-card {
  margin-bottom: 0;
}
.agent-hint {
  font-size: 13px;
  color: var(--color-text-3);
  line-height: 1.8;
  margin-bottom: 12px;
}
.agent-steps {
  margin: 8px 0 20px;
}
.code-block {
  background: var(--color-fill-1);
  border: 1px solid var(--color-border-1);
  border-radius: 6px;
  overflow: hidden;
}
.code-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 10px;
  font-size: 12px;
  color: var(--color-text-2);
  border-bottom: 1px solid var(--color-border-1);
}
.code-block pre {
  margin: 0;
  padding: 12px;
  font-family: 'SFMono-Regular', Consolas, Menlo, monospace;
  font-size: 12px;
  line-height: 1.7;
  white-space: pre-wrap;
  word-break: break-all;
}
.agent-questions {
  margin: 0;
  padding-left: 20px;
  font-size: 13px;
  color: var(--color-text-2);
  line-height: 1.9;
}
</style>
