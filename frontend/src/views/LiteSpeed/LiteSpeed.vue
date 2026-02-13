<template>
  <div class="litespeed-container">
    <div class="header-section">
      <a-typography-title :heading="2">OpenLiteSpeed 管理</a-typography-title>
      <a-button type="outline" @click="expertMode = !expertMode">
        {{ expertMode ? '简易模式' : '专家模式' }}
      </a-button>
    </div>

    <a-tabs default-active-key="1">
      <a-tab-pane key="1" title="服务状态">
        <a-row :gutter="20">
          <a-col :span="12">
            <a-card title="运行状态" hoverable>
              <template #extra>
                <a-tag :color="olsStatus.status === 'running' ? 'green' : 'red'">
                  {{ olsStatus.status?.toUpperCase() }}
                </a-tag>
              </template>
              <a-space direction="vertical" size="large" fill>
                <div class="status-item">
                  <span>版本:</span>
                  <a-tag color="arcoblue">{{ olsStatus.version }}</a-tag>
                </div>
                <div class="status-item">
                  <span>PID:</span>
                  <a-tag>{{ olsStatus.pid }}</a-tag>
                </div>
                <div class="status-item">
                  <span>运行时间:</span>
                  <span>{{ olsStatus.uptime || 'N/A' }}</span>
                </div>
                <a-divider />
                <a-space>
                  <a-button type="primary" @click="handleAction('restart')" :loading="loading">
                    <template #icon><icon-refresh /></template>
                    重启
                  </a-button>
                  <a-button @click="handleAction('reload')" :loading="loading">
                    <template #icon><icon-sync /></template>
                    重载配置
                  </a-button>
                  <a-button type="outline" status="danger" @click="handleAction('stop')" :loading="loading" v-if="olsStatus.status === 'running'">
                    停止
                  </a-button>
                  <a-button type="outline" status="success" @click="handleAction('start')" :loading="loading" v-else>
                    启动
                  </a-button>
                </a-space>
              </a-space>
            </a-card>
          </a-col>
          
          <a-col :span="12">
            <a-card title="性能开关" hoverable>
              <a-space direction="vertical" fill>
                <div class="config-item">
                  <span>HTTP/2 协议</span>
                  <a-switch v-model="features.http2" @change="toggleFeature('http2', $event)" />
                </div>
                <div class="config-item">
                  <span>HTTP/3 (QUIC) 协议</span>
                  <a-switch v-model="features.http3" @change="toggleFeature('http3', $event)" />
                </div>
                <div class="config-item">
                  <span>Brotli 压缩</span>
                  <a-switch v-model="features.brotli" @change="toggleFeature('brotli', $event)" />
                </div>
                <div class="config-item">
                  <span>LSCache 全局开关</span>
                  <a-switch v-model="features.lscache" @change="toggleFeature('lscache', $event)" />
                </div>
              </a-space>
            </a-card>
          </a-col>
        </a-row>
      </a-tab-pane>

      <a-tab-pane key="2" title="虚拟主机" v-if="expertMode">
        <a-table :data="vhosts" :loading="loading">
          <template #columns>
            <a-table-column title="主机名" data-index="name"></a-table-column>
            <a-table-column title="绑定域名" data-index="domain"></a-table-column>
            <a-table-column title="根目录" data-index="root"></a-table-column>
            <a-table-column title="操作">
              <template #cell="{ record }">
                <a-button type="text" size="small">配置预览</a-button>
                <a-button type="text" size="small">编辑</a-button>
              </template>
            </a-table-column>
          </template>
        </a-table>
      </a-tab-pane>

      <a-tab-pane key="3" title="安全设置" v-if="expertMode">
        <a-card title="防盗链 / IP 黑白名单">
          <a-form :model="securityConfig" layout="vertical">
            <a-form-item label="Referer 白名单 (每行一个)">
              <a-textarea v-model="securityConfig.refererWhitelist" placeholder="*.example.com" />
            </a-form-item>
            <a-form-item label="IP 黑名单">
              <a-textarea v-model="securityConfig.ipBlacklist" placeholder="192.168.1.1" />
            </a-form-item>
            <a-button type="primary">保存安全设置</a-button>
          </a-form>
        </a-card>
      </a-tab-pane>

      <a-tab-pane key="4" title="高级配置" v-if="expertMode">
        <a-alert type="warning">手动修改配置文件可能会导致服务无法启动，请谨慎操作。</a-alert>
        <div class="editor-container" style="margin-top: 20px;">
          <a-textarea :auto-size="{ minRows: 15 }" v-model="rawConfig" />
          <a-button type="primary" style="margin-top: 10px;">保存配置文件</a-button>
        </div>
      </a-tab-pane>
    </a-tabs>
  </div>
</template>

<script setup>
import { ref, onMounted, reactive } from 'vue'
import request from '@/utils/request'
import { Message } from '@arco-design/web-vue'

const olsStatus = ref({
  status: 'unknown',
  version: '',
  pid: '',
  uptime: ''
})
const loading = ref(false)
const expertMode = ref(false)
const vhosts = ref([])
const features = reactive({
  http2: true,
  http3: true,
  brotli: true,
  lscache: true
})
const securityConfig = reactive({
  refererWhitelist: '',
  ipBlacklist: ''
})
const rawConfig = ref('')

const fetchStatus = async () => {
  try {
    const res = await request.get('/litespeed/status')
    olsStatus.value = res
  } catch (error) {
    console.error(error)
  }
}

const fetchVHosts = async () => {
  try {
    const res = await request.get('/litespeed/vhosts')
    vhosts.value = res
  } catch (error) {
    console.error(error)
  }
}

const fetchFeatures = async () => {
  try {
    const res = await request.get('/litespeed/config/features')
    Object.assign(features, res)
  } catch (error) {
    console.error(error)
  }
}

const handleAction = async (action) => {
  loading.value = true
  try {
    await request.post(`/litespeed/action/${action}`)
    Message.success(`操作成功`)
    await fetchStatus()
  } catch (error) {
    console.error(error)
  } finally {
    loading.value = false
  }
}

const toggleFeature = async (feature, enabled) => {
  try {
    await request.post('/litespeed/config/features/toggle', { feature, enabled })
    Message.success(`${feature} 已${enabled ? '开启' : '关闭'}`)
  } catch (error) {
    console.error(error)
  }
}

onMounted(() => {
  fetchStatus()
  fetchVHosts()
  fetchFeatures()
})
</script>

<style scoped>
.litespeed-container {
  padding: 20px;
}
.header-section {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}
.status-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}
.config-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 0;
  border-bottom: 1px solid var(--color-fill-2);
}
.config-item:last-child {
  border-bottom: none;
}
</style>
