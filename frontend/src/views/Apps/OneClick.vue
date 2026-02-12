<template>
  <div class="apps-container">
    <a-typography-title :heading="2">One-Click Deployment</a-typography-title>
    
    <a-row :gutter="20">
      <a-col :span="8" v-for="app in availableApps" :key="app.name">
        <a-card hoverable style="margin-bottom: 20px">
          <template #cover>
            <div :style="{ height: '160px', overflow: 'hidden', background: app.color, display: 'flex', alignItems: 'center', justifyContent: 'center' }">
              <icon-apps :style="{ fontSize: '64px', color: '#fff' }" />
            </div>
          </template>
          <a-card-meta :title="app.name" :description="app.description">
          </a-card-meta>
          <template #actions>
            <a-button type="primary" @click="handleInstall(app)" :loading="installing === app.name">Install Now</a-button>
          </template>
        </a-card>
      </a-col>
    </a-row>

    <!-- Install Modal -->
    <a-modal v-model:visible="showModal" :title="`Install ${selectedApp?.name}`" @ok="confirmInstall" @cancel="selectedApp = null">
      <a-form :model="installForm" layout="vertical">
        <a-form-item field="site_id" label="Select Site" required>
          <a-select v-model="installForm.site_id" placeholder="Select a site to install on">
            <a-option v-for="site in sites" :key="site.id" :value="site.id">{{ site.domain }}</a-option>
          </a-select>
        </a-form-item>
        <a-form-item field="admin_user" label="Admin Username" required v-if="selectedApp?.name === 'WordPress'">
          <a-input v-model="installForm.admin_user" />
        </a-form-item>
        <a-form-item field="admin_pass" label="Admin Password" required v-if="selectedApp?.name === 'WordPress'">
          <a-input-password v-model="installForm.admin_pass" />
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import request from '@/utils/request'
import { Message } from '@arco-design/web-vue'

const availableApps = [
  { name: 'WordPress', description: 'The world\'s most popular website builder.', color: '#21759b' },
  { name: 'Typecho', description: 'A lightweight PHP blogging platform.', color: '#467b96' },
  { name: 'Nextcloud', description: 'Safe home for all your data.', color: '#0082c9' }
]

const sites = ref([])
const installing = ref('')
const showModal = ref(false)
const selectedApp = ref(null)

const installForm = reactive({
  site_id: null,
  admin_user: 'admin',
  admin_pass: ''
})

const fetchSites = async () => {
  try {
    sites.value = await request.get('/sites/')
  } catch (error) {
    console.error(error)
  }
}

const handleInstall = (app) => {
  selectedApp.value = app
  showModal.value = true
}

const confirmInstall = async () => {
  if (!installForm.site_id) {
    Message.error('Please select a site')
    return
  }
  
  const appName = selectedApp.value.name
  installing.value = appName
  showModal.value = false
  
  try {
    // Mock installation process
    Message.info(`Starting ${appName} installation...`)
    await new Promise(resolve => setTimeout(resolve, 3000))
    Message.success(`${appName} installed successfully on site!`)
  } catch (error) {
    console.error(error)
  } finally {
    installing.value = ''
    selectedApp.value = null
  }
}

onMounted(() => {
  fetchSites()
})
</script>
