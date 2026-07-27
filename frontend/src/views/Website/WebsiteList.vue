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
        <a-button size="small" @click="batchUpdateWP" :disabled="selectedIds.length === 0" :loading="batchWPUpdateLoading">更新 WordPress</a-button>
        <a-select
          v-model="batchInstallSlug"
          size="small"
          :style="{ width: '200px' }"
          placeholder="选择或输入插件 slug"
          :disabled="selectedIds.length === 0"
          allow-search
          allow-create
        >
          <a-option v-for="p in presetPlugins" :key="p.slug" :value="p.slug" :label="p.name" />
        </a-select>
        <a-button size="small" type="outline" @click="batchInstallPlugin" :disabled="selectedIds.length === 0 || !batchInstallSlug">安装</a-button>
        <a-popover trigger="manual" v-model:popup-visible="pluginSlugVisible">
          <a-button size="small" status="danger" @click="batchDeletePlugin" :disabled="selectedIds.length === 0">删除插件</a-button>
          <template #content>
            <div style="width: 240px">
              <p>输入要删除的插件 slug：</p>
              <a-input v-model="batchPluginSlug" size="small" style="margin-bottom:10px" />
              <a-button type="primary" size="small" @click="confirmDeletePlugin">确认删除</a-button>
            </div>
          </template>
        </a-popover>
      </a-space>
    </a-card>

    <!-- 站群功能 -->
    <a-card class="action-row" :bordered="false" size="small" style="margin-top:0">
      <a-space wrap>
        <span class="action-label">站群功能：</span>
        <a-button size="small" @click="batchGenerateWooKeys" :disabled="selectedIds.length === 0">生成 Woo API</a-button>
        <a-button size="small" @click="downloadWooKeysCSV">下载本页 Woo Key</a-button>
        <a-button size="small" @click="handleShowNginx(selectedIds[0])" :disabled="selectedIds.length !== 1">修改 nginx（CF 反代版）</a-button>
      </a-space>
    </a-card>

    <a-card class="list-card">
      <a-table
        :data="sites"
        :loading="loading"
        :pagination="pagination"
        :scroll="{ x: 1200 }"
        table-layout-fixed
        row-key="id"
        v-model:selected-keys="selectedIds"
        :row-selection="{ type: 'checkbox', showCheckedAll: true }"
        @selection-change="onSelectionChange"
      >
        <template #columns>
          <a-table-column title="域名" :width="200" ellipsis>
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

          <a-table-column title="状态" :width="100" >
            <template #cell="{ record }">
              <a-badge :status="getStatusBadge(record.status)" :text="getStatusText(record.status)" />
            </template>
          </a-table-column>
          <a-table-column title="速度（PC/移动）" :width="100">
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
          <a-table-column title="缓存状态" :width="100" >
            <template #cell="{ record }">
              <a-tag color="green" v-if="record.lscache_enabled">已开启 (四层)</a-tag>
              <a-tag color="gray" v-else>未开启</a-tag>
            </template>
          </a-table-column>
          <a-table-column title="备份" :width="100">
            <template #cell="{ record }">
              <a-link @click="handleBackupList(record)">
                {{ record.backup_count > 0 ? record.backup_count : '无备份' }}
              </a-link>
            </template>
          </a-table-column>
          <a-table-column title="监控" :width="100">
            <template #cell="{ record }">
              <a-tag color="green" v-if="record.monitor_enabled">已启用</a-tag>
              <a-tag color="gray" v-else>未开启</a-tag>
            </template>
          </a-table-column>
          <a-table-column title="SSL证书到期时间" :width="150">
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
          <a-table-column title="WordPress版本" :width="90" >
            <template #cell="{ record }">
              <a-tag color="arcoblue">{{ record.wp_version || '未安装' }}</a-tag>
            </template>
          </a-table-column>
          <a-table-column title="创建时间" :width="150">
            <template #cell="{ record }">
              {{ formatDate(record.created_at) }}
            </template>
          </a-table-column>
          <a-table-column title="操作" :width="360">
            <template #cell="{ record }">
              <div class="action-btns">
                <a-button type="text" size="small" @click="handleManage(record)">设置</a-button>
                <a-button type="text" size="small" @click="handleOpenFiles(record)">
                  文件
                </a-button>
                <a-button type="text" size="small" @click="handleOpenPMA(record)" style="color: #165dff">
                  数据库
                </a-button>
                <a-button type="text" size="small" @click="handleAIRepair(record)" style="color: #7b2ff7">
                  AI修复
                </a-button>
                <a-button type="text" size="small" @click="openDomainChange(record)">更换域名</a-button>
                <a-popconfirm content="确定要删除站点吗？此操作不可撤销！" @ok="handleDelete(record.id)" type="warning">
                  <a-button type="text" size="small" status="danger">删除</a-button>
                </a-popconfirm>
              </div>
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
            <a-row :gutter="12">
              <a-col :span="14">
                <a-input v-model="form.domain" placeholder="例如: example.com" @input="handleDomainInput" />
              </a-col>
              <a-col :span="10">
                <a-input-tag v-model="form.aliases" placeholder="别名: www.domain.com" allow-clear />
              </a-col>
            </a-row>
          </a-form-item>
          <a-row :gutter="12">
            <a-col :span="12">
              <a-form-item field="php_version" label="PHP 版本">
                <a-select v-model="form.php_version">
                  <a-option>8.2</a-option>
                  <a-option>8.1</a-option>
                  <a-option>7.4</a-option>
                </a-select>
              </a-form-item>
            </a-col>
            <a-col :span="12">
              <a-form-item label="数据库类型">
                <a-input placeholder="MariaDB" disabled />
              </a-form-item>
            </a-col>
          </a-row>
          <a-form-item field="root_path" label="根目录">
            <a-input v-model="form.root_path" placeholder="/var/www/html/域名" />
          </a-form-item>
          <a-form-item field="ssl_mode" label="SSL 模式">
            <a-radio-group v-model="form.ssl_mode" type="button">
              <a-radio value="cloudflare">Cloudflare</a-radio>
              <a-radio value="letsencrypt">面板自动申请</a-radio>
              <a-radio value="none">不配置 HTTPS</a-radio>
            </a-radio-group>
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
              <a-input v-model="migrateForm.source_path" placeholder="/var/www/html/wordpress" />
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
    <a-modal v-model:visible="showDomainModal" title="更换域名" :width="500" @cancel="onCancelDomainChange" :footer="false">
      <a-form :model="domainForm" layout="vertical">
        <a-form-item label="当前域名">
          <a-input :model-value="currentSite?.domain" disabled />
        </a-form-item>
        <a-form-item field="new_domain" label="新域名" required
          :rules="[{ required: true, message: '请输入新域名' }]"
        >
          <a-input v-model="domainForm.new_domain" placeholder="new-domain.com" :disabled="domainChanging" />
        </a-form-item>
      </a-form>
      <!-- Progress steps -->
      <div v-if="domainChanging" class="domain-progress">
        <div
          v-for="(step, idx) in domainSteps"
          :key="idx"
          class="domain-progress-step"
          :class="'status-' + step.status"
        >
          <span class="step-icon">
            <icon-loading v-if="step.status === 'running'" />
            <icon-check-circle v-else-if="step.status === 'done'" />
            <icon-close-circle v-else-if="step.status === 'failed'" />
            <span class="step-dot" v-else />
          </span>
          <span class="step-text">{{ step.name }}</span>
          <span class="step-msg">{{ step.message }}</span>
        </div>
      </div>
      <a-button
        v-if="!domainChanging"
        type="primary" long :loading="domainLoading" @click="handleDomainChange"
      >确认更换</a-button>
      <a-button
        v-if="domainChanging && domainDone"
        type="primary" long @click="onDomainChangeComplete"
      >完成</a-button>
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
                  <a-button type="text" size="small" @click="handleDownloadBackup(record)">下载</a-button>
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

    <!-- AI Repair Modal -->
    <a-modal
      v-model:visible="showAIRepairModal"
      title="AI 一键修复"
      :width="900"
      :mask-closable="false"
      @cancel="handleAIRepairClose"
    >
      <div class="ai-repair-body">
        <div v-if="!aiAnalysis && !aiRepairLoading" class="ai-empty">
          <p>点击下方按钮，AI 将对站点进行全面诊断分析。</p>
        </div>
        <a-row v-else :gutter="16">
          <a-col :span="12">
            <div class="ai-repair-log" ref="aiRepairLogRef">
              <div v-if="(aiRepairLoading || aiExecLoading) && aiProcessLog.length === 0" class="ai-loading">
                <a-spin />
                <span style="margin-left: 8px">正在初始化...</span>
              </div>
              <div v-for="(item, i) in aiProcessLog" :key="i" class="ai-log-line">
                <span v-if="item.startsWith('[★]')" class="ai-log-cmd">{{ item }}</span>
                <span v-else>{{ item }}</span>
              </div>
            </div>
          </a-col>
          <a-col :span="12">
            <div v-if="aiAnalysis" class="ai-analysis" v-html="aiAnalysisHtml" />
          </a-col>
        </a-row>
      </div>
      <template #footer>
        <a-space>
          <a-button @click="showAIRepairModal = false">关闭</a-button>
          <a-button
            v-if="!aiAnalysis"
            type="primary"
            @click="handleAIStartDiagnose"
            :loading="aiRepairLoading"
            :disabled="aiRepairLoading"
          >
            AI 一键检测
          </a-button>
          <a-button
            v-if="aiAnalysis"
            type="primary"
            status="success"
            @click="handleAIRepairExecute"
            :loading="aiExecLoading"
            :disabled="aiExecLoading"
          >
            执行修复
          </a-button>
        </a-space>
      </template>
    </a-modal>

    <!-- Batch Task Progress Modal -->
    <a-modal
      v-model:visible="showBatchTaskModal"
      :title="batchTaskTitle"
      :width="600"
      :mask-closable="false"
      :footer="false"
    >
      <div class="ai-repair-log" ref="batchTaskLogRef" style="height: 400px">
        <div v-if="batchTaskLoading && batchTaskLog.length === 0" class="ai-loading">
          <a-spin />
          <span style="margin-left: 8px">正在执行...</span>
        </div>
        <div v-for="(item, i) in batchTaskLog" :key="i" class="ai-log-line">
          <span :class="{ 'ai-log-success': item.includes('成功'), 'ai-log-error': item.includes('失败') }">{{ item }}</span>
        </div>
      </div>
      <div v-if="!batchTaskLoading && batchTaskLog.length > 0" style="margin-top: 12px; text-align: right">
        <a-button type="primary" @click="showBatchTaskModal = false">关闭</a-button>
      </div>
    </a-modal>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import request from '@/utils/request'
import { Message, Modal } from '@arco-design/web-vue'
import {
  IconPlus,
  IconMore,
  IconInfoCircle,
  IconCheckCircleFill,
  IconCheckCircle,
  IconCloseCircle,
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
const batchWPUpdateLoading = ref(false)

const showAIRepairModal = ref(false)
const aiRepairLoading = ref(false)
const aiExecLoading = ref(false)
const aiProcessLog = ref([])
const aiAnalysis = ref('')
const aiRepairLogRef = ref(null)
const aiCurrentSite = ref(null)

const showMigrateModal = ref(false)
const migrateLoading = ref(false)
const migrateForm = reactive({
  domain: '',
  source_host: '',
  source_port: 22,
  source_user: 'root',
  source_password: '',
  source_path: '/var/www/html/wordpress',
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
const domainChanging = ref(false)
const domainDone = ref(false)
const domainSteps = ref([])
let domainPollTimer = null

const batchPluginSlug = ref('')
const pluginSlugVisible = ref(false)
const batchInstallSlug = ref('')

const showBatchTaskModal = ref(false)
const batchTaskTitle = ref('')
const batchTaskLog = ref([])
const batchTaskLoading = ref(false)
const batchTaskLogRef = ref(null)

const presetPlugins = [
  { slug: 'litespeed-cache', name: 'LiteSpeed Cache' },
  { slug: 'wordfence', name: 'Wordfence Security' },
  { slug: 'wordpress-seo', name: 'Yoast SEO' },
  { slug: 'woocommerce', name: 'WooCommerce' },
  { slug: 'contact-form-7', name: 'Contact Form 7' },
  { slug: 'akismet', name: 'Akismet Anti-Spam' },
  { slug: 'elementor', name: 'Elementor' },
  { slug: 'updraftplus', name: 'UpdraftPlus Backup' },
  { slug: 'wp-optimize', name: 'WP-Optimize' },
  { slug: 'really-simple-ssl', name: 'Really Simple SSL' },
  { slug: 'wp-rocket', name: 'WP Rocket' },
  { slug: 'rank-math', name: 'Rank Math SEO' },
  { slug: 'imagify', name: 'Imagify' },
  { slug: 'redirection', name: 'Redirection' },
  { slug: 'wp-mail-smtp', name: 'WP Mail SMTP' },
]

const showNginxModal = ref(false)
const nginxSiteId = ref(null)
const nginxConfig = ref('')

const showBackupModal = ref(false)
const backupList = ref([])
const backupListLoading = ref(false)
const backupLoading = ref(false)

const form = reactive({
  domain: '',
  aliases: [],
  root_path: '/var/www/html/',
  php_version: '8.2',
  ssl_mode: 'cloudflare',
  performance_preset: 'performance'
})

const onSelectionChange = (rowKeys) => {
  selectedIds.value = rowKeys
}

const pagination = {
  pageSize: 10,
  pageSizeOptions: [10, 100, 500],
  showTotal: (total) => `共 ${total} 站点`,
  showPageSize: true,
}

const getScoreColor = (score) => {
  if (score >= 90) return '#00b42a'
  if (score >= 60) return '#ff7d00'
  return '#f53f3f'
}

const getStatusBadge = (status) => {
  if (status === 'active') return 'success'
  if (status === 'creating') return 'processing'
  return 'danger'
}

const getStatusText = (status) => {
  if (status === 'active') return '运行中'
  if (status === 'creating') return '创建中'
  return '已停止'
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

const handleAIRepair = (record) => {
  showAIRepairModal.value = true
  aiProcessLog.value = []
  aiAnalysis.value = ''
  aiRepairLoading.value = false
  aiExecLoading.value = false
  aiCurrentSite.value = record
}

const handleAIStartDiagnose = async () => {
  if (!aiCurrentSite.value) return
  aiRepairLoading.value = true
  aiProcessLog.value = []
  aiAnalysis.value = ''
  try {
    const res = await request.post(`/sites/${aiCurrentSite.value.id}/ai-repair`, {}, { timeout: 300000 })
    aiProcessLog.value = res.process_log || []
    aiAnalysis.value = res.ai_analysis || ''
  } catch (error) {
    aiProcessLog.value.push('检测失败: ' + (error.response?.data?.detail || error.message))
  } finally {
    aiRepairLoading.value = false
    nextTick(() => {
      if (aiRepairLogRef.value) {
        aiRepairLogRef.value.scrollTop = aiRepairLogRef.value.scrollHeight
      }
    })
  }
}

const handleAIRepairExecute = async () => {
  if (!aiCurrentSite.value || !aiAnalysis.value) return
  aiExecLoading.value = true
  aiProcessLog.value = []
  try {
    const res = await request.post(
      `/sites/${aiCurrentSite.value.id}/ai-repair/execute`,
      { ai_analysis: aiAnalysis.value },
      { timeout: 300000 }
    )
    aiProcessLog.value = res.process_log || []
  } catch (error) {
    aiProcessLog.value.push('执行失败: ' + (error.response?.data?.detail || error.message))
  } finally {
    aiExecLoading.value = false
    nextTick(() => {
      if (aiRepairLogRef.value) {
        aiRepairLogRef.value.scrollTop = aiRepairLogRef.value.scrollHeight
      }
    })
  }
}

const handleAIRepairClose = () => {
  showAIRepairModal.value = false
  aiProcessLog.value = []
  aiAnalysis.value = ''
  aiCurrentSite.value = null
}

const aiAnalysisHtml = computed(() => {
  if (!aiAnalysis.value) return ''
  return aiAnalysis.value
    .replace(/### (.+)/g, '<h3>$1</h3>')
    .replace(/## (.+)/g, '<h2>$1</h2>')
    .replace(/# (.+)/g, '<h1>$1</h1>')
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    .replace(/^- (.+)/gm, '<li>$1</li>')
    .replace(/(<li>[\s\S]*?<\/li>)/g, (match) => `<ul>${match}</ul>`)
    .replace(/\n/g, '<br>')
})

const handleDomainInput = () => {
  form.root_path = form.domain ? `/var/www/html/${form.domain}` : '/var/www/html/'
  if (form.domain && !form.aliases.length) {
    form.aliases = [`www.${form.domain}`]
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
  if (errors) return false
  confirmLoading.value = true
  installStep.value = 1
  try {
    const newSite = await request.post('/sites/', form)
    const siteId = newSite.id
    // Use raw axios for polling (no error interceptor)
    const { default: axios } = await import('axios')
    const poll = axios.create({ baseURL: '/api/v1', timeout: 30000 })
    const token = localStorage.getItem('token')
    const pollInterval = setInterval(async () => {
      try {
        const { data } = await poll.get(`/sites/${siteId}`, {
          headers: token ? { Authorization: `Bearer ${token}` } : {},
        })
        const notes = data.notes || ''
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
        // Poll silently
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
  batchTaskTitle.value = '批量更新 WordPress'
  batchTaskLog.value = []
  batchTaskLoading.value = true
  showBatchTaskModal.value = true
  batchWPUpdateLoading.value = true
  for (const id of selectedIds.value) {
    try {
      batchTaskLog.value.push(`站点 #${id} 正在更新 WordPress...`)
      await request.post(`/sites/${id}/wp/update`, {}, { timeout: 130000 })
      batchTaskLog.value.push(`站点 #${id} 更新成功 ✓`)
    } catch (e) {
      batchTaskLog.value.push(`站点 #${id} 更新失败: ${e.response?.data?.detail || e.message}`)
    }
  }
  fetchSites()
  batchWPUpdateLoading.value = false
  batchTaskLoading.value = false
}

const batchInstallPlugin = async () => {
  const slug = batchInstallSlug.value
  if (!slug) return
  batchTaskTitle.value = `批量安装插件: ${slug}`
  batchTaskLog.value = []
  batchTaskLoading.value = true
  showBatchTaskModal.value = true
  for (const id of selectedIds.value) {
    try {
      batchTaskLog.value.push(`站点 #${id} 正在安装 ${slug}...`)
      await request.post(`/sites/${id}/wp/plugins/install`, { slug }, { timeout: 60000 })
      batchTaskLog.value.push(`站点 #${id} 安装成功 ✓`)
    } catch (e) {
      batchTaskLog.value.push(`站点 #${id} 安装失败: ${e.response?.data?.detail || e.message}`)
    }
  }
  batchTaskLoading.value = false
}

const batchDeletePlugin = () => {
  if (selectedIds.value.length === 0) { Message.warning('请先选择站点'); return }
  pluginSlugVisible.value = true
}

const confirmDeletePlugin = async () => {
  const slug = batchPluginSlug.value
  if (!slug) { Message.warning('请输入插件 slug'); return }
  pluginSlugVisible.value = false
  batchTaskTitle.value = `批量删除插件: ${slug}`
  batchTaskLog.value = []
  batchTaskLoading.value = true
  showBatchTaskModal.value = true
  for (const id of selectedIds.value) {
    try {
      batchTaskLog.value.push(`站点 #${id} 正在停用 ${slug}...`)
      batchTaskLog.value.push(`站点 #${id} 正在删除 ${slug}...`)
      await request.delete(`/sites/${id}/wp/plugins/${slug}`, { timeout: 150000 })
      batchTaskLog.value.push(`站点 #${id} 删除成功 ✓`)
    } catch (e) {
      batchTaskLog.value.push(`站点 #${id} 删除失败: ${e.response?.data?.detail || e.message}`)
    }
  }
  batchTaskLoading.value = false
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

const downloadWooKeysCSV = () => {
  const header = '\uFEFFID,Domain,WooCommerce Key,WooCommerce Secret'
  const rows = sites.value
    .filter(s => s.wc_key || s.wc_secret)
    .map(s => {
      const escape = (v) => `"${(v || '').replace(/"/g, '""')}"`
      return `${s.id},${escape(s.domain)},${escape(s.wc_key)},${escape(s.wc_secret)}`
    })
  if (rows.length === 0) {
    Message.warning('本页没有可下载的 WooCommerce Key')
    return
  }
  const csv = [header, ...rows].join('\n')
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8' })
  const url = window.URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `woocommerce-keys-${new Date().toISOString().split('T')[0]}.csv`
  a.click()
  window.URL.revokeObjectURL(url)
  Message.success(`已导出 ${rows.length} 条记录`)
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
  domainChanging.value = false
  domainDone.value = false
  domainSteps.value = []
  showDomainModal.value = true
}

const onCancelDomainChange = () => {
  if (domainChanging.value && !domainDone.value) return
  stopDomainPolling()
  showDomainModal.value = false
}

const stopDomainPolling = () => {
  if (domainPollTimer) {
    clearInterval(domainPollTimer)
    domainPollTimer = null
  }
}

const onDomainChangeComplete = () => {
  stopDomainPolling()
  showDomainModal.value = false
  domainChanging.value = false
  domainDone.value = false
  fetchSites()
}

const handleDomainChange = async () => {
  if (!domainForm.new_domain) { Message.warning('请输入新域名'); return }
  domainLoading.value = true
  try {
    const res = await request.put(`/sites/${currentSite.value.id}/change-domain`, { new_domain: domainForm.new_domain })
    const taskId = res.task_id
    domainChanging.value = true
    domainLoading.value = false
    domainDone.value = false

    const { default: axios } = await import('axios')
    const poll = axios.create({ baseURL: '/api/v1', timeout: 15000 })

    domainPollTimer = setInterval(async () => {
      try {
        const token = localStorage.getItem('token')
        const { data } = await poll.get(`/sites/change-domain/${taskId}/progress`, {
          headers: token ? { Authorization: `Bearer ${token}` } : {},
        })
        domainSteps.value = data.steps || []
        if (data.done) {
          stopDomainPolling()
          domainDone.value = true
          if (data.result?.error) {
            Message.error(data.result.error)
          } else if (data.result?.success) {
            Message.success('域名更换完成')
          }
        }
      } catch (e) {
        // Poll silently, don't show error toasts
      }
    }, 2000)
  } catch (error) {
    domainLoading.value = false
    Message.error('更换域名失败: ' + (error.response?.data?.detail || error.message))
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
    const res = await request.get(`/sites/${siteId}/backups`)
    backupList.value = res.map(b => ({
      ...b,
      size: formatFileSize(b.file_size)
    }))
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
    await request.post(`/sites/${currentSite.value.id}/backup`, {}, { timeout: 300000 })
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
    await request.delete(`/sites/${currentSite.value.id}/backups/${backup.id}`)
    Message.success('备份已删除')
    fetchBackups(currentSite.value.id)
    fetchSites()
  } catch (error) {
    Message.error('删除备份失败')
  }
}

const handleDownloadBackup = async (backup) => {
  try {
    const blob = await request.get(`/sites/${currentSite.value.id}/backups/${backup.id}/download`, {
      responseType: 'blob'
    })
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = backup.name
    a.click()
    window.URL.revokeObjectURL(url)
  } catch (error) {
    Message.error('下载失败')
  }
}

const formatFileSize = (bytes) => {
  if (!bytes || bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i]
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
    aliases: [],
    root_path: '/var/www/html/',
    php_version: '8.2',
    ssl_mode: 'cloudflare',
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
.action-btns {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}
.action-btns .arco-btn-text {
  padding: 2px 6px;
  line-height: 1.4;
  white-space: nowrap;
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

/* Domain change progress */
.domain-progress {
  margin: 16px 0;
}
.domain-progress-step {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 0;
  font-size: 13px;
}
.step-icon {
  display: flex;
  align-items: center;
  font-size: 16px;
  width: 20px;
  flex-shrink: 0;
}
.step-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--color-fill-3);
  display: inline-block;
  margin-left: 4px;
}
.status-running .step-icon {
  color: var(--color-primary-6);
  animation: arco-loading-circle 1s linear infinite;
}
.status-done .step-icon {
  color: #00b42a;
}
.status-failed .step-icon {
  color: #f53f3f;
}
.status-running .step-text {
  color: var(--color-primary-6);
  font-weight: 500;
}
.status-done .step-text {
  color: #00b42a;
}
.status-failed .step-text {
  color: #f53f3f;
}
.step-msg {
  display: block;
  width: 100%;
  font-size: 11px;
  color: var(--color-text-3);
  word-break: break-all;
}

.ai-repair-body {
  min-height: 320px;
}

.ai-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 200px;
  color: #86909c;
  font-size: 14px;
}

.ai-repair-log {
  background: #1d2129;
  border-radius: 4px;
  padding: 12px;
  height: 450px;
  overflow-y: auto;
  font-family: 'Courier New', Courier, monospace;
  font-size: 12px;
  line-height: 1.6;
  color: #a8c97e;
}

.ai-log-line {
  white-space: pre-wrap;
  word-break: break-all;
}

.ai-loading {
  display: flex;
  align-items: center;
  color: #86909c;
}

.ai-analysis {
  background: #f7f8fa;
  border-radius: 4px;
  padding: 16px;
  height: 450px;
  overflow-y: auto;
  font-size: 13px;
  line-height: 1.8;
  color: #1d2129;
}

.ai-analysis :deep(h1) { font-size: 18px; margin: 8px 0; }
.ai-analysis :deep(h2) { font-size: 16px; margin: 8px 0; }
.ai-analysis :deep(h3) { font-size: 14px; margin: 6px 0; }
.ai-analysis :deep(strong) { color: #1d2129; }
.ai-analysis :deep(code) { background: #e5e6eb; padding: 1px 6px; border-radius: 3px; font-size: 12px; }
.ai-analysis :deep(li) { margin-left: 16px; }
.ai-analysis :deep(ul) { margin: 4px 0; }

.ai-log-cmd {
  color: #ffb020;
  font-weight: bold;
}

.ai-log-success {
  color: #a8c97e;
}

.ai-log-error {
  color: #f76965;
}
</style>