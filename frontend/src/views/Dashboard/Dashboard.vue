<template>
  <div class="dashboard-container">
    <a-typography-title :heading="2">仪表盘</a-typography-title>
    
    <!-- 实时指标卡片 -->
    <a-row :gutter="20" class="stat-cards">
      <a-col :span="8">
        <a-card title="CPU 使用率" hoverable class="stat-card">
          <a-statistic :value="metrics.cpu.percent" :precision="1">
            <template #suffix>
              <span class="small-percent">%</span>
            </template>
          </a-statistic>
          <div class="stat-footer">
            <a-tag color="blue">{{ metrics.cpu.count }} 核心</a-tag>
          </div>
        </a-card>
      </a-col>
      <a-col :span="8">
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
      <a-col :span="8">
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
  </div>
</template>

<script setup>
import { reactive, onMounted, onUnmounted, ref, nextTick, watch } from 'vue'
import request from '@/utils/request'
import * as echarts from 'echarts'

const metrics = reactive({
  cpu: { percent: 0, count: 0 },
  memory: { total: 0, used: 0, percent: 0 },
  disk: { total: 0, used: 0, percent: 0 }
})

const timeRange = ref('24h')
const chartRef = ref(null)
let chartInstance = null
let timer = null

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
  timer = setInterval(fetchMetrics, 3000)
  nextTick(() => {
    initChart()
    window.addEventListener('resize', handleResize)
  })
})

onUnmounted(() => {
  if (timer) clearInterval(timer)
  window.removeEventListener('resize', handleResize)
  chartInstance?.dispose()
})
</script>

<style scoped>
.dashboard-container {
  padding: 0;
}
.stat-cards :deep(.arco-card-body) {
  display: flex;
  flex-direction: column;
  height: 80px;
}
.stat-card {
  height: 100%;
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
