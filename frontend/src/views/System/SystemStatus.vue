<template>
  <div class="system-status-container">
    <a-row :gutter="20">
      <a-col :span="12">
        <a-card title="系统信息和服务状态">
          <a-descriptions :column="1" bordered size="medium">
            <a-descriptions-item label="主机名">{{ overview.system.hostname || '-' }}</a-descriptions-item>
            <a-descriptions-item label="操作系统">{{ overview.system.os || '-' }}</a-descriptions-item>
            <a-descriptions-item label="Python 版本">{{ overview.system.python_version || '-' }}</a-descriptions-item>
            <a-descriptions-item label="面板版本">{{ overview.system.panel_version || '-' }}</a-descriptions-item>
            <a-descriptions-item label="启动时间">{{ overview.system.boot_time || '-' }}</a-descriptions-item>
            <a-descriptions-item label="运行时长">{{ formatUptime(overview.system.uptime_seconds) }}</a-descriptions-item>
            <a-descriptions-item v-for="svc in overview.services" :key="svc.name" :label="svc.label">
              <a-tag :color="svc.status === 'running' ? 'green' : (svc.status === 'stopped' ? 'red' : 'gray')">
                {{ svc.status === 'running' ? '运行中' : (svc.status === 'stopped' ? '已停止' : '未安装') }}
              </a-tag>
            </a-descriptions-item>
          </a-descriptions>
        </a-card>
      </a-col>

      <a-col :span="12">
        <a-space direction="vertical" fill :size="20">
          <a-card title="运行状态">
            <template #extra>
              <a-tag :color="olsTag.color">{{ olsTag.text }}</a-tag>
            </template>
            <a-space direction="vertical" size="large" fill>
              <div class="status-item">
                <span>版本:</span>
                <a-tag color="arcoblue">{{ olsStatus.version }}</a-tag>
              </div>
              <div class="status-item">
                <span>PID:</span>
                <a-tag>{{ olsStatus.pid }}</a-tag>
              </div>
              <div class="status-item">
                <span>运行时间:</span>
                <span>{{ olsStatus.uptime || 'N/A' }}</span>
              </div>
              <a-divider />
              <a-alert v-if="isOlsMissing" type="warning" show-icon>
                OpenLiteSpeed 未安装（缺少 /usr/local/lsws/bin/lswsctrl），无法启动或重启。
                请先安装 OLS。
              </a-alert>
              <a-space v-else>
                <a-button type="primary" @click="handleAction('restart')" :loading="loading">
                  <template #icon><icon-refresh /></template>
                  重启
                </a-button>
                <a-button @click="handleAction('reload')" :loading="loading">
                  <template #icon><icon-sync /></template>
                  重载配置
                </a-button>
                <a-button type="outline" status="danger" @click="handleAction('stop')" :loading="loading" v-if="olsStatus.status === 'running'">
                  停止
                </a-button>
                <a-button type="outline" status="success" @click="handleAction('start')" :loading="loading" v-else>
                  启动
                </a-button>
              </a-space>
            </a-space>
          </a-card>

          <a-card title="性能开关">
            <a-space direction="vertical" fill>
              <div class="config-item">
                <span>HTTP/2 协议</span>
                <a-switch v-model="features.http2" :disabled="isOlsMissing" @change="toggleFeature('http2', $event)" />
              </div>
              <div class="config-item">
                <span>HTTP/3 (QUIC) 协议</span>
                <a-switch v-model="features.http3" :disabled="isOlsMissing" @change="toggleFeature('http3', $event)" />
              </div>
              <div class="config-item">
                <span>Brotli 压缩</span>
                <a-switch v-model="features.brotli" :disabled="isOlsMissing" @change="toggleFeature('brotli', $event)" />
              </div>
              <div class="config-item">
                <span>LSCache 全局开关</span>
                <a-switch v-model="features.lscache" :disabled="isOlsMissing" @change="toggleFeature('lscache', $event)" />
              </div>
            </a-space>
          </a-card>

          <a-card title="OLS 管理后台" v-if="!isOlsMissing">
            <template #extra>
              <a-link :href="olsAdminUrl" target="_blank" :hoverable="false">
                <icon-export /> 打开管理后台
              </a-link>
            </template>
            <a-space direction="vertical" size="medium">
              <div class="status-item">
                <span>管理员地址:</span>
                <a-link :href="olsAdminUrl" target="_blank">
                  {{ olsAdminUrl }} <icon-export />
                </a-link>
              </div>
              <div class="status-item">
                <span>用户名:</span>
                <a-tag color="arcoblue">{{ olsAdmin.user }}</a-tag>
              </div>
              <div class="status-item">
                <span>密&emsp;&emsp;码:</span>
                <a-tag>{{ olsAdmin.password || '未设置' }}</a-tag>
              </div>
            </a-space>
          </a-card>
        </a-space>
      </a-col>
    </a-row>
  </div>
</template>

<script setup>
import { reactive, ref, computed, onMounted } from 'vue'
import request from '@/utils/request'
import { Message } from '@arco-design/web-vue'

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

const olsStatus = ref({
  status: 'unknown',
  version: '',
  pid: '',
  uptime: '',
  admin: { user: 'admin', password: '', port: 7080 }
})
const loading = ref(false)
const isOlsMissing = computed(() => olsStatus.value.status === 'not_installed')
const olsTag = computed(() => {
  const s = olsStatus.value.status
  if (s === 'running') return { color: 'green', text: 'RUNNING' }
  if (s === 'not_installed') return { color: 'gray', text: '未安装' }
  return { color: 'red', text: (s || 'unknown').toUpperCase() }
})
const olsAdmin = computed(() => olsStatus.value.admin || { user: 'admin', password: '', port: 7080 })
const olsAdminUrl = computed(() => `http://${window.location.hostname}:${olsAdmin.value.port}`)
const features = reactive({
  http2: true,
  http3: true,
  brotli: true,
  lscache: true
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

const fetchOverview = async () => {
  try {
    const ov = await request.get('/system/overview')
    if (ov.system) Object.assign(overview.system, ov.system)
    if (ov.services) overview.services = ov.services
  } catch (error) {
    console.error(error)
  }
}

const fetchStatus = async () => {
  try {
    const res = await request.get('/litespeed/status')
    olsStatus.value = res
  } catch (error) {
    console.error(error)
  }
}

const fetchFeatures = async () => {
  try {
    const res = await request.get('/litespeed/config/features')
    Object.assign(features, res)
  } catch (error) {
    console.error(error)
  }
}

const handleAction = async (action) => {
  loading.value = true
  try {
    await request.post(`/litespeed/action/${action}`)
    Message.success('操作成功')
    await fetchStatus()
  } catch (error) {
    console.error(error)
  } finally {
    loading.value = false
  }
}

const toggleFeature = async (feature, enabled) => {
  try {
    await request.post('/litespeed/config/features/toggle', { feature, enabled })
    Message.success(`${feature} 已${enabled ? '开启' : '关闭'}`)
  } catch (error) {
    console.error(error)
  }
}

onMounted(() => {
  fetchOverview()
  fetchStatus()
  fetchFeatures()
})
</script>

<style scoped>
.system-status-container {
  padding: 0;
}
.status-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}
.config-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 0;
  border-bottom: 1px solid var(--color-fill-2);
}
.config-item:last-child {
  border-bottom: none;
}
</style>
