<template>
  <div class="assets-opt-container">
    <a-typography-title :heading="2">Frontend Asset Optimization</a-typography-title>
    
    <a-row :gutter="20">
      <a-col :span="24" style="margin-bottom: 20px">
        <a-card>
          <a-space>
            <span>Select Site:</span>
            <a-select v-model="selectedSiteId" @change="fetchStatus" style="width: 300px">
              <a-option v-for="site in sites" :key="site.id" :value="site.id">{{ site.domain }}</a-option>
            </a-select>
          </a-space>
        </a-card>
      </a-col>

      <template v-if="selectedSiteId">
        <!-- Current Status -->
        <a-col :span="12">
          <a-card title="Current Asset Status">
            <a-descriptions :column="1" bordered>
              <a-descriptions-item label="CSS Minified">
                <a-tag :color="status.css_minified ? 'green' : 'red'">{{ status.css_minified ? 'Yes' : 'No' }}</a-tag>
              </a-descriptions-item>
              <a-descriptions-item label="JS Minified">
                <a-tag :color="status.js_minified ? 'green' : 'red'">{{ status.js_minified ? 'Yes' : 'No' }}</a-tag>
              </a-descriptions-item>
              <a-descriptions-item label="Critical CSS">
                <a-tag :color="status.critical_css_generated ? 'green' : 'red'">{{ status.critical_css_generated ? 'Generated' : 'Missing' }}</a-tag>
              </a-descriptions-item>
              <a-descriptions-item label="Fonts Localized">
                <a-tag :color="status.fonts_localized ? 'green' : 'red'">{{ status.fonts_localized ? 'Yes' : 'No' }}</a-tag>
              </a-descriptions-item>
              <a-descriptions-item label="Total Assets">{{ status.total_assets }} files</a-descriptions-item>
              <a-descriptions-item label="Optimizable Space">{{ status.optimizable_size_kb }} KB</a-descriptions-item>
            </a-descriptions>
          </a-card>
        </a-col>

        <!-- Optimization Config -->
        <a-col :span="12">
          <a-card title="Optimization Settings">
            <a-space direction="vertical" fill size="large">
              <a-checkbox v-model="config.minify_css">Minify CSS & Merge</a-checkbox>
              <a-checkbox v-model="config.minify_js">Minify JS & Merge</a-checkbox>
              <a-checkbox v-model="config.generate_critical_css">Generate Critical CSS (Above-the-fold)</a-checkbox>
              <a-checkbox v-model="config.localize_fonts">Localize Google Fonts</a-checkbox>
              
              <a-divider />
              
              <a-button type="primary" long @click="handleOptimize" :loading="optimizing">
                Run Asset Optimization
              </a-button>
            </a-space>
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
const status = reactive({
  css_minified: false,
  js_minified: false,
  critical_css_generated: false,
  fonts_localized: false,
  total_assets: 0,
  optimizable_size_kb: 0
})

const config = reactive({
  minify_css: true,
  minify_js: true,
  generate_critical_css: false,
  localize_fonts: true
})

const fetchSites = async () => {
  try {
    sites.value = await request.get('/sites/')
    if (sites.value.length > 0) {
      selectedSiteId.value = sites.value[0].id
      fetchStatus()
    }
  } catch (error) {
    console.error(error)
  }
}

const fetchStatus = async () => {
  if (!selectedSiteId.value) return
  try {
    const res = await request.get(`/assets/sites/${selectedSiteId.value}/status`)
    Object.assign(status, res)
  } catch (error) {
    console.error(error)
  }
}

const handleOptimize = async () => {
  optimizing.value = true
  try {
    const res = await request.post(`/assets/sites/${selectedSiteId.value}/optimize`, config)
    Message.success(res.message + ` (Saved: ${res.saved_size})`)
    fetchStatus()
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
