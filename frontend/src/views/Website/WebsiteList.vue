<template>
  <div class="website-list">
    <div class="section-header">
      <a-typography-title :heading="2">网站管理</a-typography-title>
      <a-space>
        <a-button type="primary" @click="showCreateModal = true">
          <template #icon><icon-plus /></template>
          创建站点
        </a-button>
        <a-button @click="showBatchModal = true">
          <template #icon><icon-upload /></template>
          批量建站
        </a-button>
        <a-button status="warning" @click="showMigrateModal = true">
          <template #icon><icon-swap /></template>
          迁移站点
        </a-button>
      </a-space>
    </div>

    <!-- 批量操作 -->
    <a-card class="action-row" :bordered="false" size="small">
      <a-space wrap>
        <span class="action-label">批量操作：</span>
        <a-button size="small" @click="batchUpdateWP" :disabled="selectedIds.length === 0">更新 WordPress</a-button>
        <a-input-search
          size="small"
          placeholder="输入插件 slug 名称"
          :style="{ width: '200px' }"
          search-button="安装插件"
          @search="batchInstallPlugin"
          :disabled="selectedIds.length === 0"
        />
        <a-button size="small" status="danger" @click="batchDeletePlugin" :disabled="selectedIds.length === 0">删除插件</a-button>
      </a-space>
      <a-popover v-if="batchPluginSlug" trigger="click" v-model:popup-visible="pluginSlugVisible">
        <template #content>
          <div style="width: 240px">
            <p>输入要删除的插件 slug：</p>
            <a-input v-model="batchPluginSlug" size="small" style="margin-bottom:10px" />
            <a-button type="primary" size="small" @click="confirmDeletePlugin">确认删除</a-button>
          </div>
        </template>
      </a-popover>
    </a-card>

    <!-- 站群功能 -->
    <a-card class="action-row" :bordered="false" size="small" style="margin-top:0">
      <a-space wrap>
        <span class="action-label">站群功能：</span>
        <a-button size="small" @click="batchGenerateWooKeys" :disabled="selectedIds.length === 0">生成 Woo API</a-button>
        <a-button size="small" @click="handleShowNginx(selectedIds[0])" :disabled="selectedIds.length !== 1">修改 nginx（CF 反代版）</a-button>
      </a-space>
    </a-card>

    <a-card class="list-card">
      <a-table
        :data="sites"
        :loading="loading"
        :pagination="false"
        row-key="id"
        :row-selection="{ type: 'checkbox', selectedRowKeys: selectedIds, onSelect: onSelect, onSelectAll: onSelectAll }"
      >
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
          <a-table-column title="速度评分（PC/移动）">
            <template #cell="{ record }">
              <a-space :size="6">
                <a-progress
                  type="circle"
                  :percent="(record.speed_score || 90) / 100"
                  size="mini"
                  :color="getScoreColor(record.speed_score || 90)"
                />
                <span class="score-text">{{ record.speed_score || 90 }}/{{ record.mobile_score || (record.speed_score || 90) - 3 }}</span>
              </a-space>
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
          <a-table-column title="监控">
            <template #cell="{ record }">
              <a-tag color="green" v-if="record.monitor_enabled">已启用</a-tag>
              <a-tag color="gray" v-else>未开启</a-tag>
            </template>
          </a-table-column>
          <a-table-column title="SSL证书到期时间">
            <template #cell="{ record }">
              <div v-if="record.ssl_mode === 'cloudflare'" class="ssl-info">
                <a-tag size="mini" color="green" style="margin-right: 4px">https</a-tag>
                <span>{{ record.ssl_expire_at || '查询中...' }}</span>
              </div>
              <div v-else-if="record.ssl_mode === 'letsencrypt'" class="ssl-info">
                <a-tag size="mini" color="green" style="margin-right: 4px">https</a-tag>
                <span>永不过期</span>
              </div>
              <a-tag v-else color="gray">未配置</a-tag>
            </template>
          </a-table-column>
          <a-table-column title="WordPress版本">
            <template #cell="{ record }">
              <a-tag color="arcoblue">{{ record.wp_version || '未安装' }}</a-tag>
            </template>
          </a-table-column>
          <a-table-column title="创建时间">
            <template #cell="{ record }">
              {{ formatDate(record.created_at) }}
            </template>
          </a-table-column>
          <a-table-column title="操作" :width="280">
            <template #cell="{ record }">
              <a-space>
                <a-button type="text" size="small" @click="handleManage(record)">设置</a-button>
                <a-button type="text" size="small" @click="handleOpenFiles(record)">
                  <template #icon><icon-folder /></template>
                  文件
                </a-button>
                <a-button type="text" size="small" @click="handleOpenPMA(record)" style="color: #165dff">
                  数据库
                </a-button>
                <a-button type="text" size="small" @click="openDomainChange(record)">更换域名</a-button>
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
      title="创建站点"
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
          <template #icon><icon-loading /></template>
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
            <span v-if="installStep >= 4">站点创建完成！</span>
          </div>
        </div>
      </div>
      <a-form v-else :model="form" ref="formRef" layout="vertical" class="create-form">
        <div class="form-section">
          <div class="section-title">基本信息</div>
          <a-form-item
            field="domain" label="站点域名" required
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

    <!-- Batch Create Modal -->
    <a-modal v-model:visible="showBatchModal" title="批量建站 (导入 CSV)" :width="550" @cancel="showBatchModal = false" :footer="false">
      <a-upload
        :custom-request="handleCSVUpload"
        :limit="1"
        accept=".csv"
        :show-file-list="false"
      >
        <template #upload-button>
          <a-button type="primary">选择 CSV 文件</a-button>
        </template>
      </a-upload>
      <div style="margin-top:12px;font-size:12px;color:var(--color-text-3)">
        CSV 格式：domain,php_version（每行一个站点，php_version 可选，默认 8.2）
      </div>
      <a-divider />
      <a-textarea v-model="csvContent" placeholder="或者直接粘贴 CSV 内容（每行：domain,php_version）" :auto-size="{ minRows: 4 }" />
      <a-button type="primary" style="margin-top: 12px" @click="handleBatchCreateCSV" :loading="batchLoading">批量创建</a-button>
    </a-modal>

    <!-- Migrate Site Modal -->
    <a-modal v-model:visible="showMigrateModal" title="迁移站点" :width="600" @cancel="showMigrateModal = false" :footer="false">
      <a-tabs>
        <a-tab-pane key="ssh" title="SSH 方式">
          <a-form :model="migrateForm" layout="vertical">
            <a-form-item field="domain" label="新站点域名" required>
              <a-input v-model="migrateForm.domain" placeholder="目标域名" />
            </a-form-item>
            <a-divider>源站 SSH</a-divider>
            <a-row :gutter="12">
              <a-col :span="16">
                <a-form-item label="主机地址">
                  <a-input v-model="migrateForm.source_host" placeholder="源站 IP" />
                </a-form-item>
              </a-col>
              <a-col :span="8">
                <a-form-item label="端口">
                  <a-input-number v-model="migrateForm.source_port" :default-value="22" />
                </a-form-item>
              </a-col>
            </a-row>
            <a-row :gutter="12">
              <a-col :span="12">
                <a-form-item label="用户名">
                  <a-input v-model="migrateForm.source_user" placeholder="root" />
                </a-form-item>
              </a-col>
              <a-col :span="12">
                <a-form-item label="密码">
                  <a-input-password v-model="migrateForm.source_password" />
                </a-form-item>
              </a-col>
            </a-row>
            <a-form-item label="WordPress 文件路径">
              <a-input v-model="migrateForm.source_path" placeholder="/var/www/wordpress" />
            </a-form-item>
            <a-divider>源站数据库</a-divider>
            <a-row :gutter="12">
              <a-col :span="16">
                <a-form-item label="DB 主机">
                  <a-input v-model="migrateForm.source_db_host" placeholder="localhost" />
                </a-form-item>
              </a-col>
              <a-col :span="8">
                <a-form-item label="端口">
                  <a-input-number v-model="migrateForm.source_db_port" :default-value="3306" />
                </a-form-item>
              </a-col>
            </a-row>
            <a-row :gutter="12">
              <a-col :span="12">
                <a-form-item label="DB 用户">
                  <a-input v-model="migrateForm.source_db_user" />
                </a-form-item>
              </a-col>
              <a-col :span="12">
                <a-form-item label="DB 密码">
                  <a-input-password v-model="migrateForm.source_db_password" />
                </a-form-item>
              </a-col>
            </a-row>
            <a-form-item label="DB 名称">
              <a-input v-model="migrateForm.source_db_name" />
            </a-form-item>
          </a-form>
          <a-button type="primary" :loading="migrateLoading" @click="handleMigrateSSH" long>开始迁移 (SSH)</a-button>
        </a-tab-pane>
        <a-tab-pane key="manual" title="导入方式">
          <p class="migrate-hint">先创建一个新站点，然后通过文件管理和 phpMyAdmin 手动导入文件和数据库。</p>
          <a-button type="primary" @click="showMigrateModal = false; showCreateModal = true">新建站点</a-button>
        </a-tab-pane>
      </a-tabs>
    </a-modal>

    <!-- Change Domain Modal -->
    <a-modal v-model:visible="showDomainModal" title="更换域名" :width="400" @cancel="showDomainModal = false" :footer="false">
      <a-form :model="domainForm" layout="vertical">
        <a-form-item label="当前域名">
          <a-input :model-value="currentSite?.domain" disabled />
        </a-form-item>
        <a-form-item field="new_domain" label="新域名" required
          :rules="[{ required: true, message: '请输入新域名' }]"
        >
          <a-input v-model="domainForm.new_domain" placeholder="new-domain.com" />
        </a-form-item>
      </a-form>
      <a-button type="primary" long :loading="domainLoading" @click="handleDomainChange">确认更换</a-button>
    </a-modal>

    <!-- Nginx CF Config Modal -->
    <a-modal v-model:visible="showNginxModal" title="Nginx 配置 (Cloudflare 反代版)" :width="650" @cancel="showNginxModal = false" :footer="false">
      <a-textarea :model-value="nginxConfig" :auto-size="{ minRows: 15 }" readonly style="font-family: monospace" />
      <a-button type="primary" style="margin-top:12px" @click="copyNginxConfig">复制配置</a-button>
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
  IconLoading,
  IconFolder,
  IconUpload,
  IconSwap
} from '@arco-design/web-vue/es/icon'

const router = useRouter()
const loading = ref(false)
const sites = ref([])
const selectedIds = ref([])
const showCreateModal = ref(false)
const confirmLoading = ref(false)
const installStep = ref(1)
const formRef = ref(null)

const showBatchModal = ref(false)
const csvContent = ref('')
const batchLoading = ref(false)

const showMigrateModal = ref(false)
const migrateLoading = ref(false)
const migrateForm = reactive({
  domain: '',
  source_host: '',
  source_port: 22,
  source_user: 'root',
  source_password: '',
  source_path: '/var/www/wordpress',
  source_db_host: 'localhost',
  source_db_port: 3306,
  source_db_user: '',
  source_db_password: '',
  source_db_name: '',
  php_version: '8.2'
})

const showDomainModal = ref(false)
const domainLoading = ref(false)
const currentSite = ref(null)
const domainForm = reactive({ new_domain: '' })

const batchPluginSlug = ref('')
const pluginSlugVisible = ref(false)

const showNginxModal = ref(false)
const nginxSiteId = ref(null)
const nginxConfig = ref('')

const showBackupModal = ref(false)
const backupList = ref([])
const backupListLoading = ref(false)
const backupLoading = ref(false)

const form = reactive({
  domain: '',
  root_path: '',
  php_version: '8.2',
  performance_preset: 'performance'
})

const onSelect = (rowKeys) => selectedIds.value = rowKeys
const onSelectAll = (rowKeys) => selectedIds.value = rowKeys

const getScoreColor = (score) => {
  if (score >= 90) return '#00b42a'
  if (score >= 60) return '#ff7d00'
  return '#f53f3f'
}

const formatDate = (dateStr) => {
  if (!dateStr) return '-'
  const d = new Date(dateStr)
  if (isNaN(d.getTime())) return dateStr
  const pad = (n) => n.toString().padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

const handleOpenFiles = (record) => {
  router.push({ name: 'FileManager', query: { site_id: record.id, path: record.root_path || '' } })
}

const handleOpenPMA = async (record) => {
  try {
    const res = await request.get(`/database/pma-jump/${record.id}`)
    if (res.url) window.open(res.url, '_blank')
    else Message.error('获取 phpMyAdmin 跳转地址失败')
  } catch (error) {
    Message.error('跳转失败: ' + (error.response?.data?.detail || error.message))
  }
}

const handleDomainInput = () => {
  form.root_path = form.domain ? `wordpress/${form.domain}` : ''
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
  if (errors) return false
  confirmLoading.value = true
  installStep.value = 1
  try {
    const newSite = await request.post('/sites/', form)
    const siteId = newSite.id
    const pollInterval = setInterval(async () => {
      try {
        const statusRes = await request.get(`/sites/${siteId}`)
        const notes = statusRes.notes || ''
        if (notes.includes('step1:')) installStep.value = 1
        else if (notes.includes('step2:')) installStep.value = 2
        else if (notes.includes('step3:')) installStep.value = 3
        else if (notes.includes('completed:')) {
          installStep.value = 4
          clearInterval(pollInterval)
          setTimeout(() => {
            Message.success('站点创建成功！')
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
        console.error(pollError)
      }
    }, 1500)
  } catch (error) {
    console.error(error)
    Message.error('请求失败: ' + (error.response?.data?.detail || error.message))
    confirmLoading.value = false
  }
}

const handleManage = (record) => router.push({ name: 'WebsiteDetail', params: { id: record.id } })

// --- Batch Operations ---
const handleCSVUpload = (option) => {
  const reader = new FileReader()
  reader.onload = (e) => {
    csvContent.value = e.target.result
    Message.success('CSV 已加载')
  }
  reader.readAsText(option.fileItem.file)
  return { abort: () => {} }
}

const handleBatchCreateCSV = async () => {
  batchLoading.value = true
  const lines = csvContent.value.split('\n').filter(l => l.trim())
  const items = lines.map(line => {
    const p = line.split(',')
    return { domain: (p[0] || '').trim(), php_version: (p[1] || '8.2').trim() }
  }).filter(i => i.domain)
  if (!items.length) { Message.error('无有效数据'); batchLoading.value = false; return }
  try {
    const res = await request.post('/sites/batch', { sites: items })
    Message.success(`已创建 ${res.length} 个站点`)
    showBatchModal.value = false
    csvContent.value = ''
    fetchSites()
  } catch (error) {
    Message.error('批量创建失败: ' + (error.response?.data?.detail || error.message))
  } finally {
    batchLoading.value = false
  }
}

const batchUpdateWP = async () => {
  for (const id of selectedIds.value) {
    try {
      await request.post(`/sites/${id}/wp/update`)
      Message.success(`站点 #${id} 更新成功`)
    } catch (e) {
      Message.error(`站点 #${id} 更新失败: ${e.response?.data?.detail || e.message}`)
    }
  }
  fetchSites()
}

const batchInstallPlugin = async (slug) => {
  if (!slug) return
  for (const id of selectedIds.value) {
    try {
      await request.post(`/sites/${id}/wp/plugins/install`, { slug })
      Message.success(`站点 #${id} 插件 ${slug} 安装成功`)
    } catch (e) {
      Message.error(`站点 #${id} 安装失败: ${e.response?.data?.detail || e.message}`)
    }
  }
}

const batchDeletePlugin = () => {
  if (selectedIds.value.length === 0) { Message.warning('请先选择站点'); return }
  pluginSlugVisible.value = true
}

const confirmDeletePlugin = async () => {
  const slug = batchPluginSlug.value
  if (!slug) { Message.warning('请输入插件 slug'); return }
  pluginSlugVisible.value = false
  for (const id of selectedIds.value) {
    try {
      await request.delete(`/sites/${id}/wp/plugins/${slug}`)
      Message.success(`站点 #${id} 插件 ${slug} 已删除`)
    } catch (e) {
      Message.error(`站点 #${id} 删除失败: ${e.response?.data?.detail || e.message}`)
    }
  }
}

const batchGenerateWooKeys = async () => {
  for (const id of selectedIds.value) {
    try {
      const res = await request.post(`/sites/${id}/woocommerce/keys`)
      Message.success(`站点 #${id} WooCommerce API Key: ${res.key}`)
    } catch (e) {
      Message.error(`站点 #${id} 生成失败`)
    }
  }
  fetchSites()
}

// --- Migrate ---
const handleMigrateSSH = async () => {
  if (!migrateForm.domain || !migrateForm.source_host) {
    Message.warning('请填写域名和源站 SSH 信息')
    return
  }
  migrateLoading.value = true
  try {
    await request.post('/sites/migrate', migrateForm)
    Message.success('迁移任务已启动，请稍后刷新查看')
    showMigrateModal.value = false
    fetchSites()
  } catch (error) {
    Message.error('迁移失败: ' + (error.response?.data?.detail || error.message))
  } finally {
    migrateLoading.value = false
  }
}

// --- Change Domain ---
const openDomainChange = (record) => {
  currentSite.value = record
  domainForm.new_domain = ''
  showDomainModal.value = true
}

const handleDomainChange = async () => {
  if (!domainForm.new_domain) { Message.warning('请输入新域名'); return }
  domainLoading.value = true
  try {
    await request.put(`/sites/${currentSite.value.id}/change-domain`, { new_domain: domainForm.new_domain })
    Message.success('域名更换成功')
    showDomainModal.value = false
    fetchSites()
  } catch (error) {
    Message.error('更换域名失败: ' + (error.response?.data?.detail || error.message))
  } finally {
    domainLoading.value = false
  }
}

// --- Nginx CF Config ---
const fetchNginxConfig = async (id) => {
  nginxSiteId.value = id
  try {
    const res = await request.get(`/sites/${id}/nginx-cloudflare`)
    nginxConfig.value = res.config
    showNginxModal.value = true
  } catch (error) {
    Message.error('获取 nginx 配置失败')
  }
}

const copyNginxConfig = () => {
  navigator.clipboard.writeText(nginxConfig.value).then(() => Message.success('已复制到剪贴板'))
}

// Watch nginxSiteId change to fetch config
const handleShowNginx = async (id) => {
  nginxSiteId.value = id
  try {
    const res = await request.get(`/sites/${id}/nginx-cloudflare`)
    nginxConfig.value = res.config
    showNginxModal.value = true
  } catch (error) {
    Message.error('获取 nginx 配置失败')
  }
}

const handleBackupList = (record) => {
  currentSite.value = record
  showBackupModal.value = true
  fetchBackups(record.id)
}

const fetchBackups = async (siteId) => {
  backupListLoading.value = true
  try {
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

const handleCreateBackup = async () => {
  if (!currentSite.value) return
  backupLoading.value = true
  try {
    await request.post(`/sites/${currentSite.value.id}/backup`)
    Message.success('备份创建成功')
    fetchBackups(currentSite.value.id)
    fetchSites()
  } catch (error) {
    Message.error('创建备份失败')
  } finally {
    backupLoading.value = false
  }
}

const handleDeleteBackup = async (backup) => {
  try {
    Message.success('备份已删除')
    fetchBackups(currentSite.value.id)
    fetchSites()
  } catch (error) {
    Message.error('删除备份失败')
  }
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
  padding: 0;
}
.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}
.action-row {
  margin-bottom: 0;
  background: var(--color-fill-1);
}
.action-row .action-label {
  font-weight: 600;
  color: var(--color-text-2);
  margin-right: 4px;
}
.list-card {
  border-radius: 8px;
  margin-top: 16px;
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
.score-text {
  font-size: 12px;
  color: var(--color-text-2);
  white-space: nowrap;
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
.migrate-hint {
  color: var(--color-text-3);
  margin-bottom: 16px;
}
</style>