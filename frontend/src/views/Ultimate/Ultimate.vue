<template>
  <div class="ultimate-opt-container">
    <a-typography-title :heading="2">One-Click Ultimate Optimization</a-typography-title>
    
    <a-row :gutter="20">
      <a-col :span="24">
        <a-card>
          <div class="hero-section">
            <icon-thunderbolt-fill style="font-size: 64px; color: #ff7d00" />
            <a-typography-title :heading="3">Speed Up Your Site in One Click</a-typography-title>
            <p>This will automatically run all optimization modules: Cache, Images, Assets, DB, and CDN.</p>
            
            <a-space direction="vertical" fill style="max-width: 400px; margin: 0 auto">
              <a-select v-model="selectedSiteId" placeholder="Select Site to Optimize">
                <a-option v-for="site in sites" :key="site.id" :value="site.id">{{ site.domain }}</a-option>
              </a-select>
              <a-button type="primary" size="large" long :disabled="!selectedSiteId" @click="handleRun" :loading="running">
                RUN ULTIMATE OPTIMIZATION
              </a-button>
            </a-space>
          </div>
        </a-card>
      </a-col>

      <!-- Progress -->
      <a-col :span="24" style="margin-top: 20px" v-if="steps.length > 0">
        <a-card title="Optimization Steps">
          <a-steps direction="vertical" :current="currentStep">
            <a-step v-for="(step, index) in steps" :key="index" :title="step">
              <template #icon v-if="index < currentStep">
                <icon-check-circle-fill />
              </template>
            </a-step>
          </a-steps>
          
          <div v-if="finished" style="margin-top: 20px">
            <a-alert type="success">
              Optimization Finished! Performance Score estimated increase: {{ scoreIncrease }}
            </a-alert>
          </div>
        </a-card>
      </a-col>
    </a-row>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import request from '@/utils/request'
import { Message } from '@arco-design/web-vue'
import { IconCheckCircleFill } from '@arco-design/web-vue/es/icon'

const sites = ref([])
const selectedSiteId = ref(null)
const running = ref(false)
const finished = ref(false)
const steps = ref([])
const currentStep = ref(0)
const scoreIncrease = ref('')

const fetchSites = async () => {
  try {
    sites.value = await request.get('/sites/')
    if (sites.value.length > 0) {
      selectedSiteId.value = sites.value[0].id
    }
  } catch (error) {
    console.error(error)
  }
}

const handleRun = async () => {
  running.value = true
  finished.value = false
  steps.value = []
  currentStep.value = 0
  
  try {
    const res = await request.post(`/ultimate/sites/${selectedSiteId.value}/optimize`)
    steps.value = res.steps
    scoreIncrease.value = res.performance_score_increase
    
    // Simulate step progress
    const interval = setInterval(() => {
      if (currentStep.value < steps.value.length) {
        currentStep.value++
      } else {
        clearInterval(interval)
        running.value = false
        finished.value = true
        Message.success('Optimization finished!')
      }
    }, 1000)
    
  } catch (error) {
    console.error(error)
    running.value = false
  }
}

onMounted(() => {
  fetchSites()
})
</script>

<style scoped>
.hero-section {
  text-align: center;
  padding: 40px 0;
}
</style>
