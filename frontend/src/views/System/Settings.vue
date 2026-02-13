<template>
  <div class="system-settings-container">
    <a-typography-title :heading="2">系统设置</a-typography-title>

    <a-row :gutter="20">
      <a-col :span="12">
        <!-- 管理员密码修改 -->
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

        <!-- 面板端口修改 -->
        <a-card title="面板端口设置" style="margin-top: 20px;" hoverable>
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

        <!-- JWT 密钥管理 -->
        <a-card title="安全密钥管理" style="margin-top: 20px;" hoverable>
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

      <a-col :span="12">
        <!-- 日志查看 -->
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
      </a-col>
    </a-row>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, nextTick } from 'vue'
import { Message } from '@arco-design/web-vue'
import { IconRefresh, IconDownload, IconDelete } from '@arco-design/web-vue/es/icon'
import request from '@/utils/request'

const loading = reactive({
  password: false,
  port: false,
  secret: false,
  logs: false
})

const passwordForm = reactive({
  old_password: '',
  new_password: '',
  confirm_password: ''
})

const portForm = reactive({
  port: 8000
})

const logs = ref('')
const logContainer = ref(null)

const fetchData = async () => {
  try {
    // 获取当前端口（模拟或从配置接口获取）
    // const res = await request.get('/system/config')
    // portForm.port = res.port || 8000
    fetchLogs()
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
    // 实际项目中可能需要跳转到登录页
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
