<template>
  <div class="dashboard-container">
    <!-- 标题栏：左侧标题 + 右侧操作按钮 -->
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
      <a-typography-title :heading="2" :style="{ margin: 0 }">仪表盘</a-typography-title>
      <div style="display: flex; align-items: center; gap: 12px;">
        <a-button
          v-if="updateInfo.available"
          type="primary"
          :disabled="operating"
          @click="showUpdateModal"
        >
          <template #icon><icon-download /></template>
          更新面板
        </a-button>
        <a-button
          :disabled="operating"
          @click="showRestartModal"
        >
          <template #icon><icon-refresh /></template>
          重启面板
        </a-button>
      </div>
    </div>

    <!-- 重启确认弹窗 -->
    <a-modal
      v-model:visible="restartModalVisible"
      title="重启面板"
      @ok="handleRestartConfirm"
      :ok-loading="restartLoading"
      ok-text="确认重启"
    >
      <p>重启后页面将短暂不可用，面板恢复后刷新页面即可。</p>
      <p v-if="restartStatus" style="margin-top:8px;color:var(--arco-color-text-3);font-size:13px">
        状态：{{ restartStatus }}
      </p>
    </a-modal>

    <!-- 更新确认弹窗 -->
    <a-modal
      v-model:visible="updateModalVisible"
      title="更新面板"
      @ok="handleUpdateConfirm"
      :ok-loading="updateLoading"
      ok-text="更新并重启"
    >
      <p>将执行 <code>git pull --ff-only</code> 拉取最新代码并重启面板，预计需要 30 秒。</p>
      <a-descriptions
        v-if="updateInfo.available"
        :column="1"
        size="small"
        style="margin-top:12px"
        bordered
      >
        <a-descriptions-item label="当前版本">{{ updateInfo.current_commit }}</a-descriptions-item>
        <a-descriptions-item label="最新版本">{{ updateInfo.latest_commit }}</a-descriptions-item>
        <a-descriptions-item v-if="updateInfo.commit_message" label="更新说明">
          {{ updateInfo.commit_message }}
        </a-descriptions-item>
      </a-descriptions>
      <p v-if="updateStatus" style="margin-top:8px;color:var(--arco-color-text-3);font-size:13px">
        状态：{{ updateStatus }}
      </p>
    </a-modal>

    <!-- 全屏 loading 遮罩 -->
    <a-spin :loading="operating" tip="操作进行中，请稍候…" style="width:100%">
    <!-- 实时指标卡片 -->
    <a-row :gutter="20" class="stat-cards">
      <a-col :span="4.8" style="width: 20%">
        <a-card title="CPU 使用率" hoverable class="stat-card">
          <a-statistic :value="metrics.cpu.percent" :precision="1">
            <template #suffix>
              <span class="small-percent">%</span>
            </template>
          </a-statistic>
          <div class="stat-footer">
            <a-tag class="stat-footer">{{ metrics.cpu.count }} 核心</a-tag>
          </div>
        </a-card>
      </a-col>
      <a-col :span="4.8" style="width: 20%">
        <a-card title="内存使用率" hoverable class="stat-card">
          <a-statistic :value="metrics.memory.percent" :precision="1">
            <template #suffix>
              <span class="small-percent">%</span>
            </template>
          </a-statistic>
          <div class="stat-footer">
            已用: {{ (metrics.memory.used / 1024 / 1024 / 1024).toFixed(2) }} GB / 
            总量: {{ (metrics.memory.total / 1024 / 1024 / 1024).toFixed(2) }} GB
          </div>
        </a-card>
      </a-col>
      <a-col :span="4.8" style="width: 20%">
        <a-card title="磁盘使用率" hoverable class="stat-card">
          <a-statistic :value="metrics.disk.percent" :precision="1">
            <template #suffix>
              <span class="small-percent">%</span>
            </template>
          </a-statistic>
          <div class="stat-footer">
            已用: {{ (metrics.disk.used / 1024 / 1024 / 1024).toFixed(2) }} GB / 
            总量: {{ (metrics.disk.total / 1024 / 1024 / 1024).toFixed(2) }} GB
          </div>
        </a-card>
      </a-col>
      <a-col :span="4.8" style="width: 20%">
        <a-card title="网站数量" hoverable class="stat-card clickable" @click="router.push({ name: 'Website' })">
          <a-statistic :value="metrics.site_count" />
          <div class="stat-footer">
            <a-link>管理站点 <icon-arrow-right /></a-link>
          </div>
        </a-card>
      </a-col>
      <a-col :span="4.8" style="width: 20%">
        <a-card title="备份数量" hoverable class="stat-card clickable" @click="router.push({ name: 'Backup' })">
          <a-statistic :value="metrics.backup_count" />
          <div class="stat-footer">
            <a-link>管理备份 <icon-arrow-right /></a-link>
          </div>
        </a-card>
      </a-col>
    </a-row>

    <!-- 历史趋势图表 -->
    <a-row :gutter="20" style="margin-top: 20px;">
      <a-col :span="24">
        <a-card title="系统资源历史趋势" hoverable>
          <template #extra>
            <a-radio-group v-model="timeRange" type="button" size="small" @change="handleTimeRangeChange">
              <a-radio value="24h">24h</a-radio>
              <a-radio value="7d">7天</a-radio>
              <a-radio value="30d">30天</a-radio>
            </a-radio-group>
          </template>
          <div ref="chartRef" style="height: 350px; width: 100%;"></div>
        </a-card>
      </a-col>
    </a-row>
    </a-spin>
  </div>
</template>

<script setup>
import { reactive, onMounted, onUnmounted, ref, nextTick, watch } from 'vue'
import { useRouter } from 'vue-router'
import { Message } from '@arco-design/web-vue'
import request from '@/utils/request'
import * as echarts from 'echarts'
import {
  IconArrowRight,
  IconRefresh,
  IconDownload,
} from '@arco-design/web-vue/es/icon'

const router = useRouter()
const metrics = reactive({
  cpu: { percent: 0, count: 0 },
  memory: { total: 0, used: 0, percent: 0 },
  disk: { total: 0, used: 0, percent: 0 },
  site_count: 0,
  backup_count: 0
})

const timeRange = ref('24h')
const chartRef = ref(null)
let chartInstance = null
let timer = null

// ─── 更新 & 重启相关 ───
const updateInfo = ref({
  available: false,
  current_commit: '',
  latest_commit: '',
  commit_message: '',
})
const restartModalVisible = ref(false)
const updateModalVisible = ref(false)
const restartLoading = ref(false)
const updateLoading = ref(false)
const operating = ref(false)
const restartStatus = ref('')
const updateStatus = ref('')
let pollTimer = null
const POLL_INTERVAL = 2000
const POLL_TIMEOUT = 60000

const showRestartModal = () => { restartModalVisible.value = true }
const showUpdateModal = () => { updateModalVisible.value = true }

const fetchUpdateStatus = async () => {
  try {
    const res = await request.get('/system/update-check')
    updateInfo.value = res
  } catch {
    // 静默失败，不显示按钮
  }
}

const startPolling = (taskUuid, statusRef, onDone) => {
  const start = Date.now()
  statusRef.value = 'pending'
  pollTimer = setInterval(async () => {
    try {
      const task = await request.get(`/system/task/${taskUuid}`)
      statusRef.value = task.status
      if (task.status === 'running') {
        statusRef.value = task.message || 'running'
      }
      if (['completed', 'success'].includes(task.status)) {
        clearPolling()
        operating.value = false
        onDone?.(true, task.message || '操作完成')
      } else if (task.status === 'failed') {
        clearPolling()
        operating.value = false
        onDone?.(false, task.error || task.message || '操作失败')
      } else if (Date.now() - start > POLL_TIMEOUT) {
        clearPolling()
        operating.value = false
        onDone?.(false, '操作超时，请手动刷新页面查看状态')
      }
    } catch {
      // 后端可能已重启导致请求失败：继续轮询到超时
      statusRef.value = '面板正在重启中…'
      if (Date.now() - start > POLL_TIMEOUT) {
        clearPolling()
        operating.value = false
        onDone?.(false, '未收到面板响应，请手动刷新页面')
      }
    }
  }, POLL_INTERVAL)
}

const clearPolling = () => {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

const handleRestartConfirm = async () => {
  restartLoading.value = true
  operating.value = true
  restartModalVisible.value = false
  try {
    const res = await request.post('/system/restart')
    restartLoading.value = false
    startPolling(res.task_uuid, restartStatus, (ok, msg) => {
      if (ok) {
        Message.success(msg)
      } else {
        Message.warning(msg)
      }
    })
  } catch {
    restartLoading.value = false
    operating.value = false
  }
}

const handleUpdateConfirm = async () => {
  updateLoading.value = true
  operating.value = true
  updateModalVisible.value = false
  try {
    const res = await request.post('/system/update')
    updateLoading.value = false
    startPolling(res.task_uuid, updateStatus, (ok, msg) => {
      if (ok) {
        Message.success(msg)
      } else {
        Message.warning(msg)
      }
    })
  } catch {
    updateLoading.value = false
    operating.value = false
  }
}

const handleTimeRangeChange = () => {
  fetchHistoryData()
}

const fetchMetrics = async () => {
  try {
    const res = await request.get('/system/metrics')
    Object.assign(metrics, res)
  } catch (error) {
    console.error(error)
  }
}

const fetchHistoryData = async () => {
  // 模拟历史数据，实际开发中需对接后端接口
  const now = new Date()
  const dataPoints = timeRange.value === '24h' ? 24 : (timeRange.value === '7d' ? 7 : 30)
  const categories = []
  const cpuData = []
  const memData = []
  const diskData = []

  for (let i = dataPoints; i >= 0; i--) {
    const d = new Date(now)
    if (timeRange.value === '24h') {
      d.setHours(now.getHours() - i)
      categories.push(`${d.getHours()}:00`)
    } else {
      d.setDate(now.getDate() - i)
      categories.push(`${d.getMonth() + 1}-${d.getDate()}`)
    }
    cpuData.push(Math.floor(Math.random() * 50) + 10)
    memData.push(Math.floor(Math.random() * 40) + 30)
    diskData.push(45)
  }

  updateChart(categories, cpuData, memData, diskData)
}

const initChart = () => {
  if (chartRef.value) {
    chartInstance = echarts.init(chartRef.value, 'dark')
    fetchHistoryData()
  }
}

const updateChart = (categories, cpu, mem, disk) => {
  if (!chartInstance) return

  const option = {
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'cross' }
    },
    legend: {
      data: ['CPU', '内存', '磁盘'],
      bottom: 0
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '10%',
      top: '5%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: categories,
      axisLine: { lineStyle: { color: '#666' } }
    },
    yAxis: {
      type: 'value',
      axisLabel: { formatter: '{value} %' },
      max: 100,
      axisLine: { lineStyle: { color: '#666' } },
      splitLine: { lineStyle: { color: '#333' } }
    },
    series: [
      {
        name: 'CPU',
        type: 'line',
        smooth: true,
        data: cpu,
        color: '#165DFF',
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(22, 93, 255, 0.3)' },
            { offset: 1, color: 'rgba(22, 93, 255, 0)' }
          ])
        }
      },
      {
        name: '内存',
        type: 'line',
        smooth: true,
        data: mem,
        color: '#00B42A',
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(0, 180, 42, 0.3)' },
            { offset: 1, color: 'rgba(0, 180, 42, 0)' }
          ])
        }
      },
      {
        name: '磁盘',
        type: 'line',
        smooth: true,
        data: disk,
        color: '#FF7D00',
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(255, 125, 0, 0.3)' },
            { offset: 1, color: 'rgba(255, 125, 0, 0)' }
          ])
        }
      }
    ]
  }
  chartInstance.setOption(option)
}

const handleResize = () => {
  chartInstance?.resize()
}

onMounted(() => {
  fetchMetrics()
  fetchUpdateStatus()
  timer = setInterval(fetchMetrics, 3000)
  nextTick(() => {
    initChart()
    window.addEventListener('resize', handleResize)
  })
})

onUnmounted(() => {
  if (timer) clearInterval(timer)
  clearPolling()
  window.removeEventListener('resize', handleResize)
  chartInstance?.dispose()
})
</script>

<style scoped>
.dashboard-container {
  padding: 0;
}
.dashboard-container :deep(.arco-typography) {
  text-align: left !important;
}
.stat-cards :deep(.arco-card-body) {
  display: flex;
  flex-direction: column;
  height: 80px;
}
.stat-card {
  height: 100%;
}
.stat-card.clickable {
  cursor: pointer;
  transition: all 0.3s;
}
.stat-card.clickable:hover {
  transform: translateY(-4px);
  box-shadow: 0 4px 10px rgba(0, 0, 0, 0.1);
}
.stat-footer {
  margin-top: auto;
  font-size: 12px;
  color: var(--arco-color-text-3);
  height: 24px;
  display: flex;
  align-items: center;
}
.small-percent {
  font-size: 14px;
  margin-left: 2px;
  color: var(--arco-color-text-3);
}
</style>
