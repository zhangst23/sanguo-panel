<template>
  <div class="monitor-container">
    <a-typography-title :heading="2">Resource Monitoring</a-typography-title>
    
    <a-row :gutter="20">
      <!-- Real-time Charts -->
      <a-col :span="12">
        <a-card title="CPU Usage Trend">
          <div ref="cpuChart" style="height: 300px"></div>
        </a-card>
      </a-col>
      <a-col :span="12">
        <a-card title="Memory Usage Trend">
          <div ref="memChart" style="height: 300px"></div>
        </a-card>
      </a-col>

      <!-- Network Traffic -->
      <a-col :span="24" style="margin-top: 20px">
        <a-card title="Network Traffic (Last 24 Hours)">
          <div ref="netChart" style="height: 350px"></div>
        </a-card>
      </a-col>
    </a-row>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import * as echarts from 'echarts'

const cpuChart = ref(null)
const memChart = ref(null)
const netChart = ref(null)

let cpuInstance, memInstance, netInstance
let timer

const initCharts = () => {
  // CPU Chart
  cpuInstance = echarts.init(cpuChart.value)
  cpuInstance.setOption({
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'category', data: [] },
    yAxis: { type: 'value', max: 100 },
    series: [{ data: [], type: 'line', smooth: true, areaStyle: {} }]
  })

  // Memory Chart
  memInstance = echarts.init(memChart.value)
  memInstance.setOption({
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'category', data: [] },
    yAxis: { type: 'value', max: 100 },
    series: [{ data: [], type: 'line', smooth: true, areaStyle: { color: '#82ca9d' }, itemStyle: { color: '#82ca9d' } }]
  })

  // Network Chart
  netInstance = echarts.init(netChart.value)
  const hours = Array.from({length: 24}, (_, i) => `${i}:00`)
  netInstance.setOption({
    tooltip: { trigger: 'axis' },
    legend: { data: ['Inbound', 'Outbound'] },
    xAxis: { type: 'category', data: hours },
    yAxis: { type: 'value', name: 'Mbps' },
    series: [
      { name: 'Inbound', type: 'line', data: Array.from({length: 24}, () => Math.random() * 50) },
      { name: 'Outbound', type: 'line', data: Array.from({length: 24}, () => Math.random() * 30) }
    ]
  })
}

const updateData = () => {
  const now = new Date().toLocaleTimeString()
  
  // Mock CPU update
  const cpuOption = cpuInstance.getOption()
  cpuOption.xAxis[0].data.push(now)
  cpuOption.series[0].data.push(Math.floor(Math.random() * 40) + 10)
  if (cpuOption.xAxis[0].data.length > 10) {
    cpuOption.xAxis[0].data.shift()
    cpuOption.series[0].data.shift()
  }
  cpuInstance.setOption(cpuOption)

  // Mock Memory update
  const memOption = memInstance.getOption()
  memOption.xAxis[0].data.push(now)
  memOption.series[0].data.push(Math.floor(Math.random() * 20) + 50)
  if (memOption.xAxis[0].data.length > 10) {
    memOption.xAxis[0].data.shift()
    memOption.series[0].data.shift()
  }
  memInstance.setOption(memOption)
}

onMounted(() => {
  initCharts()
  timer = setInterval(updateData, 2000)
  window.addEventListener('resize', () => {
    cpuInstance?.resize()
    memInstance?.resize()
    netInstance?.resize()
  })
})

onUnmounted(() => {
  clearInterval(timer)
})
</script>

<style scoped>
.monitor-container {
  padding: 0;
}
</style>
