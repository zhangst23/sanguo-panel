<template>
  <div class="monitor-container">
    <a-typography-title :heading="2">监控中心</a-typography-title>

    <!-- 顶部核心指标 -->
    <a-row :gutter="20" class="core-metrics">
      <a-col :span="6">
        <a-card hoverable>
          <a-statistic title="Web QPS" :value="webStats.requests.qps" :precision="1" show-group-separator>
            <template #suffix>req/s</template>
          </a-statistic>
        </a-card>
      </a-col>
      <a-col :span="6">
        <a-card hoverable>
          <a-statistic title="LSCache 命中率" :value="webStats.cache_hit_rate" :precision="1">
            <template #suffix>%</template>
          </a-statistic>
        </a-card>
      </a-col>
      <a-col :span="6">
        <a-card hoverable>
          <a-statistic title="Redis 命中率" :value="redisStats.hit_rate" :precision="1">
            <template #suffix>%</template>
          </a-statistic>
        </a-card>
      </a-col>
      <a-col :span="6">
        <a-card hoverable>
          <a-statistic title="平均响应时间 (TTFB)" :value="webStats.ttfb" :precision="0">
            <template #suffix>ms</template>
          </a-statistic>
        </a-card>
      </a-col>
    </a-row>

    <a-tabs default-active-key="system" style="margin-top: 20px;">
      <!-- 系统资源监控 -->
      <a-tab-pane key="system" title="系统资源">
        <a-row :gutter="20">
          <a-col :span="12">
            <a-card title="CPU 使用率 (%)">
              <div ref="cpuChartRef" style="height: 300px"></div>
            </a-card>
          </a-col>
          <a-col :span="12">
            <a-card title="内存使用率 (%)">
              <div ref="memChartRef" style="height: 300px"></div>
            </a-card>
          </a-col>
          <a-col :span="24" style="margin-top: 20px">
            <a-card title="网络流量 (Bytes/s)">
              <div ref="netChartRef" style="height: 300px"></div>
            </a-card>
          </a-col>
        </a-row>
      </a-tab-pane>

      <!-- Web 服务监控 -->
      <a-tab-pane key="web" title="Web 服务">
        <a-row :gutter="20">
          <a-col :span="16">
            <a-card title="Web 请求量趋势 (QPS)">
              <div ref="webRequestChartRef" style="height: 350px"></div>
            </a-card>
          </a-col>
          <a-col :span="8">
            <a-card title="响应状态码分布">
              <div ref="statusPieChartRef" style="height: 350px"></div>
            </a-card>
          </a-col>
        </a-row>
      </a-tab-pane>

      <!-- 数据库监控 -->
      <a-tab-pane key="database" title="数据库">
        <a-row :gutter="20">
          <a-col :span="12">
            <a-card title="MariaDB 查询耗时 (s)">
              <div ref="dbQueryChartRef" style="height: 300px"></div>
            </a-card>
          </a-col>
          <a-col :span="12">
            <a-card title="慢查询数量趋势">
              <div ref="slowQueryChartRef" style="height: 300px"></div>
            </a-card>
          </a-col>
          <a-col :span="24" style="margin-top: 20px" v-if="dbStats.alert">
            <a-alert type="warning" title="数据库性能预警">
              当前共享数据库表总数已接近阈值，建议新增共享实例。
            </a-alert>
          </a-col>
        </a-row>
      </a-tab-pane>

      <!-- 站点优化监控 -->
      <a-tab-pane key="optimization" title="优化监控">
        <a-row :gutter="20">
          <a-col :span="24">
            <a-card title="PageSpeed 评分记录">
              <a-table :data="pageSpeedData" :pagination="false">
                <template #columns>
                  <a-table-column title="站点域名" data-index="domain" />
                  <a-table-column title="移动端评分" data-index="mobile">
                    <template #cell="{ record }">
                      <a-progress :percent="record.mobile / 100" :status="record.mobile > 80 ? 'success' : 'warning'" />
                    </template>
                  </a-table-column>
                  <a-table-column title="桌面端评分" data-index="desktop">
                    <template #cell="{ record }">
                      <a-progress :percent="record.desktop / 100" :status="record.desktop > 90 ? 'success' : 'warning'" />
                    </template>
                  </a-table-column>
                  <a-table-column title="最后检测时间" data-index="time" />
                  <a-table-column title="操作">
                    <template #cell>
                      <a-button type="text" size="small">立即检测</a-button>
                    </template>
                  </a-table-column>
                </template>
              </a-table>
            </a-card>
          </a-col>
        </a-row>
      </a-tab-pane>
    </a-tabs>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted, nextTick } from 'vue'
import * as echarts from 'echarts'
import request from '@/utils/request'

// 图表引用
const cpuChartRef = ref(null)
const memChartRef = ref(null)
const netChartRef = ref(null)
const webRequestChartRef = ref(null)
const statusPieChartRef = ref(null)
const dbQueryChartRef = ref(null)
const slowQueryChartRef = ref(null)

// 图表实例
let instances = {}
let timer = null

// 数据状态
const webStats = reactive({
  requests: { total: 0, qps: 0, status_codes: [] },
  cache_hit_rate: 0,
  ttfb: 0
})
const redisStats = reactive({ hit_rate: 0 })
const dbStats = reactive({ alert: false })
const pageSpeedData = ref([
  { domain: 'example.com', mobile: 85, desktop: 95, time: '2024-02-13 10:00' },
  { domain: 'test.com', mobile: 65, desktop: 88, time: '2024-02-13 11:30' }
])

const initChart = (ref, option) => {
  if (!ref) return null
  const instance = echarts.init(ref)
  instance.setOption(option)
  return instance
}

const getLineOption = (title, color) => ({
  tooltip: { trigger: 'axis' },
  grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
  xAxis: { type: 'category', boundaryGap: false, data: [] },
  yAxis: { type: 'value' },
  series: [{
    name: title,
    type: 'line',
    smooth: true,
    showSymbol: false,
    areaStyle: { opacity: 0.1 },
    itemStyle: { color: color },
    data: []
  }]
})

const initAllCharts = () => {
  instances.cpu = initChart(cpuChartRef.value, getLineOption('CPU', '#165DFF'))
  instances.mem = initChart(memChartRef.value, getLineOption('Memory', '#00B42A'))
  instances.net = initChart(netChartRef.value, {
    ...getLineOption('Traffic', '#FF7D00'),
    series: [
      { name: 'Sent', type: 'line', smooth: true, data: [] },
      { name: 'Received', type: 'line', smooth: true, data: [] }
    ]
  })
  instances.web = initChart(webRequestChartRef.value, getLineOption('QPS', '#722ED1'))
  instances.pie = initChart(statusPieChartRef.value, {
    tooltip: { trigger: 'item' },
    series: [{
      type: 'pie',
      radius: ['40%', '70%'],
      avoidLabelOverlap: false,
      itemStyle: { borderRadius: 10, borderColor: '#fff', borderWidth: 2 },
      label: { show: false },
      data: []
    }]
  })
  instances.db = initChart(dbQueryChartRef.value, getLineOption('Query Time', '#F53F3F'))
  instances.slow = initChart(slowQueryChartRef.value, getLineOption('Slow Queries', '#F77234'))
}

const fetchRealtime = async () => {
  try {
    const res = await request.get('/monitor/realtime')
    const time = new Date(res.timestamp).toLocaleTimeString()
    
    // 更新 CPU/Mem
    const updateLine = (inst, val) => {
      const opt = inst.getOption()
      opt.xAxis[0].data.push(time)
      opt.series[0].data.push(val)
      if (opt.xAxis[0].data.length > 20) {
        opt.xAxis[0].data.shift()
        opt.series[0].data.shift()
      }
      inst.setOption(opt)
    }
    
    if (instances.cpu) updateLine(instances.cpu, res.cpu)
    if (instances.mem) updateLine(instances.mem, res.memory)
  } catch (e) {}
}

const fetchStaticStats = async () => {
  try {
    const [web, db, redis] = await Promise.all([
      request.get('/monitor/web-stats'),
      request.get('/monitor/db-stats'),
      request.get('/monitor/redis-stats')
    ])
    Object.assign(webStats, web)
    Object.assign(dbStats, db)
    Object.assign(redisStats, redis)
    
    // 更新饼图
    if (instances.pie) {
      instances.pie.setOption({
        series: [{ data: web.requests.status_codes }]
      })
    }
  } catch (e) {}
}

onMounted(() => {
  nextTick(() => {
    initAllCharts()
    fetchStaticStats()
    timer = setInterval(() => {
      fetchRealtime()
    }, 2000)
    
    window.addEventListener('resize', () => {
      Object.values(instances).forEach(i => i?.resize())
    })
  })
})

onUnmounted(() => {
  if (timer) clearInterval(timer)
  Object.values(instances).forEach(i => i?.dispose())
})
</script>

<style scoped lang="scss">
.monitor-container {
  padding: 0 0 20px 0;
  .core-metrics {
    margin-bottom: 20px;
  }
}
</style>
