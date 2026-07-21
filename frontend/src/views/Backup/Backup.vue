<template>
  <div class="backup-container">
    <a-typography-title :heading="2">备份与迁移</a-typography-title>

    <a-tabs v-model:active-key="activeTab">
      <!-- 备份记录标签页 -->
      <a-tab-pane key="records" title="备份管理">
        <a-row :gutter="20">
          <a-col :span="16">
            <a-card>
              <template #title>
                <a-space size="large">
                  <a-button type="primary" @click="handleOpenManualModal">
                    <template #icon><icon-plus /></template>
                    创建手动备份
                  </a-button>
                  <a-typography-text type="secondary">
                    备份文件目录：<a-typography-text code>backup</a-typography-text>
                  </a-typography-text>
                </a-space>
              </template>
              <a-table :data="backups" :loading="loading.fetch">
                <template #columns>
                  <a-table-column title="文件名" data-index="name" />
                  <a-table-column title="大小" data-index="file_size">
                    <template #cell="{ record }">
                      {{ (record.file_size / 1024 / 1024).toFixed(2) }} MB
                    </template>
                  </a-table-column>
                  <a-table-column title="状态" data-index="status">
                    <template #cell="{ record }">
                      <a-tag :color="record.status === 'success' ? 'green' : 'red'">
                        {{ record.status }}
                      </a-tag>
                    </template>
                  </a-table-column>
                  <a-table-column title="创建时间" data-index="created_at" />
                  <a-table-column title="操作">
                    <template #cell="{ record }">
                      <a-space>
                        <a-button type="text" size="small" @click="handleDownload(record)">下载</a-button>
                        <a-button type="text" size="small" status="success" @click="handleRestore(record)">恢复</a-button>
                        <a-button type="text" size="small" status="danger" @click="handleDelete(record)">删除</a-button>
                      </a-space>
                    </template>
                  </a-table-column>
                </template>
              </a-table>
            </a-card>

            <a-card title="正在进行的任务" v-if="activeTasks.length > 0" style="margin-top: 20px;">
              <a-list>
                <a-list-item v-for="task in activeTasks" :key="task.task_uuid">
                  <a-list-item-meta
                    :title="task.message"
                    :description="`进度: ${task.progress}% - ${task.status}`"
                  >
                    <template #avatar>
                      <a-progress type="circle" :percent="task.progress / 100" size="mini" />
                    </template>
                  </a-list-item-meta>
                </a-list-item>
              </a-list>
            </a-card>
          </a-col>

          <a-col :span="8">
            <a-card title="定时备份策略">
              <a-tabs default-active-key="all">
                <!-- 所有站点备份 -->
                <a-tab-pane key="all" title="所有站点">
                  <div style="margin-top: 20px;">
                    <a-space direction="vertical" fill size="large">
                      <a-form layout="vertical">
                        <a-form-item label="包含内容">
                          <a-space direction="vertical">
                            <a-checkbox v-model="allSitesBackupConfig.include_db">包含数据库</a-checkbox>
                            <a-checkbox v-model="allSitesBackupConfig.include_files">包含网站文件</a-checkbox>
                          </a-space>
                        </a-form-item>
                        
                        <a-button type="primary" long size="large" @click="handleAllSitesBackup" :loading="loading.backup">
                          一键备份所有站点
                        </a-button>
                      </a-form>
                      
                      <a-typography-text type="secondary" size="small">
                        * 点击按钮将立即为面板中所有已配置的站点创建备份任务。
                      </a-typography-text>
                    </a-space>
                  </div>
                </a-tab-pane>

                <!-- 单个站点备份 -->
                <a-tab-pane key="single" title="单个站点">
                  <a-form layout="vertical" :model="scheduleForm" style="margin-top: 10px;">
                    <a-form-item label="选择站点">
                      <a-select v-model="scheduleForm.site_id" placeholder="请选择站点" @change="handleScheduleSiteChange">
                        <a-option v-for="item in items" :key="item.id" :value="item.id">{{ item.name }}</a-option>
                      </a-select>
                    </a-form-item>
                    
                    <a-form-item label="启用定时备份">
                      <a-switch v-model="scheduleForm.enabled" />
                    </a-form-item>
                    
                    <a-form-item label="备份频率">
                      <a-space direction="vertical" fill>
                        <a-row :gutter="8">
                          <a-col :span="10">
                            <a-select v-model="scheduleForm.frequency_type" placeholder="请选择频率">
                              <a-option value="weekly">每周</a-option>
                              <a-option value="monthly">每月</a-option>
                            </a-select>
                          </a-col>
                          <a-col :span="14">
                            <!-- 每周选择周几 -->
                            <a-select v-if="scheduleForm.frequency_type === 'weekly'" v-model="scheduleForm.cron_weekday" placeholder="周几">
                              <a-option :value="1">周一</a-option>
                              <a-option :value="2">周二</a-option>
                              <a-option :value="3">周三</a-option>
                              <a-option :value="4">周四</a-option>
                              <a-option :value="5">周五</a-option>
                              <a-option :value="6">周六</a-option>
                              <a-option :value="0">周日</a-option>
                            </a-select>
                            <!-- 每月选择几号 -->
                            <a-input-number v-if="scheduleForm.frequency_type === 'monthly'" v-model="scheduleForm.cron_monthday" placeholder="几号" :min="1" :max="31" hide-button>
                              <template #append>号</template>
                            </a-input-number>
                          </a-col>
                        </a-row>
                        <a-row :gutter="8">
                          <a-col :span="12">
                            <a-input-number v-model="scheduleForm.cron_hour" placeholder="时" :min="0" :max="23" hide-button>
                              <template #append>时</template>
                            </a-input-number>
                          </a-col>
                          <a-col :span="12">
                            <a-input-number v-model="scheduleForm.cron_minute" placeholder="分" :min="0" :max="59" hide-button>
                              <template #append>分</template>
                            </a-input-number>
                          </a-col>
                        </a-row>
                      </a-space>
                    </a-form-item>
                    
                    <a-form-item label="保留份数">
                      <a-input-number v-model="scheduleForm.retention_days" :min="1" :max="365" />
                    </a-form-item>

                    <a-form-item label="包含内容">
                      <a-space direction="vertical">
                        <a-checkbox v-model="scheduleForm.include_db">包含数据库</a-checkbox>
                        <a-checkbox v-model="scheduleForm.include_files">包含网站文件</a-checkbox>
                      </a-space>
                    </a-form-item>

                    <div style="margin-top: 20px;">
                      <a-button type="primary" long @click="handleSaveSchedule">保存策略</a-button>
                    </div>
                  </a-form>
                </a-tab-pane>
              </a-tabs>
            </a-card>
          </a-col>
        </a-row>
      </a-tab-pane>

      <!-- 一键迁移标签页 -->
      <a-tab-pane key="migration" title="一键迁移">
        <a-card title="从外部面板迁入">
          <a-alert style="margin-bottom: 20px;">支持从宝塔 (BT)、CyberPanel、Plesk 等面板导出的备份文件一键导入。</a-alert>
          <a-form :model="migrationForm" layout="vertical" style="max-width: 500px;">
            <a-form-item label="源面板类型">
              <a-radio-group v-model="migrationForm.type" type="button">
                <a-radio value="bt">宝塔面板</a-radio>
                <a-radio value="cyberpanel">CyberPanel</a-radio>
                <a-radio value="other">其他</a-radio>
              </a-radio-group>
            </a-form-item>
            <a-form-item label="备份文件路径">
              <a-input v-model="migrationForm.path" placeholder="/root/backup.tar.gz" />
            </a-form-item>
            <a-button type="primary" size="large" @click="handleMigration" :loading="loading.migration">开始迁移解析</a-button>
          </a-form>
        </a-card>
      </a-tab-pane>
    </a-tabs>

    <!-- 手动备份弹窗 -->
    <a-modal v-model:visible="showManualModal" title="创建手动备份" @ok="handleManualBackup">
      <a-form :model="manualForm" layout="vertical">
        <a-form-item label="备份目标" required>
          <a-radio-group v-model="manualForm.target">
            <a-radio value="site">指定站点</a-radio>
            <a-radio value="database">指定数据库</a-radio>
            <a-radio value="full">全站备份</a-radio>
          </a-radio-group>
        </a-form-item>
        <a-form-item label="选择对象" v-if="manualForm.target !== 'full'">
          <a-select v-model="manualForm.id" :placeholder="manualForm.target === 'site' ? '请选择站点' : '请选择数据库'">
            <a-option v-for="item in items" :key="item.id" :value="item.id">
              {{ manualForm.target === 'site' ? item.name : (item.db_name || item.name) }}
            </a-option>
          </a-select>
          <template #extra v-if="items.length === 0">
            <span style="color: #ff7d00;">未发现可用站点，请先前往“站点管理”创建</span>
          </template>
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { Message } from '@arco-design/web-vue'
import request from '@/utils/request'

const activeTab = ref('records')
const loading = reactive({
  fetch: false,
  backup: false,
  migration: false
})

const showManualModal = ref(false)
const backups = ref([])
const activeTasks = ref([])
const items = ref([])
let pollTimer = null

const handleOpenManualModal = async () => {
  showManualModal.value = true
  await fetchData()
  if (items.value.length > 0 && !manualForm.id) {
    manualForm.id = items.value[0].id
  }
}

const scheduleForm = reactive({
  site_id: null,
  name: 'Default Schedule',
  cron_expression: '0 0 * * *',
  frequency_type: 'weekly',
  cron_day: 1,
  cron_hour: 0,
  cron_minute: 0,
  cron_weekday: 0,
  cron_monthday: 1,
  enabled: true,
  frequency: 'daily',
  retention_days: 3,
  include_db: true,
  include_files: true
})

const manualForm = reactive({
  target: 'site',
  id: null
})

const migrationForm = reactive({
  type: 'bt',
  path: ''
})

const allSitesBackupConfig = reactive({
  include_db: true,
  include_files: true
})

const fetchData = async () => {
  loading.fetch = true
  try {
    // 1. 获取备份记录
    try {
      const res = await request.get('/security/backups')
      backups.value = res || []
    } catch (e) {
      console.error('Failed to fetch backups:', e)
    }
    
    // 2. 获取站点列表 (这是下拉菜单的数据源)
    try {
      const sitesRes = await request.get('/sites/')
      // 兼容多种返回格式: 直接数组 或 { items: [] }
      const sitesList = Array.isArray(sitesRes) ? sitesRes : (sitesRes.items || [])
      items.value = sitesList.map(s => ({ 
        id: s.id, 
        name: s.domain,
        db_name: s.db_name 
      }))
      
      if (items.value.length > 0 && !scheduleForm.site_id) {
        scheduleForm.site_id = items.value[0].id
      }
    } catch (e) {
      console.error('Failed to fetch sites:', e)
    }

    // 3. 获取定时任务配置
    try {
      const schedules = await request.get('/security/backups/schedule')
      if (schedules && schedules.length > 0) {
        Object.assign(scheduleForm, schedules[0])
      }
    } catch (e) {
      console.error('Failed to fetch schedules:', e)
    }
    
  } finally {
    loading.fetch = false
  }
}

const fetchTasks = async () => {
  try {
    const tasks = await request.get('/tasks/')
    activeTasks.value = tasks.filter(t => t.type === 'backup' && (t.status === 'pending' || t.status === 'running'))
    
    // If there are active tasks, keep polling
    if (activeTasks.value.length > 0) {
      if (!pollTimer) {
        pollTimer = setInterval(fetchTasks, 3000)
      }
    } else {
      if (pollTimer) {
        clearInterval(pollTimer)
        pollTimer = null
        // Refresh backups list when tasks finish
        fetchData()
      }
    }
  } catch (error) {
    console.error(error)
  }
}

const handleScheduleSiteChange = async (siteId) => {
  try {
    const schedules = await request.get(`/security/backups/schedule?site_id=${siteId}`)
    if (schedules && schedules.length > 0) {
      Object.assign(scheduleForm, schedules[0])
    } else {
      // Reset to defaults for this site
      Object.assign(scheduleForm, {
        site_id: siteId,
        name: 'Default Schedule',
        cron_expression: '0 0 * * *',
        enabled: true,
        retention_days: 7,
        include_db: true,
        include_files: true
      })
    }
  } catch (error) {
    console.error(error)
  }
}

const handleSaveSchedule = async () => {
  try {
    // 根据选择的频率类型构建 cron 表达式
    if (scheduleForm.frequency_type === 'custom') {
      // 简单实现：每隔 N 天/小时/分钟。
      // 这里可以根据实际后端逻辑调整，通常 "每隔" 用 */N
      const m = scheduleForm.cron_minute || 0
      const h = scheduleForm.cron_hour || 0
      const d = scheduleForm.cron_day || 1
      scheduleForm.cron_expression = `${m} ${h} */${d} * *` 
    } else if (scheduleForm.frequency_type === 'weekly') {
      scheduleForm.cron_expression = `0 0 * * ${scheduleForm.cron_weekday}`
    } else if (scheduleForm.frequency_type === 'monthly') {
      scheduleForm.cron_expression = `0 0 ${scheduleForm.cron_monthday} * *`
    }

    await request.post('/security/backups/schedule', scheduleForm)
    Message.success('定时备份策略已保存')
  } catch (error) {
    Message.error('保存策略失败')
  }
}

const handleManualBackup = async () => {
  try {
    await request.post(`/security/backups/create?target=${manualForm.target}&item_id=${manualForm.id || ''}`)
    Message.info('备份任务已在后台启动')
    showManualModal.value = false
    fetchTasks()
  } catch (error) {
    Message.error('创建备份失败')
  }
}

const handleAllSitesBackup = async () => {
  try {
    loading.backup = true
    await request.post('/security/backups/create', null, {
      params: {
        target: 'all',
        include_db: allSitesBackupConfig.include_db,
        include_files: allSitesBackupConfig.include_files
      }
    })
    Message.success('已启动所有站点备份任务')
    fetchTasks()
  } catch (error) {
    Message.error('启动一键备份失败')
  } finally {
    loading.backup = false
  }
}

const handleDownload = async (record) => {
  try {
    const response = await request.get(`/security/backups/${record.id}/download`, {
      responseType: 'blob'
    })
    const url = window.URL.createObjectURL(new Blob([response]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', record.name)
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
  } catch (error) {
    Message.error('下载失败')
  }
}

const handleRestore = async (record) => {
  try {
    await request.post(`/security/backups/${record.id}/restore`)
    Message.success('恢复任务已启动')
    fetchTasks()
  } catch (error) {
    Message.error('启动恢复失败')
  }
}

const handleDelete = async (record) => {
  try {
    await request.delete(`/security/backups/${record.id}`)
    Message.success('备份已删除')
    fetchData()
  } catch (error) {
    Message.error('删除失败')
  }
}

const handleMigration = () => {
  Message.info('迁移解析功能正在开发中...')
}

onMounted(() => {
  fetchData()
  fetchTasks()
})
</script>

<style scoped lang="scss">
.backup-container {
  padding: 0;
}
</style>
