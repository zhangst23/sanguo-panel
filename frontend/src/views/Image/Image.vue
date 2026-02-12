<template>
  <div class="image-opt-container">
    <a-typography-title :heading="2">Image Optimization</a-typography-title>
    
    <a-row :gutter="20">
      <a-col :span="24" style="margin-bottom: 20px">
        <a-card>
          <a-space>
            <span>Select Site:</span>
            <a-select v-model="selectedSiteId" @change="fetchStats" style="width: 300px">
              <a-option v-for="site in sites" :key="site.id" :value="site.id">{{ site.domain }}</a-option>
            </a-select>
          </a-space>
        </a-card>
      </a-col>

      <template v-if="selectedSiteId">
        <!-- Stats -->
        <a-col :span="16">
          <a-card title="Optimization Statistics">
            <a-row :gutter="20">
              <a-col :span="8">
                <a-statistic title="Total Images" :value="stats.total_images" show-group-separator />
              </a-col>
              <a-col :span="8">
                <a-statistic title="Optimized" :value="stats.optimized_images" color="#00b42a" show-group-separator />
              </a-col>
              <a-col :span="8">
                <a-statistic title="Space Saved" :value="stats.space_saved_mb" precision="2" suffix="MB" />
              </a-col>
            </a-row>
            <div style="margin-top: 20px">
              <a-progress :percent="Math.round((stats.optimized_images / stats.total_images) * 100)" status="success" />
            </div>
          </a-card>
        </a-col>

        <!-- Configuration -->
        <a-col :span="8">
          <a-card title="Optimization Settings">
            <a-space direction="vertical" fill>
              <div>
                <div style="margin-bottom: 10px">Quality: {{ quality }}%</div>
                <a-slider v-model="quality" :min="50" :max="100" />
              </div>
              <a-checkbox v-model="convertWebP">Convert to WebP</a-checkbox>
              <a-checkbox v-model="convertAVIF">Convert to AVIF</a-checkbox>
              <a-button type="primary" long @click="handleOptimize" :loading="optimizing">
                Start Optimization
              </a-button>
            </a-space>
          </a-card>
        </a-col>

        <!-- Progress Log -->
        <a-col :span="24" style="margin-top: 20px" v-if="logs.length > 0">
          <a-card title="Optimization Logs">
            <div class="log-container">
              <div v-for="(log, index) in logs" :key="index" class="log-item">
                <span class="log-time">[{{ new Date().toLocaleTimeString() }}]</span> {{ log }}
              </div>
            </div>
          </a-card>
        </a-col>
      </template>
    </a-row>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import request from '@/utils/request'
import { Message } from '@arco-design/web-vue'

const sites = ref([])
const selectedSiteId = ref(null)
const optimizing = ref(false)
const quality = ref(80)
const convertWebP = ref(true)
const convertAVIF = ref(false)
const logs = ref([])

const stats = reactive({
  total_images: 0,
  optimized_images: 0,
  unoptimized_images: 0,
  space_saved_mb: 0
})

const fetchSites = async () => {
  try {
    sites.value = await request.get('/sites/')
    if (sites.value.length > 0) {
      selectedSiteId.value = sites.value[0].id
      fetchStats()
    }
  } catch (error) {
    console.error(error)
  }
}

const fetchStats = async () => {
  if (!selectedSiteId.value) return
  try {
    const res = await request.get(`/images/sites/${selectedSiteId.value}/stats`)
    Object.assign(stats, res)
  } catch (error) {
    console.error(error)
  }
}

const handleOptimize = async () => {
  optimizing.value = true
  logs.value = []
  try {
    const res = await request.post(`/images/sites/${selectedSiteId.value}/optimize`, {
      quality: quality.value,
      convert_webp: convertWebP.value,
      convert_avif: convertAVIF.value
    })
    Message.success(res.message)
    logs.value = res.tasks
  } catch (error) {
    console.error(error)
  } finally {
    optimizing.value = false
  }
}

onMounted(() => {
  fetchSites()
})
</script>

<style scoped>
.log-container {
  background: #1d2129;
  color: #fff;
  padding: 15px;
  border-radius: 4px;
  font-family: monospace;
  height: 200px;
  overflow-y: auto;
}
.log-item {
  margin-bottom: 5px;
}
.log-time {
  color: #86909c;
}
</style>
