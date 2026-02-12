<template>
  <div class="cdn-container">
    <a-typography-title :heading="2">CDN Integration</a-typography-title>
    
    <a-row :gutter="20">
      <a-col :span="24" style="margin-bottom: 20px">
        <a-card>
          <a-space>
            <span>Select Site:</span>
            <a-select v-model="selectedSiteId" @change="fetchConfig" style="width: 300px">
              <a-option v-for="site in sites" :key="site.id" :value="site.id">{{ site.domain }}</a-option>
            </a-select>
          </a-space>
        </a-card>
      </a-col>

      <template v-if="selectedSiteId">
        <!-- Status -->
        <a-col :span="12">
          <a-card title="CDN Connection Status">
            <template v-if="config.status === 'connected'">
              <a-result status="success" :title="config.provider + ' Connected'">
                <template #subtitle>
                  CNAME: {{ config.cname }}
                </template>
                <template #extra>
                  <a-space>
                    <a-button type="outline" status="danger" @click="handleDisconnect">Disconnect</a-button>
                    <a-button type="primary" @click="handlePurge" :loading="purging">Purge Global Cache</a-button>
                  </a-space>
                </template>
              </a-result>
            </template>
            <template v-else>
              <a-empty description="No CDN Connected" />
            </template>
          </a-card>
        </a-col>

        <!-- Connection Form -->
        <a-col :span="12">
          <a-card title="Connect New CDN Provider">
            <a-form :model="form" layout="vertical">
              <a-form-item label="CDN Provider">
                <a-select v-model="form.provider">
                  <a-option>Cloudflare</a-option>
                  <a-option>StackPath</a-option>
                  <a-option>KeyCDN</a-option>
                </a-select>
              </a-form-item>
              <a-form-item label="API Key / Token">
                <a-input-password v-model="form.api_key" placeholder="Enter your CDN API Key" />
              </a-form-item>
              <a-form-item>
                <a-button type="primary" long @click="handleConnect" :loading="connecting">
                  Verify & Connect
                </a-button>
              </a-form-item>
            </a-form>
          </a-card>
        </a-col>
      </template>
    </a-row>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import request from '@/utils/request'
import { Message, Modal } from '@arco-design/web-vue'

const sites = ref([])
const selectedSiteId = ref(null)
const connecting = ref(false)
const purging = ref(false)

const config = reactive({
  provider: '',
  status: 'none',
  cname: '',
  api_key_last_4: ''
})

const form = reactive({
  provider: 'Cloudflare',
  api_key: ''
})

const fetchSites = async () => {
  try {
    sites.value = await request.get('/sites/')
    if (sites.value.length > 0) {
      selectedSiteId.value = sites.value[0].id
      fetchConfig()
    }
  } catch (error) {
    console.error(error)
  }
}

const fetchConfig = async () => {
  if (!selectedSiteId.value) return
  try {
    const res = await request.get(`/cdn/sites/${selectedSiteId.value}/config`)
    Object.assign(config, res)
  } catch (error) {
    // If 404, set to none
    config.status = 'none'
  }
}

const handleConnect = async () => {
  connecting.value = true
  try {
    const res = await request.post(`/cdn/sites/${selectedSiteId.value}/connect`, form)
    Message.success(res.message)
    fetchConfig()
  } catch (error) {
    console.error(error)
  } finally {
    connecting.value = false
  }
}

const handlePurge = async () => {
  purging.value = true
  try {
    const res = await request.post(`/cdn/sites/${selectedSiteId.value}/purge`)
    Message.success(res.message)
  } catch (error) {
    console.error(error)
  } finally {
    purging.value = false
  }
}

const handleDisconnect = () => {
  Modal.confirm({
    title: 'Disconnect CDN',
    content: 'Are you sure you want to disconnect this CDN? This will not delete your files on the CDN but will stop integration.',
    onOk: () => {
      config.status = 'none'
      Message.info('CDN Disconnected (Mock)')
    }
  })
}

onMounted(() => {
  fetchSites()
})
</script>
