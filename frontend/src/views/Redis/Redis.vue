<template>
  <div class="redis-container">
    <a-typography-title :heading="2">Redis & Cache Management</a-typography-title>
    
    <a-row :gutter="20">
      <!-- Redis Service Metrics -->
      <a-col :span="16">
        <a-card title="Redis Service Metrics" hoverable>
          <template #extra>
            <a-tag :color="metrics.status === 'running' ? 'green' : 'red'">
              {{ metrics.status.toUpperCase() }}
            </a-tag>
          </template>
          
          <a-row :gutter="20">
            <a-col :span="6">
              <a-statistic title="Used Memory" :value="metrics.used_memory_human" />
            </a-col>
            <a-col :span="6">
              <a-statistic title="Max Memory" :value="metrics.maxmemory_human" />
            </a-col>
            <a-col :span="6">
              <a-statistic title="Connected Clients" :value="metrics.connected_clients" />
            </a-col>
            <a-col :span="6">
              <a-statistic title="Hit Rate" :value="metrics.hit_rate" unit="%" />
            </a-col>
          </a-row>

          <a-divider />

          <a-space size="large">
            <div class="metric-item">
              <span class="label">Uptime:</span>
              <span class="value">{{ formatUptime(metrics.uptime_in_seconds) }}</span>
            </div>
            <div class="metric-item">
              <span class="label">Fragmentation:</span>
              <span class="value">{{ metrics.mem_fragmentation_ratio }}</span>
            </div>
            <div class="metric-item">
              <span class="label">Version:</span>
              <span class="value">{{ metrics.version }}</span>
            </div>
          </a-space>
        </a-card>

        <!-- Memory Config -->
        <a-card title="Redis Configuration" style="margin-top: 20px">
          <a-form :model="configForm" layout="vertical" @submit="handleUpdateConfig">
            <a-row :gutter="20">
              <a-col :span="8">
                <a-form-item label="Max Memory (MB)" help="Recommended: 1/4 of total system RAM">
                  <a-input-number v-model="configForm.maxmemory_mb" :min="64" :max="16384" />
                </a-form-item>
              </a-col>
              <a-col :span="8">
                <a-form-item label="Eviction Policy" help="LRU is recommended for object caching">
                  <a-select v-model="configForm.policy">
                    <a-option value="allkeys-lru">allkeys-lru (Recommended)</a-option>
                    <a-option value="volatile-lru">volatile-lru</a-option>
                    <a-option value="allkeys-random">allkeys-random</a-option>
                    <a-option value="noeviction">noeviction</a-option>
                  </a-select>
                </a-form-item>
              </a-col>
              <a-col :span="8">
                <a-form-item label="Redis Password" help="Leave empty to disable password">
                  <a-input-password v-model="configForm.password" placeholder="New Password" />
                </a-form-item>
              </a-col>
            </a-row>
            <a-button type="primary" html-type="submit" :loading="loading.config">Update Configuration</a-button>
          </a-form>
        </a-card>
      </a-col>

      <!-- Redis Actions -->
      <a-col :span="8">
        <a-card title="Quick Actions" hoverable>
          <a-space direction="vertical" fill size="large">
            <a-button type="primary" long @click="handleAction('redis', 'restart')" :loading="loading.redis">
              <template #icon><icon-refresh /></template>
              Restart Redis Service
            </a-button>
            
            <a-popconfirm content="Are you sure to clear all Redis keys? This may temporarily slow down sites." @ok="handleFlush">
              <a-button status="danger" long :loading="loading.flush">
                <template #icon><icon-delete /></template>
                Flush All Cache (FLUSHALL)
              </a-button>
            </a-popconfirm>

            <a-divider />
            
            <div class="info-box">
              <icon-info-circle />
              <div class="text">
                Redis is used as an <b>Object Cache</b> for WordPress sites to significantly reduce database load.
              </div>
            </div>
          </a-space>
        </a-card>

        <a-card title="Site Isolation Status" style="margin-top: 20px">
          <div class="desc">
            Each site is automatically assigned a unique Redis database index (0-15) to prevent key collisions.
          </div>
          <a-list size="small" :bordered="false">
            <a-list-item v-for="site in sites" :key="site.id">
              <a-list-item-meta :title="site.domain" :description="'Redis DB Index: ' + (site.id % 16)" />
              <template #actions>
                <a-tag v-if="site.redis_enabled" color="green">Active</a-tag>
                <a-tag v-else color="gray">Inactive</a-tag>
                <a-button v-if="site.redis_enabled" type="text" size="small" @click="handleFlush(site.id)" :loading="loading['flush_' + site.id]">
                  Clear
                </a-button>
              </template>
            </a-list-item>
          </a-list>
        </a-card>
      </a-col>
    </a-row>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted } from 'vue'
import request from '@/utils/request'
import { Message } from '@arco-design/web-vue'
import { IconRefresh, IconDelete, IconInfoCircle } from '@arco-design/web-vue/es/icon'

const loading = reactive({
  redis: false,
  flush: false,
  config: false,
  metrics: false
})

const metrics = reactive({
  status: 'stopped',
  version: '-',
  uptime_in_seconds: 0,
  used_memory_human: '0B',
  maxmemory_human: '0B',
  connected_clients: 0,
  keyspace_hits: 0,
  keyspace_misses: 0,
  hit_rate: 0,
  mem_fragmentation_ratio: 0
})

const configForm = reactive({
  maxmemory_mb: 256,
  policy: 'allkeys-lru',
  password: ''
})

const sites = ref([])
let timer = null

const fetchConfig = async () => {
  try {
    const res = await request.get('/cache/redis/config')
    configForm.maxmemory_mb = res.maxmemory_mb
    configForm.policy = res.policy
    // We don't fetch the password itself for security, 
    // just let the user set a new one if needed.
  } catch (error) {
    console.error(error)
  }
}

const fetchMetrics = async () => {
  try {
    const res = await request.get('/cache/redis/status')
    Object.assign(metrics, res)
  } catch (error) {
    console.error(error)
  }
}

const fetchSites = async () => {
  try {
    sites.value = await request.get('/sites/')
  } catch (error) {
    console.error(error)
  }
}

const handleAction = async (service, action) => {
  loading[service] = true
  try {
    await request.post(`/service/${service}/${action}`)
    Message.success(`${service} ${action}ed successfully`)
    setTimeout(fetchMetrics, 2000)
  } catch (error) {
    console.error(error)
  } finally {
    loading[service] = false
  }
}

const handleFlush = async (siteId = null) => {
  const loadingKey = siteId ? `flush_${siteId}` : 'flush'
  loading[loadingKey] = true
  try {
    const url = siteId ? `/cache/redis/clear?site_id=${siteId}` : '/cache/redis/clear'
    await request.post(url)
    Message.success(siteId ? 'Site cache cleared' : 'All Redis cache cleared')
    fetchMetrics()
  } catch (error) {
    console.error(error)
  } finally {
    loading[loadingKey] = false
  }
}

const handleUpdateConfig = async () => {
  loading.config = true
  try {
    await request.post('/cache/redis/config', configForm)
    Message.success('Redis configuration updated')
    fetchMetrics()
  } catch (error) {
    console.error(error)
  } finally {
    loading.config = false
  }
}

const formatUptime = (seconds) => {
  if (!seconds) return '-'
  const d = Math.floor(seconds / (3600 * 24))
  const h = Math.floor((seconds % (3600 * 24)) / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  return `${d}d ${h}h ${m}m`
}

onMounted(() => {
  fetchMetrics()
  fetchConfig()
  fetchSites()
  timer = setInterval(fetchMetrics, 10000)
})

onUnmounted(() => {
  if (timer) clearInterval(timer)
})
</script>

<style scoped>
.metric-item {
  display: flex;
  gap: 8px;
  align-items: center;
}
.metric-item .label {
  color: var(--color-text-3);
  font-size: 13px;
}
.metric-item .value {
  font-weight: bold;
}
.info-box {
  background: var(--color-fill-2);
  padding: 15px;
  border-radius: 4px;
  display: flex;
  gap: 10px;
  align-items: flex-start;
  color: var(--color-text-2);
  font-size: 13px;
}
.desc {
  font-size: 12px;
  color: var(--color-text-3);
  margin-bottom: 15px;
}
</style>
