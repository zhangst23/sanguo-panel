<template>
  <div class="cache-container">
    <a-typography-title :heading="2">Performance & Cache Control</a-typography-title>
    
    <a-row :gutter="20">
      <!-- Site Selection -->
      <a-col :span="24" style="margin-bottom: 20px">
        <a-card>
          <a-space>
            <span>Select Site:</span>
            <a-select v-model="selectedSiteId" @change="fetchSiteSettings" style="width: 300px">
              <a-option v-for="site in sites" :key="site.id" :value="site.id">{{ site.domain }}</a-option>
            </a-select>
          </a-space>
        </a-card>
      </a-col>

      <template v-if="selectedSiteId">
        <!-- Preset Slider -->
        <a-col :span="24" style="margin-bottom: 20px">
          <a-card title="Performance Preset">
            <div class="preset-slider-wrapper">
              <a-slider
                v-model="presetValue"
                :max="2"
                :step="1"
                :marks="{ 0: 'Basic', 1: 'Balanced', 2: 'Ultimate' }"
                @change="handlePresetChange"
              />
            </div>
            <div class="preset-desc">
              <a-alert v-if="presetValue === 0" type="info">Basic: Minimum caching. Best for development or sites with highly dynamic content.</a-alert>
              <a-alert v-if="presetValue === 1" type="success">Balanced: Recommended for most sites. High performance with good compatibility.</a-alert>
              <a-alert v-if="presetValue === 2" type="warning">Ultimate: Maximum performance. Best for high-traffic sites. (LSCache + Aggressive Redis)</a-alert>
            </div>
          </a-card>
        </a-col>

        <!-- Detailed Toggles -->
        <a-col :span="12">
          <a-card title="Advanced Cache Settings">
            <a-space direction="vertical" fill size="large">
              <div class="toggle-item">
                <div class="info">
                  <div class="title">LiteSpeed Cache (LSCache)</div>
                  <div class="desc">Full-page caching at server level.</div>
                </div>
                <a-switch v-model="siteSettings.lscache_enabled" @change="updateSettings" />
              </div>
              <div class="toggle-item">
                <div class="info">
                  <div class="title">Redis Object Cache</div>
                  <div class="desc">Accelerates database queries and PHP objects.</div>
                </div>
                <a-switch v-model="siteSettings.redis_enabled" @change="updateSettings" />
              </div>
              <div class="toggle-item">
                <div class="info">
                  <div class="title">PHP OPcache</div>
                  <div class="desc">Speeds up PHP execution by caching bytecode.</div>
                </div>
                <a-switch v-model="siteSettings.opcache_enabled" @change="updateSettings" />
              </div>
              <div class="toggle-item">
                <div class="info">
                  <div class="title">Browser Cache</div>
                  <div class="desc">Caches static assets on the visitor's browser.</div>
                </div>
                <a-switch v-model="siteSettings.browser_cache_enabled" @change="updateSettings" />
              </div>
            </a-space>
          </a-card>
        </a-col>

        <!-- Actions -->
        <a-col :span="12">
          <a-card title="Cache Actions">
            <a-space direction="vertical" fill>
              <a-button type="outline" long @click="handlePurge('all')" :loading="purging">Purge All Cache</a-button>
              <a-button type="outline" long @click="handlePurge('lscache')">Purge LSCache Only</a-button>
              <a-button type="outline" long @click="handlePurge('redis')">Flush Redis Only</a-button>
            </a-space>
          </a-card>
        </a-col>
      </template>
    </a-row>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, watch } from 'vue'
import request from '@/utils/request'
import { Message } from '@arco-design/web-vue'

const sites = ref([])
const selectedSiteId = ref(null)
const presetValue = ref(1)
const purging = ref(false)

const siteSettings = reactive({
  lscache_enabled: true,
  redis_enabled: true,
  opcache_enabled: true,
  browser_cache_enabled: true,
  performance_preset: 'balanced'
})

const presetMap = { 0: 'basic', 1: 'balanced', 2: 'ultimate' }
const valueMap = { 'basic': 0, 'balanced': 1, 'ultimate': 2 }

const fetchSites = async () => {
  try {
    sites.value = await request.get('/sites/')
    if (sites.value.length > 0) {
      selectedSiteId.value = sites.value[0].id
      fetchSiteSettings()
    }
  } catch (error) {
    console.error(error)
  }
}

const fetchSiteSettings = async () => {
  if (!selectedSiteId.value) return
  try {
    const res = await request.get(`/cache/sites/${selectedSiteId.value}`)
    Object.assign(siteSettings, res)
    presetValue.value = valueMap[res.performance_preset] || 1
  } catch (error) {
    console.error(error)
  }
}

const handlePresetChange = async (val) => {
  const preset = presetMap[val]
  try {
    const res = await request.post(`/cache/sites/${selectedSiteId.value}/preset?preset=${preset}`)
    Object.assign(siteSettings, res)
    Message.success(`Performance preset updated to ${preset}`)
  } catch (error) {
    console.error(error)
  }
}

const updateSettings = async () => {
  try {
    await request.patch(`/sites/${selectedSiteId.value}`, siteSettings)
    Message.success('Cache settings updated')
  } catch (error) {
    console.error(error)
  }
}

const handlePurge = async (type) => {
  purging.value = true
  try {
    await request.post(`/cache/sites/${selectedSiteId.value}/purge?cache_type=${type}`)
    Message.success(`${type} cache purged successfully`)
  } catch (error) {
    console.error(error)
  } finally {
    purging.value = false
  }
}

onMounted(() => {
  fetchSites()
})
</script>

<style scoped>
.preset-slider-wrapper {
  padding: 20px 40px 40px;
}
.preset-desc {
  margin-top: 10px;
}
.toggle-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.toggle-item .title {
  font-weight: bold;
  font-size: 14px;
}
.toggle-item .desc {
  font-size: 12px;
  color: var(--color-text-3);
}
</style>
