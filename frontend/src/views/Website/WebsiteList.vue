<template>
  <div class="website-list">
    <div class="section-header">
      <a-typography-title :heading="2">网站管理</a-typography-title>
      <a-button type="primary" @click="showCreateModal = true">
        <template #icon><icon-plus /></template>
        创建站点
      </a-button>
    </div>

    <a-card class="list-card">
      <a-table :data="sites" :loading="loading" :pagination="false">
        <template #columns>
          <a-table-column title="域名" data-index="domain">
            <template #cell="{ record }">
              <div class="domain-info">
                <div class="primary-domain">{{ record.domain }}</div>
                <div class="aliases" v-if="record.aliases?.length">
                  <a-tag v-for="alias in record.aliases" :key="alias" size="mini">{{ alias }}</a-tag>
                </div>
              </div>
            </template>
          </a-table-column>
          <a-table-column title="PHP版本" data-index="php_version">
            <template #cell="{ record }">
              <a-tag color="arcoblue">{{ record.php_version }}</a-tag>
            </template>
          </a-table-column>
          <a-table-column title="状态">
            <template #cell="{ record }">
              <a-badge :status="record.status === 'active' ? 'success' : 'danger'" :text="record.status === 'active' ? '运行中' : '已停止'" />
            </template>
          </a-table-column>
          <a-table-column title="速度评分">
            <template #cell="{ record }">
              <a-tooltip :content="`移动端: ${record.speed_score || 90}分`">
                <a-progress type="circle" :percent="(record.speed_score || 90) / 100" size="mini" :color="getScoreColor(record.speed_score || 90)" />
              </a-tooltip>
            </template>
          </a-table-column>
          <a-table-column title="缓存状态">
            <template #cell="{ record }">
              <a-tag color="green" v-if="record.lscache_enabled">已开启 (四层)</a-tag>
              <a-tag color="gray" v-else>未开启</a-tag>
            </template>
          </a-table-column>
          <a-table-column title="操作">
            <template #cell="{ record }">
              <a-space>
                <a-button type="text" size="small">管理</a-button>
                <a-button type="text" size="small">清理缓存</a-button>
                <a-dropdown>
                  <a-button type="text" size="small"><icon-more /></a-button>
                  <template #content>
                    <a-doption>SSL 配置</a-doption>
                    <a-doption>备份管理</a-doption>
                    <a-doption status="danger" @click="handleDelete(record.id)">删除站点</a-doption>
                  </template>
                </a-dropdown>
              </a-space>
            </template>
          </a-table-column>
        </template>
      </a-table>
    </a-card>

    <!-- Create Site Modal -->
    <a-modal 
      v-model:visible="showCreateModal" 
      title="创建新站点" 
      :width="550"
      @ok="handleCreate"
      @cancel="resetForm"
      :confirm-loading="confirmLoading"
      ok-text="立即创建"
      cancel-text="取消"
    >
      <a-form :model="form" layout="vertical" class="create-form">
        <!-- Basic Info Section -->
        <div class="form-section">
          <div class="section-title">基本信息</div>
          <a-form-item field="domain" label="站点域名" required help="输入主域名，系统将自动配置根目录及数据库">
            <a-input v-model="form.domain" placeholder="例如: example.com" @input="handleDomainInput" />
          </a-form-item>
          <a-form-item field="php_version" label="PHP 版本">
            <a-select v-model="form.php_version">
              <a-option>8.2</a-option>
              <a-option>8.1</a-option>
              <a-option>7.4</a-option>
            </a-select>
          </a-form-item>
          <a-form-item label="数据库类型">
            <a-input placeholder="默认MariaDB" disabled />
          </a-form-item>
          <a-form-item field="root_path" label="根目录">
            <a-input v-model="form.root_path" placeholder="默认: /www/wwwroot/域名" />
          </a-form-item>
        </div>

        <!-- Performance Section -->
        <div class="form-section">
          <div class="section-title">性能优化</div>
          <div class="optimization-card">
            <div class="opt-header">
              <icon-check-circle-fill class="opt-icon" />
              <span class="opt-title">WordPress 专项性能优化已开启</span>
            </div>
            <p class="opt-desc">
              系统将自动配置：OpenLiteSpeed 技术底座、MariaDB 专属优化、Redis 对象缓存、OPcache 深度优化、浏览器缓存、全站静态化、图片自动化压缩、CSS/JS 合并等。
            </p>
          </div>
        </div>
        
        <div class="confirm-tip mini">
          <icon-info-circle /> 点击创建后，系统将自动完成环境部署、数据库创建及 WordPress 安装。
        </div>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import request from '@/utils/request'
import { Message } from '@arco-design/web-vue'
import { IconPlus, IconMore, IconInfoCircle, IconCheckCircleFill } from '@arco-design/web-vue/es/icon'

const loading = ref(false)
const sites = ref([])
const showCreateModal = ref(false)
const confirmLoading = ref(false)

const form = reactive({
  domain: '',
  root_path: '',
  php_version: '8.2',
  performance_preset: 'performance' // 默认开启极致优化
})

const getScoreColor = (score) => {
  if (score >= 90) return '#00b42a'
  if (score >= 60) return '#ff7d00'
  return '#f53f3f'
}

const handleDomainInput = () => {
  if (form.domain) {
    form.root_path = `/www/wwwroot/${form.domain}`
  } else {
    form.root_path = ''
  }
}

const fetchSites = async () => {
  loading.value = true
  try {
    const res = await request.get('/sites/')
    sites.value = res
  } catch (error) {
    console.error(error)
  } finally {
    loading.value = false
  }
}

const handleCreate = async () => {
  if (!form.domain) {
    Message.error('请输入站点域名')
    return false
  }
  confirmLoading.value = true
  try {
    await request.post('/sites/', form)
    Message.success('站点创建成功，正在后台部署中...')
    showCreateModal.value = false
    resetForm()
    fetchSites()
  } catch (error) {
    console.error(error)
  } finally {
    confirmLoading.value = false
  }
}

const handleDelete = async (id) => {
  try {
    await request.delete(`/sites/${id}`)
    Message.success('站点已删除')
    fetchSites()
  } catch (error) {
    console.error(error)
  }
}

const resetForm = () => {
  Object.assign(form, {
    domain: '',
    root_path: '',
    php_version: '8.2',
    performance_preset: 'performance'
  })
}

onMounted(() => {
  fetchSites()
})
</script>

<style scoped>
.website-list {
  padding: 20px;
}
.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}
.list-card {
  border-radius: 8px;
}
.domain-info {
  display: flex;
  flex-direction: column;
}
.primary-domain {
  font-weight: 500;
  color: var(--color-text-1);
}
.aliases {
  margin-top: 4px;
}
.form-section {
  margin-bottom: 24px;
}
.section-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--color-text-1);
  margin-bottom: 16px;
  padding-left: 8px;
  border-left: 4px solid var(--color-primary-light-4);
}
.optimization-card {
  background: var(--color-fill-2);
  padding: 16px;
  border-radius: 8px;
  border: 1px solid var(--color-fill-3);
}
.opt-header {
  display: flex;
  align-items: center;
  margin-bottom: 8px;
  color: var(--color-success-6);
}
.opt-icon {
  font-size: 18px;
  margin-right: 8px;
}
.opt-title {
  font-weight: 600;
  font-size: 14px;
}
.opt-desc {
  margin: 0;
  font-size: 12px;
  color: var(--color-text-3);
  line-height: 1.6;
}
.confirm-tip.mini {
  padding: 10px 12px;
  background: var(--color-primary-light-1);
  color: var(--color-primary-6);
  border-radius: 4px;
  font-size: 12px;
  display: flex;
  align-items: center;
  gap: 8px;
}
</style>
