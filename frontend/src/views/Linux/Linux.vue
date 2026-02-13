<template>
  <div class="linux-container">
    <div class="header-section">
      <a-typography-title :heading="2">Linux 系统优化</a-typography-title>
      <a-typography-paragraph>
        面板自动检测并优化 Linux 内核参数、服务配置，提升服务器整体处理能力。
      </a-typography-paragraph>
    </div>

    <a-row :gutter="20">
      <!-- 优化概览 -->
      <a-col :span="16">
        <a-card title="优化状态" :loading="loading.status">
          <template #extra>
            <a-tag :color="status.optimized ? 'green' : 'orange'">
              {{ status.optimized ? '系统已达到最佳状态' : '建议应用优化' }}
            </a-tag>
          </template>
          
          <a-list :bordered="false">
            <a-list-item>
              <a-list-item-meta title="TCP BBR 拥塞控制" description="调整 TCP 缓冲区大小及 BBR 算法，提升网络并发能力。">
                <template #avatar>
                  <icon-thunderbolt :style="{ color: status.tcp_bbr ? '#00b42a' : '#f53f3f' }" />
                </template>
              </a-list-item-meta>
              <template #actions>
                <a-tag :color="status.tcp_bbr ? 'green' : 'red'">{{ status.tcp_bbr ? '已开启' : '未开启' }}</a-tag>
              </template>
            </a-list-item>

            <a-list-item>
              <a-list-item-meta title="文件句柄限制 (ulimit)" description="提升系统最大文件打开数，增强高并发处理能力。">
                <template #avatar>
                  <icon-file :style="{ color: status.file_limits >= 65535 ? '#00b42a' : '#f53f3f' }" />
                </template>
              </a-list-item-meta>
              <template #actions>
                <span>{{ status.file_limits }}</span>
              </template>
            </a-list-item>

            <a-list-item>
              <a-list-item-meta title="Swap 交换分区优化" description="调整 swappiness 值为 10，减少不必要的磁盘 I/O。">
                <template #avatar>
                  <icon-swap :style="{ color: status.swappiness <= 10 ? '#00b42a' : '#f53f3f' }" />
                </template>
              </a-list-item-meta>
              <template #actions>
                <span>{{ status.swappiness }}</span>
              </template>
            </a-list-item>

            <a-list-item>
              <a-list-item-meta title="时间同步服务 (NTP)" description="安装并启用 chrony 服务，确保服务器时间准确。">
                <template #avatar>
                  <icon-clock-circle :style="{ color: status.ntp_status === 'active' ? '#00b42a' : '#f53f3f' }" />
                </template>
              </a-list-item-meta>
              <template #actions>
                <a-tag :color="status.ntp_status === 'active' ? 'green' : 'red'">{{ status.ntp_status === 'active' ? '运行中' : '未运行' }}</a-tag>
              </template>
            </a-list-item>
          </a-list>

          <div style="margin-top: 20px; text-align: right;">
            <a-button type="primary" size="large" @click="handleApply" :loading="loading.apply">
              <template #icon><icon-check-circle /></template>
              应用全站优化
            </a-button>
          </div>
        </a-card>
      </a-col>

      <!-- 服务精简 -->
      <a-col :span="8">
        <a-card title="无用服务清理" :loading="loading.services">
          <a-typography-text type="secondary" size="small">
            禁用不需要的系统服务，释放内存资源。
          </a-typography-text>
          
          <a-list style="margin-top: 15px;">
            <a-list-item v-for="svc in services" :key="svc.name">
              <a-list-item-meta :title="svc.name" :description="svc.description" />
              <template #actions>
                <a-switch 
                  :model-value="svc.active" 
                  checked-color="#f53f3f"
                  unchecked-color="#00b42a"
                  @change="(val) => handleToggleService(svc, val)"
                  :loading="loading[svc.name]"
                >
                  <template #checked>运行中</template>
                  <template #unchecked>已禁用</template>
                </a-switch>
              </template>
            </a-list-item>
          </a-list>
        </a-card>
      </a-col>
    </a-row>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import request from '@/utils/request'
import { Message, Modal } from '@arco-design/web-vue'

const status = reactive({
  tcp_bbr: false,
  file_limits: 0,
  swappiness: 60,
  io_scheduler: 'unknown',
  ntp_status: 'inactive',
  optimized: false
})

const services = ref([])
const loading = reactive({
  status: false,
  apply: false,
  services: false
})

const fetchStatus = async () => {
  loading.status = true
  try {
    const res = await request.get('/linux/optimization/status')
    Object.assign(status, res)
  } catch (error) {
    console.error(error)
  } finally {
    loading.status = false
  }
}

const fetchServices = async () => {
  loading.services = true
  try {
    services.value = await request.get('/linux/services/removable')
  } catch (error) {
    console.error(error)
  } finally {
    loading.services = false
  }
}

const handleApply = () => {
  Modal.confirm({
    title: '确认优化',
    content: '系统将修改 /etc/sysctl.conf 和 /etc/security/limits.conf 等核心配置，并安装 chrony 服务。是否继续？',
    onOk: async () => {
      loading.apply = true
      try {
        await request.post('/linux/optimization/apply')
        Message.success('系统优化参数已应用')
        fetchStatus()
      } catch (error) {
        console.error(error)
      } finally {
        loading.apply = false
      }
    }
  })
}

const handleToggleService = async (svc, val) => {
  if (val) {
    Message.info('目前仅支持禁用服务以释放资源')
    return
  }
  
  loading[svc.name] = true
  try {
    await request.post(`/linux/services/disable?service_name=${svc.name}`)
    Message.success(`服务 ${svc.name} 已禁用`)
    fetchServices()
  } catch (error) {
    console.error(error)
  } finally {
    loading[svc.name] = false
  }
}

onMounted(() => {
  fetchStatus()
  fetchServices()
})
</script>

<style scoped lang="scss">
.linux-container {
  .header-section {
    margin-bottom: 24px;
  }
}
</style>
