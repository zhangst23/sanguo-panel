<template>
  <div class="system-status-container">
    <a-row :gutter="20">
      <a-col :span="12">
        <a-space direction="vertical" fill :size="20">
          <a-card title="系统信息和服务状态" :loading="refreshing && !lastUpdated">
            <template #extra>
              <a-space size="8">
                <span v-if="lastUpdated" class="last-updated">更新于 {{ lastUpdated }}</span>
                <a-button size="small" :loading="refreshing" @click="handleRefresh">
                  <template #icon><icon-refresh /></template>
                  刷新
                </a-button>
              </a-space>
            </template>
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
        </a-space>
      </a-col>
    </a-row>
  </div>
</template>

<script setup>
import { reactive, ref, computed, onMounted } from 'vue'
import request from '@/utils/request'
import { Message } from '@arco-design/web-vue'
import { IconRefresh } from '@arco-design/web-vue/es/icon'

const CACHE_KEY = 'panel:system-status-v1'

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
const refreshing = ref(false)
const lastUpdated = ref('')
const cacheAvailable = ref(false)

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

// ─── 本地缓存：进入页面先显示上次检测结果，不必等待慢查询 ───
const loadCachedState = () => {
  try {
    const raw = localStorage.getItem(CACHE_KEY)
    if (!raw) return false
    const cached = JSON.parse(raw)
    if (cached.overview?.system) Object.assign(overview.system, cached.overview.system)
    if (cached.overview?.services) overview.services = cached.overview.services
    if (cached.olsStatus) olsStatus.value = { ...olsStatus.value, ...cached.olsStatus }
    if (cached.features) Object.assign(features, cached.features)
    if (cached.savedAt) {
      lastUpdated.value = new Date(cached.savedAt).toLocaleString()
      cacheAvailable.value = true
    }
    return true
  } catch {
    return false
  }
}

const saveCachedState = () => {
  try {
    const savedAt = Date.now()
    localStorage.setItem(CACHE_KEY, JSON.stringify({
      overview: { system: { ...overview.system }, services: [...overview.services] },
      olsStatus: olsStatus.value,
      features: { ...features },
      savedAt
    }))
    lastUpdated.value = new Date(savedAt).toLocaleString()
    cacheAvailable.value = true
  } catch {
    // localStorage 不可用时忽略，不影响页面展示
  }
}

// 这三个接口支持本地缓存，统一静默处理错误，避免多个弹窗
const fetchOverview = async () => {
  const ov = await request.get('/system/overview', { silent: true, timeout: 30000 })
  if (ov.system) Object.assign(overview.system, ov.system)
  if (ov.services) overview.services = ov.services
}

const fetchStatus = async () => {
  olsStatus.value = await request.get('/litespeed/status', { silent: true, timeout: 30000 })
}

const fetchFeatures = async () => {
  const res = await request.get('/litespeed/config/features', { silent: true, timeout: 30000 })
  Object.assign(features, res)
}

const fetchLatest = async () => {
  const results = await Promise.allSettled([fetchOverview(), fetchStatus(), fetchFeatures()])
  const failed = results.filter((r) => r.status === 'rejected')
  if (failed.length) {
    failed.forEach((r) => console.error(r.reason))
    // 部分接口失败时保留已成功更新的数据，缓存仍保留上次结果
    Message.warning(
      failed.length === results.length
        ? '获取状态失败，请稍后重试'
        : '部分状态刷新失败，其余数据已更新'
    )
    return false
  }
  saveCachedState()
  return true
}

const handleRefresh = async () => {
  if (refreshing.value) return
  refreshing.value = true
  try {
    await fetchLatest()
  } finally {
    refreshing.value = false
  }
}

const handleAction = async (action) => {
  loading.value = true
  try {
    await request.post(`/litespeed/action/${action}`)
    Message.success('操作成功')
    await fetchStatus()
    saveCachedState()
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
  // 优先显示上次检测结果；首次访问没有缓存时才静默拉取一次
  if (!loadCachedState()) handleRefresh()
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
.last-updated {
  font-size: 12px;
  color: var(--color-text-3);
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
