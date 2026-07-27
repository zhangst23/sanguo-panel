<template>
  <div class="system-settings-container">
    <a-typography-title :heading="2">系统设置</a-typography-title>

    <a-tabs default-active-key="settings">
      <!-- 系统设置 -->
      <a-tab-pane key="settings" title="系统设置">
        <a-row :gutter="[20, 20]">
          <!-- 管理员密码修改 -->
          <a-col :span="8">
            <a-card title="修改管理员密码" hoverable>
              <a-form :model="passwordForm" layout="vertical" @submit="handlePasswordChange">
                <a-form-item label="当前密码" required>
                  <a-input-password v-model="passwordForm.old_password" placeholder="请输入当前密码" />
                </a-form-item>
                <a-form-item label="新密码" required>
                  <a-input-password v-model="passwordForm.new_password" placeholder="请输入新密码" />
                </a-form-item>
                <a-form-item label="确认新密码" required>
                  <a-input-password v-model="passwordForm.confirm_password" placeholder="请再次输入新密码" />
                </a-form-item>
                <a-button type="primary" html-type="submit" :loading="loading.password">
                  更新密码
                </a-button>
              </a-form>
            </a-card>
          </a-col>

          <!-- AI 设置 -->
          <a-col :span="8">
            <a-card title="AI 设置" hoverable>
              <a-form :model="aiForm" layout="vertical" @submit="handleAISave">
                <a-form-item label="模型" required>
                  <a-input v-model="aiForm.model" placeholder="请输入模型名称" />
                </a-form-item>
                <a-form-item label="API Key" required>
                  <a-input
                    v-model="aiForm.api_key"
                    :type="aiKeyVisible ? 'text' : 'password'"
                    placeholder="请输入 DeepSeek API Key"
                  >
                    <template #suffix>
                      <icon-eye v-if="!aiKeyVisible" @click="aiKeyVisible = true" style="cursor:pointer" />
                      <icon-eye-invisible v-else @click="aiKeyVisible = false" style="cursor:pointer" />
                    </template>
                  </a-input>
                </a-form-item>
                <a-button type="primary" html-type="submit" :loading="loading.ai">
                  保存
                </a-button>
              </a-form>
            </a-card>
          </a-col>

          <!-- 面板端口修改 -->
          <a-col :span="8">
            <a-card title="面板端口设置" hoverable>
              <a-form :model="portForm" layout="vertical" @submit="handlePortChange">
                <a-form-item label="面板监听端口" help="默认端口为 8000。修改后请确保防火墙已放行新端口。">
                  <a-input-number v-model="portForm.port" :min="1" :max="65535" />
                </a-form-item>
                <a-alert type="warning" style="margin-bottom: 15px;">
                  修改端口会导致面板服务重启，请使用新端口重新访问。
                </a-alert>
                <a-button type="outline" html-type="submit" :loading="loading.port">
                  保存并重启
                </a-button>
              </a-form>
            </a-card>
          </a-col>

          <!-- JWT 密钥管理 -->
          <a-col :span="8">
            <a-card title="安全密钥管理" hoverable>
              <div class="security-item">
                <div class="label">JWT 签名密钥 (SECRET_KEY)</div>
                <div class="desc">重置密钥将导致所有已登录的会话失效，需重新登录。</div>
              </div>
              <a-divider />
              <a-popconfirm content="确定要重新生成安全密钥吗？这将强制所有用户下线。" @ok="handleRegenerateSecret">
                <a-button type="outline" status="danger" :loading="loading.secret">
                  重新生成密钥
                </a-button>
              </a-popconfirm>
            </a-card>
          </a-col>

          <!-- 面板维护 -->
          <a-col :span="8">
            <a-card title="面板维护" hoverable>
              <div class="security-item">
                <div class="label">面板版本</div>
                <div class="desc">当前版本：{{ overview.system.panel_version || '1.0.0' }}</div>
              </div>
              <a-space style="margin-top: 8px;">
                <a-button :loading="updating" @click="handleUpdate">
                  <template #icon><icon-up-circle /></template>
                  检查并更新
                </a-button>
                <a-popconfirm content="确定要重启面板吗？重启期间服务会短暂不可用。" @ok="handleRestart">
                  <a-button :loading="restarting">
                    <template #icon><icon-refresh /></template>
                    重启面板
                  </a-button>
                </a-popconfirm>
              </a-space>
            </a-card>
          </a-col>
        </a-row>
      </a-tab-pane>

      <!-- 系统状态 -->
      <a-tab-pane key="status" title="系统状态">
        <a-row :gutter="20">
          <a-col :span="12">
            <a-card title="系统信息" hoverable>
              <a-descriptions :column="1" bordered size="medium">
                <a-descriptions-item label="主机名">{{ overview.system.hostname || '-' }}</a-descriptions-item>
                <a-descriptions-item label="操作系统">{{ overview.system.os || '-' }}</a-descriptions-item>
                <a-descriptions-item label="内核版本">{{ overview.system.kernel || '-' }}</a-descriptions-item>
                <a-descriptions-item label="Python 版本">{{ overview.system.python_version || '-' }}</a-descriptions-item>
                <a-descriptions-item label="面板版本">{{ overview.system.panel_version || '-' }}</a-descriptions-item>
                <a-descriptions-item label="启动时间">{{ overview.system.boot_time || '-' }}</a-descriptions-item>
                <a-descriptions-item label="运行时长">{{ formatUptime(overview.system.uptime_seconds) }}</a-descriptions-item>
              </a-descriptions>
            </a-card>
          </a-col>

          <a-col :span="12">
            <a-card title="服务 / 库状态" hoverable>
              <a-list :bordered="false">
                <a-list-item v-for="svc in overview.services" :key="svc.name">
                  <a-list-item-meta :title="svc.label">
                    <template #description>
                      <a-tag :color="svc.status === 'running' ? 'green' : (svc.status === 'stopped' ? 'red' : 'gray')">
                        {{ svc.status === 'running' ? '运行中' : (svc.status === 'stopped' ? '已停止' : '未安装') }}
                      </a-tag>
                    </template>
                  </a-list-item-meta>
                </a-list-item>
              </a-list>
            </a-card>
          </a-col>
        </a-row>
      </a-tab-pane>

      <!-- 面板运行日志 -->
      <a-tab-pane key="logs" title="面板运行日志">
        <a-card title="面板运行日志" hoverable>
          <template #extra>
            <a-space>
              <a-button size="small" @click="fetchLogs">
                <template #icon><icon-refresh /></template>
                刷新
              </a-button>
              <a-button size="small" type="outline" @click="downloadLogs">
                <template #icon><icon-download /></template>
                下载
              </a-button>
              <a-popconfirm content="确定要清空日志吗？" @ok="clearLogs">
                <a-button size="small" type="text" status="danger">
                  <template #icon><icon-delete /></template>
                  清空
                </a-button>
              </a-popconfirm>
            </a-space>
          </template>
          <div class="log-viewer-container">
            <pre class="log-content" ref="logContainer">{{ logs || '暂无日志内容...' }}</pre>
          </div>
        </a-card>
      </a-tab-pane>
    </a-tabs>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, nextTick } from 'vue'
import { Message } from '@arco-design/web-vue'
import {
  IconRefresh, IconDownload, IconDelete, IconEye, IconEyeInvisible,
  IconUpCircle
} from '@arco-design/web-vue/es/icon'
import request from '@/utils/request'

const loading = reactive({
  password: false,
  port: false,
  secret: false,
  logs: false,
  ai: false
})

const passwordForm = reactive({
  old_password: '',
  new_password: '',
  confirm_password: ''
})

const portForm = reactive({
  port: 8000
})

const aiForm = reactive({
  model: 'DeepSeek-V4-Pro',
  api_key: ''
})

const logs = ref('')
const logContainer = ref(null)
const aiKeyVisible = ref(false)
const updating = ref(false)
const restarting = ref(false)

const overview = reactive({
  system: {
    hostname: '',
    os: '',
    kernel: '',
    python_version: '',
    panel_version: '1.0.0',
    uptime_seconds: 0,
    boot_time: '',
    load_avg: []
  },
  services: []
})

const formatUptime = (sec) => {
  if (!sec) return '-'
  const d = Math.floor(sec / 86400)
  const h = Math.floor((sec % 86400) / 3600)
  const m = Math.floor((sec % 3600) / 60)
  const parts = []
  if (d) parts.push(`${d} 天`)
  if (h) parts.push(`${h} 小时`)
  if (m) parts.push(`${m} 分钟`)
  return parts.join(' ') || '0 分钟'
}

const fetchData = async () => {
  fetchLogs()
  fetchAIConfig()
  fetchOverview()
}

const fetchOverview = async () => {
  try {
    const ov = await request.get('/system/overview')
    if (ov.system) Object.assign(overview.system, ov.system)
    if (ov.services) overview.services = ov.services
  } catch (error) {
    console.error(error)
  }
}

const handlePasswordChange = async () => {
  if (passwordForm.new_password !== passwordForm.confirm_password) {
    Message.error('两次输入的新密码不一致')
    return
  }

  loading.password = true
  try {
    await request.post('/system/change-password', passwordForm)
    Message.success('密码修改成功，请重新登录')
    passwordForm.old_password = ''
    passwordForm.new_password = ''
    passwordForm.confirm_password = ''
  } catch (error) {
    Message.error(error.response?.data?.detail || '修改失败')
  } finally {
    loading.password = false
  }
}

const handlePortChange = async () => {
  loading.port = true
  try {
    await request.post('/system/change-port', { port: portForm.port })
    Message.success(`端口已修改为 ${portForm.port}，服务正在重启...`)
  } catch (error) {
    Message.error('端口修改失败')
  } finally {
    loading.port = false
  }
}

const handleRegenerateSecret = async () => {
  loading.secret = true
  try {
    await request.post('/system/regenerate-secret')
    Message.success('安全密钥已更新，请重新登录')
    setTimeout(() => {
      window.location.reload()
    }, 1500)
  } catch (error) {
    Message.error('重置密钥失败')
  } finally {
    loading.secret = false
  }
}

const handleUpdate = async () => {
  updating.value = true
  try {
    const res = await request.get('/system/update-check')
    if (res.available) {
      Message.info('发现新版本，开始更新...')
      const r = await request.post('/system/update')
      Message.success('更新已启动，面板将自动重启')
    } else {
      Message.success('当前已是最新版本')
    }
  } catch (error) {
    Message.error('检查更新失败')
  } finally {
    updating.value = false
  }
}

const handleRestart = async () => {
  restarting.value = true
  try {
    await request.post('/system/restart')
    Message.success('面板重启中...')
  } catch (error) {
    Message.error('重启失败')
  } finally {
    restarting.value = false
  }
}

const fetchAIConfig = async () => {
  try {
    const res = await request.get('/system/ai-config')
    aiForm.model = res.model || 'DeepSeek-V4-Pro'
    aiForm.api_key = res.has_key ? '••••••••' : ''
  } catch (error) {
    console.error(error)
  }
}

const handleAISave = async () => {
  loading.ai = true
  try {
    await request.post('/system/ai-config', { model: aiForm.model, api_key: aiForm.api_key })
    Message.success('AI 配置已保存')
    aiForm.api_key = '••••••••'
  } catch (error) {
    Message.error(error.response?.data?.detail || '保存失败')
  } finally {
    loading.ai = false
  }
}

const fetchLogs = async () => {
  loading.logs = true
  try {
    const res = await request.get('/system/logs')
    logs.value = res.logs || ''
    nextTick(() => {
      if (logContainer.value) {
        logContainer.value.scrollTop = logContainer.value.scrollHeight
      }
    })
  } catch (error) {
    logs.value = '无法加载日志内容'
  } finally {
    loading.logs = false
  }
}

const clearLogs = async () => {
  try {
    await request.delete('/system/logs')
    logs.value = ''
    Message.success('日志已清空')
  } catch (error) {
    Message.error('清空失败')
  }
}

const downloadLogs = () => {
  const blob = new Blob([logs.value], { type: 'text/plain' })
  const url = window.URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `sanguo-panel-${new Date().toISOString().split('T')[0]}.log`
  a.click()
  window.URL.revokeObjectURL(url)
}

onMounted(() => {
  fetchData()
})
</script>

<style scoped>
.system-settings-container {
  padding: 0;
}

.log-viewer-container {
  background-color: #1d2129;
  border-radius: 4px;
  padding: 12px;
  height: 500px;
  overflow: hidden;
}

.log-content {
  margin: 0;
  color: #ffffff;
  font-family: 'Courier New', Courier, monospace;
  font-size: 12px;
  line-height: 1.5;
  height: 100%;
  overflow-y: auto;
  white-space: pre-wrap;
  word-break: break-all;
}

.security-item {
  margin-bottom: 15px;
}

.security-item .label {
  font-weight: bold;
  margin-bottom: 4px;
}

.security-item .desc {
  font-size: 12px;
  color: #86909c;
}
</style>
