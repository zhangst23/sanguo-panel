<template>
  <div class="backup-container">
    <a-typography-title :heading="2">备份与迁移</a-typography-title>

    <a-tabs v-model:active-key="activeTab">
      <!-- 备份记录标签页 -->
      <a-tab-pane key="records" title="备份管理">
        <a-card>
          <template #extra>
            <a-button type="primary" @click="showManualModal = true">
              <template #icon><icon-plus /></template>
              创建手动备份
            </a-button>
          </template>
          <a-table :data="backups" :loading="loading.fetch">
            <template #columns>
              <a-table-column title="文件名" data-index="filename" />
              <a-table-column title="大小" data-index="size" />
              <a-table-column title="创建时间" data-index="created_at" />
              <a-table-column title="操作">
                <template #cell="{ record }">
                  <a-space>
                    <a-button type="text" size="small">下载</a-button>
                    <a-button type="text" size="small" status="success">恢复</a-button>
                    <a-button type="text" size="small" status="danger">删除</a-button>
                  </a-space>
                </template>
              </a-table-column>
            </template>
          </a-table>
        </a-card>

        <a-card title="定时备份策略" style="margin-top: 20px;">
          <a-form layout="inline" :model="scheduleForm">
            <a-form-item label="启用定时备份">
              <a-switch v-model="scheduleForm.enabled" />
            </a-form-item>
            <a-form-item label="周期">
              <a-select v-model="scheduleForm.frequency" style="width: 120px;">
                <a-option value="daily">每天</a-option>
                <a-option value="weekly">每周</a-option>
                <a-option value="monthly">每月</a-option>
              </a-select>
            </a-form-item>
            <a-form-item label="保留份数">
              <a-input-number v-model="scheduleForm.retention" style="width: 80px;" :min="1" :max="30" />
            </a-form-item>
            <a-button type="outline" @click="handleSaveSchedule">保存策略</a-button>
          </a-form>
        </a-card>
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
          <a-select v-model="manualForm.id" placeholder="请选择备份对象">
            <a-option v-for="item in items" :key="item.id" :value="item.id">{{ item.name }}</a-option>
          </a-select>
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
const items = ref([])

const scheduleForm = reactive({
  enabled: true,
  frequency: 'daily',
  retention: 7,
  storage: 'local'
})

const manualForm = reactive({
  target: 'site',
  id: null
})

const migrationForm = reactive({
  type: 'bt',
  path: ''
})

const fetchData = async () => {
  loading.fetch = true
  try {
    const res = await request.get('/security/backups')
    backups.value = res
    
    const schedule = await request.get('/security/backups/schedule')
    Object.assign(scheduleForm, schedule)
    
    const sites = await request.get('/sites')
    items.value = sites.map(s => ({ id: s.id, name: s.domain }))
  } catch (error) {
    console.error(error)
  } finally {
    loading.fetch = false
  }
}

const handleSaveSchedule = async () => {
  try {
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
    fetchData()
  } catch (error) {
    Message.error('创建备份失败')
  }
}

const handleMigration = () => {
  Message.info('迁移解析功能正在开发中...')
}

onMounted(fetchData)
</script>

<style scoped lang="scss">
.backup-container {
  padding: 0 0 20px 0;
}
</style>
