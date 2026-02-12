<template>
  <div class="ssl-container">
    <a-typography-title :heading="2">SSL Certificates</a-typography-title>
    
    <a-row :gutter="20">
      <a-col :span="24">
        <a-card>
          <a-table :data="sites" :columns="columns" :loading="loading">
            <template #ssl_status="{ record }">
              <a-tag v-if="record.ssl_status === 0" color="gray">None</a-tag>
              <a-tag v-else-if="record.ssl_status === 1" color="green">Active</a-tag>
              <a-tag v-else-if="record.ssl_status === 2" color="blue">Force HTTPS</a-tag>
              <a-tag v-else color="red">Error</a-tag>
            </template>
            <template #actions="{ record }">
              <a-space>
                <a-button v-if="record.ssl_status === 0" type="primary" size="small" @click="handleApply(record)">
                  Apply SSL
                </a-button>
                <a-button v-else size="small" status="danger" @click="handleDisable(record)">
                  Disable
                </a-button>
                <a-button size="small" @click="handleCheckStatus(record)">Check Status</a-button>
              </a-space>
            </template>
          </a-table>
        </a-card>
      </a-col>
    </a-row>

    <!-- Apply SSL Modal -->
    <a-modal v-model:visible="showApplyModal" title="Apply for SSL Certificate (Let's Encrypt)" @ok="confirmApply">
      <div v-if="selectedSite">
        <p>Applying for: <b>{{ selectedSite.domain }}</b></p>
        <p>This will use Certbot to request a free SSL certificate from Let's Encrypt.</p>
        <a-checkbox v-model="forceHttps">Force HTTPS (Redirect HTTP to HTTPS)</a-checkbox>
      </div>
    </a-modal>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import request from '@/utils/request'
import { Message, Modal } from '@arco-design/web-vue'

const sites = ref([])
const loading = ref(false)
const showApplyModal = ref(false)
const selectedSite = ref(null)
const forceHttps = ref(true)

const columns = [
  { title: 'Domain', dataIndex: 'domain' },
  { title: 'SSL Status', slotName: 'ssl_status' },
  { title: 'PHP Version', dataIndex: 'php_version' },
  { title: 'Actions', slotName: 'actions' },
]

const fetchSites = async () => {
  loading.value = true
  try {
    sites.value = await request.get('/sites/')
  } catch (error) {
    console.error(error)
  } finally {
    loading.value = false
  }
}

const handleApply = (site) => {
  selectedSite.value = site
  showApplyModal.value = true
}

const confirmApply = async () => {
  try {
    await request.post(`/ssl/sites/${selectedSite.value.id}/apply?force_https=${forceHttps.value}`)
    Message.success(`SSL applied for ${selectedSite.value.domain}`)
    showApplyModal.value = false
    fetchSites()
  } catch (error) {
    console.error(error)
  }
}

const handleDisable = async (site) => {
  Modal.confirm({
    title: 'Disable SSL',
    content: `Are you sure you want to disable SSL for ${site.domain}?`,
    onOk: async () => {
      try {
        await request.post(`/ssl/sites/${site.id}/disable`)
        Message.success(`SSL disabled for ${site.domain}`)
        fetchSites()
      } catch (error) {
        console.error(error)
      }
    }
  })
}

const handleCheckStatus = async (site) => {
  try {
    const res = await request.get(`/ssl/sites/${site.id}/status`)
    Modal.info({
      title: 'SSL Certificate Status',
      content: `Issuer: ${res.issuer}\nExpiry: ${res.expiry_date}\nDomains: ${res.domains.join(', ')}`
    })
  } catch (error) {
    console.error(error)
  }
}

onMounted(() => {
  fetchSites()
})
</script>
