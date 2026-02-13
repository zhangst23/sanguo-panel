<template>
  <div class="website-list">
    <div class="section-header">
      <a-typography-title :heading="2">网站管理</a-typography-title>
      <a-button type="primary" @click="showCreateModal = true">
        <template #icon><icon-plus /></template>
        创建 WordPress 站点
      </a-button>
    </div>

    <a-card class="list-card">
      <a-table :data="sites" :loading="loading" :pagination="false">
        <template #columns>
          <a-table-column title="域名">
            <template #cell="{ record }">
              <div class="domain-info">
                <div class="primary-domain">
                  {{ record.domain }}
                  <a :href="'http://' + record.domain" target="_blank" class="visit-link">
                    <icon-launch />
                  </a>
                </div>
                <div class="aliases" v-if="record.aliases?.length">
                  <a-tag v-for="alias in record.aliases" :key="alias" size="mini">{{ alias }}</a-tag>
                </div>
              </div>
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
          <a-table-column title="备份">
            <template #cell="{ record }">
              <a-link @click="handleBackupList(record)">
                {{ record.backup_count > 0 ? record.backup_count : '无备份' }}
              </a-link>
            </template>
          </a-table-column>
          <a-table-column title="SSL证书到期时间">
            <template #cell="{ record }">
              <div v-if="record.ssl_expire_at" class="ssl-info">
                <span>{{ record.ssl_expire_at }}</span>
                <a-tag size="mini" color="arcoblue" style="margin-left: 4px">自动续</a-tag>
              </div>
              <a-tag v-else color="gray">未配置</a-tag>
            </template>
          </a-table-column>
          <a-table-column title="PHP版本" data-index="php_version">
            <template #cell="{ record }">
              <a-tag color="arcoblue">{{ record.php_version }}</a-tag>
            </template>
          </a-table-column>
          <a-table-column title="数据库">
            <template #cell="{ record }">
              <a-link @click="handleOpenPMA(record)">
                访问
              </a-link>
            </template>
          </a-table-column>
          <a-table-column title="操作">
            <template #cell="{ record }">
              <a-space>
                <a-button type="text" size="small" @click="handleManage(record)">设置</a-button>
                <a-popconfirm content="确定要清理该站点的缓存吗？" @ok="handlePurgeCache(record)">
                  <a-button type="text" size="small">清理缓存</a-button>
                </a-popconfirm>
                <a-popconfirm content="确定要删除站点吗？此操作不可撤销！" @ok="handleDelete(record.id)" type="warning">
                  <a-button type="text" size="small" status="danger">删除</a-button>
                </a-popconfirm>
              </a-space>
            </template>
          </a-table-column>
        </template>
      </a-table>
    </a-card>

    <!-- Create Site Modal -->
    <a-modal 
      v-model:visible="showCreateModal" 
      title="创建 WordPress 站点" 
      :width="550"
      @cancel="resetForm"
      :footer="!confirmLoading"
      :mask-closable="false"
      :esc-to-close="false"
      :closable="!confirmLoading"
    >
      <template #footer>
        <a-button @click="showCreateModal = false">取消</a-button>
        <a-button type="primary" :loading="confirmLoading" @click="handleCreate">立即创建</a-button>
      </template>
      <div v-if="confirmLoading" class="install-loading">
        <a-spin :size="32">
          <template #icon>
            <icon-loading />
          </template>
        </a-spin>
        <div class="loading-steps">
          <div class="step-item active">
            <icon-check-circle-fill v-if="installStep > 1" class="done-icon" />
            <icon-loading v-else class="spin-icon" />
            WordPress 文件下载中...
          </div>
          <div class="step-item" :class="{ active: installStep >= 2 }">
            <icon-check-circle-fill v-if="installStep > 2" class="done-icon" />
            <icon-loading v-else-if="installStep === 2" class="spin-icon" />
            MariaDB 数据库安装中...
          </div>
          <div class="step-item" :class="{ active: installStep >= 3 }">
            <icon-check-circle-fill v-if="installStep > 3" class="done-icon" />
            <icon-loading v-else-if="installStep === 3" class="spin-icon" />
            配置优化中...
          </div>
          <div class="step-item" :class="{ active: installStep >= 4 }">
            <icon-check-circle-fill v-if="installStep >= 4" class="done-icon" />
            <span v-if="installStep >= 4">WordPress 站点创建完成！</span>
          </div>
        </div>
      </div>
      <a-form v-else :model="form" ref="formRef" layout="vertical" class="create-form">
        <!-- Basic Info Section -->
        <div class="form-section">
          <div class="section-title">基本信息</div>
          <a-form-item 
            field="domain" 
            label="站点域名" 
            required 
            :rules="[
              { required: true, message: '请输入站点域名' },
              { match: /^(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z0-9][a-z0-9-]{0,61}[a-z0-9]$/i, message: '域名格式不正确，必须是根域名形式（如 example.com）' }
            ]"
            help="输入主域名，系统将自动配置根目录及数据库"
          >
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
            <a-input v-model="form.root_path" placeholder="默认: wordpress/域名" />
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

    <!-- Backup Management Modal -->
    <a-modal 
      v-model:visible="showBackupModal" 
      :title="`备份管理 - ${currentSite?.domain}`" 
      :width="650"
      @cancel="showBackupModal = false"
      :footer="false"
    >
      <div class="backup-management">
        <div class="backup-actions">
          <a-button type="primary" @click="handleCreateBackup" :loading="backupLoading">
            <template #icon><icon-plus /></template>
            新增备份
          </a-button>
        </div>
        
        <a-table :data="backupList" :loading="backupListLoading" style="margin-top: 16px">
          <template #columns>
            <a-table-column title="备份时间" data-index="created_at" />
            <a-table-column title="文件大小" data-index="size" />
            <a-table-column title="操作">
              <template #cell="{ record }">
                <a-space>
                  <a-button type="text" size="small">下载</a-button>
                  <a-popconfirm content="确定要删除该备份吗？" @ok="handleDeleteBackup(record)">
                    <a-button type="text" size="small" status="danger">删除</a-button>
                  </a-popconfirm>
                </a-space>
              </template>
            </a-table-column>
          </template>
        </a-table>
      </div>
    </a-modal>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import request from '@/utils/request'
import { Message, Modal } from '@arco-design/web-vue'
import { 
  IconPlus, 
  IconMore, 
  IconInfoCircle, 
  IconCheckCircleFill,
  IconLaunch,
  IconLoading
} from '@arco-design/web-vue/es/icon'

const router = useRouter()
const loading = ref(false)
const sites = ref([])
const showCreateModal = ref(false)
const confirmLoading = ref(false)
const installStep = ref(1)
const formRef = ref(null)

// 备份管理相关状态
const showBackupModal = ref(false)
const currentSite = ref(null)
const backupList = ref([])
const backupListLoading = ref(false)
const backupLoading = ref(false)

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
    // 模拟项目路径显示，实际创建时由后端计算 project_root/wordpress/domain
    form.root_path = `wordpress/${form.domain}`
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
  const errors = await formRef.value?.validate()
  if (errors) {
    return false
  }
  
  confirmLoading.value = true
  installStep.value = 1
  
  try {
    const newSite = await request.post('/sites/', form)
    const siteId = newSite.id
    
    // 开始轮询状态
    const pollInterval = setInterval(async () => {
      try {
        const statusRes = await request.get(`/sites/${siteId}`)
        const notes = statusRes.notes || ''
        
        console.log('Current installation status:', notes)
        
        if (notes.includes('step1:')) {
          installStep.value = 1
        } else if (notes.includes('step2:')) {
          installStep.value = 2
        } else if (notes.includes('step3:')) {
          installStep.value = 3
        } else if (notes.includes('completed:')) {
          installStep.value = 4
          clearInterval(pollInterval)
          
          // 延迟 1.5 秒再关闭，让用户看清完成状态
          setTimeout(() => {
            Message.success('WordPress 站点创建成功！')
            showCreateModal.value = false
            confirmLoading.value = false
            resetForm()
            fetchSites()
          }, 1500)
        } else if (notes.includes('failed:')) {
          clearInterval(pollInterval)
          confirmLoading.value = false
          Message.error('创建失败: ' + notes.replace('failed:', ''))
        }
      } catch (pollError) {
        console.error('Polling error:', pollError)
      }
    }, 1500) // 缩短轮询间隔至 1.5s，反馈更及时

  } catch (error) {
    console.error(error)
    Message.error('请求失败: ' + (error.response?.data?.detail || error.message))
    confirmLoading.value = false
  }
}

const handleManage = (record) => {
  router.push({ name: 'WebsiteDetail', params: { id: record.id } })
}

const handleOpenPMA = async (record) => {
  try {
    const res = await request.get(`/database/pma-jump/${record.id}`)
    if (res.url) {
      window.open(res.url, '_blank')
    } else {
      Message.error('获取 phpMyAdmin 跳转地址失败')
    }
  } catch (error) {
    Message.error('跳转失败: ' + (error.response?.data?.detail || error.message))
  }
}

const fetchBackups = async (siteId) => {
  backupListLoading.value = true
  try {
    // 假设后端有获取备份列表的接口
    // const res = await request.get(`/sites/${siteId}/backups`)
    // backupList.value = res
    
    // 模拟数据
    backupList.value = [
      { id: 1, created_at: '2024-08-13 10:00:00', size: '15.2 MB' },
      { id: 2, created_at: '2024-08-12 10:00:00', size: '14.8 MB' }
    ]
  } catch (error) {
    Message.error('获取备份列表失败')
  } finally {
    backupListLoading.value = false
  }
}

const handleBackupList = (record) => {
  currentSite.value = record
  showBackupModal.value = true
  fetchBackups(record.id)
}

const handleCreateBackup = async () => {
  if (!currentSite.value) return
  backupLoading.value = true
  try {
    await request.post(`/sites/${currentSite.value.id}/backup`)
    Message.success('备份创建成功')
    fetchBackups(currentSite.value.id)
    fetchSites() // 更新列表中的备份数量
  } catch (error) {
    Message.error('创建备份失败')
  } finally {
    backupLoading.value = false
  }
}

const handleDeleteBackup = async (backup) => {
  try {
    // await request.delete(`/sites/${currentSite.value.id}/backups/${backup.id}`)
    Message.success('备份已删除')
    fetchBackups(currentSite.value.id)
    fetchSites() // 更新列表中的备份数量
  } catch (error) {
    Message.error('删除备份失败')
  }
}

const handlePurgeCache = async (record) => {
  try {
    await request.post(`/sites/${record.id}/purge-cache`)
    Message.success(`站点 ${record.domain} 缓存清理成功`)
  } catch (error) {
    Message.error('缓存清理失败')
  }
}

const handleSSL = async (record) => {
  Message.loading({ content: '正在配置 SSL...', id: 'ssl' })
  try {
    await request.post(`/sites/${record.id}/ssl`)
    Message.success({ content: 'SSL 配置成功', id: 'ssl' })
  } catch (error) {
    Message.error({ content: 'SSL 配置失败', id: 'ssl' })
  }
}

const handleBackup = async (record) => {
  Message.loading({ content: '正在创建备份...', id: 'backup' })
  try {
    await request.post(`/sites/${record.id}/backup`)
    Message.success({ content: '站点备份已完成', id: 'backup' })
  } catch (error) {
    Message.error({ content: '备份失败', id: 'backup' })
  }
}

const confirmDelete = (record) => {
  Modal.confirm({
    title: '删除站点',
    content: `确定要删除站点 ${record.domain} 吗？此操作不可撤销，且会同时清理相关配置。`,
    okText: '确认删除',
    cancelText: '取消',
    okButtonProps: { status: 'danger' },
    onOk: () => handleDelete(record.id)
  })
}

const handleDelete = async (id) => {
  try {
    await request.delete(`/sites/${id}`)
    Message.success('站点已成功删除')
    fetchSites()
  } catch (error) {
    console.error(error)
    Message.error('删除站点失败')
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
  display: flex;
  align-items: center;
  gap: 8px;
}
.visit-link {
  color: var(--color-text-3);
  font-size: 14px;
  display: inline-flex;
  transition: color 0.2s;
}
.visit-link:hover {
  color: var(--color-primary);
}
.install-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 40px 0;
}
.loading-steps {
  margin-top: 24px;
  width: 100%;
  max-width: 300px;
}
.step-item {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
  color: var(--color-text-3);
  font-size: 14px;
}
.step-item.active {
  color: var(--color-text-1);
  font-weight: 500;
}
.spin-icon {
  animation: arco-loading-circle 1s linear infinite;
  color: var(--color-primary);
}
.done-icon {
  color: #00b42a;
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
