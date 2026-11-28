<template>
  <div class="notification-settings">
    <!-- SMTP 邮件配置 -->
    <a-card title="SMTP 邮件配置" class="notify-card">
      <a-form :model="smtp" layout="vertical">
        <a-row :gutter="16">
          <a-col :span="9">
            <a-form-item label="SMTP 服务器">
              <a-input v-model="smtp.host" placeholder="smtp.example.com" allow-clear />
            </a-form-item>
          </a-col>
          <a-col :span="5">
            <a-form-item label="端口">
              <a-input-number v-model="smtp.port" :min="1" :max="65535" style="width: 100%" />
            </a-form-item>
          </a-col>
          <a-col :span="10">
            <a-form-item label="加密方式">
              <a-select v-model="smtp.encryption" style="width: 100%">
                <a-option value="STARTTLS">STARTTLS</a-option>
                <a-option value="SSL/TLS">SSL/TLS</a-option>
                <a-option value="none">无加密</a-option>
              </a-select>
            </a-form-item>
          </a-col>
        </a-row>
        <a-row :gutter="16">
          <a-col :span="12">
            <a-form-item label="SMTP 用户名">
              <a-input v-model="smtp.username" placeholder="用户名" allow-clear />
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="密码/授权码">
              <a-input-password v-model="smtp.password" placeholder="密码或授权码" allow-clear />
            </a-form-item>
          </a-col>
        </a-row>
        <a-row :gutter="16">
          <a-col :span="12">
            <a-form-item
              label="发件邮箱"
              help="用于 From 和 envelope-from，可与 SMTP 用户名不同；留空时若用户名是邮箱将自动使用用户名。"
            >
              <a-input v-model="smtp.from_email" placeholder="noreply@example.com" allow-clear />
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="管理员通知邮箱">
              <a-input v-model="smtp.admin_email" placeholder="admin@example.com" allow-clear />
            </a-form-item>
          </a-col>
        </a-row>
      </a-form>

      <a-space wrap>
        <a-button type="primary" :loading="saving.smtp" @click="saveSmtp">保存</a-button>
        <a-button :loading="testing.smtp" @click="testSmtp">测试发送</a-button>
        <a-button :loading="diagnosing" @click="diagnoseSmtp">诊断 SMTP</a-button>
        <a-button @click="copyConfig">复制配置</a-button>
        <a-button @click="importVisible = true">导入配置</a-button>
      </a-space>

      <a-alert type="warning" class="notify-hint" size="small">
        配置码包含可恢复的 SMTP 密钥，请勿发送给不可信人员；导入后需手动保存。
      </a-alert>
      <div class="notify-hint">
        使用已保存的 SMTP 配置进行 DNS、连接、加密、认证和测试邮件提交检查；报告不会包含密码或授权码。
      </div>
      <pre v-if="diagnosisReport" class="diagnosis-report">{{ diagnosisReport }}</pre>
    </a-card>

    <!-- Webhook 推送 -->
    <a-card title="Webhook 推送" class="notify-card">
      <a-form :model="webhook" layout="vertical">
        <a-row :gutter="16">
          <a-col :span="6">
            <a-form-item label="推送渠道">
              <a-select v-model="webhook.channel" style="width: 100%">
                <a-option value="wecom">企业微信</a-option>
                <a-option value="dingtalk">钉钉</a-option>
                <a-option value="feishu">飞书</a-option>
              </a-select>
            </a-form-item>
          </a-col>
          <a-col :span="18">
            <a-form-item label="Webhook URL" help="保存有效 URL 后自动启用；清空 URL 并保存即可停用。">
              <a-input v-model="webhook.url" placeholder="https://..." allow-clear />
            </a-form-item>
          </a-col>
        </a-row>
      </a-form>
      <a-space>
        <a-button type="primary" :loading="saving.webhook" @click="saveWebhook">保存</a-button>
        <a-button :loading="testing.webhook" @click="testWebhook">测试发送</a-button>
      </a-space>
    </a-card>

    <!-- 告警规则 -->
    <a-card title="告警规则" class="notify-card">
      <div class="rule-grid">
        <div v-for="rule in ruleDefs" :key="rule.key" class="rule-item">
          <a-switch v-model="rules[rule.key]" size="small" />
          <span>{{ rule.label }}</span>
        </div>
      </div>
      <a-divider />
      <a-row :gutter="16">
        <a-col :span="6">
          <a-form-item label="告警阈值（次）">
            <a-input-number v-model="thresholds.hit_count" :min="1" :max="10000" style="width: 100%" />
          </a-form-item>
        </a-col>
        <a-col :span="6">
          <a-form-item label="统计窗口（小时）">
            <a-input-number v-model="thresholds.window_hours" :min="1" :max="720" style="width: 100%" />
          </a-form-item>
        </a-col>
      </a-row>
      <div class="notify-hint">
        资源告警每 2 小时、可用性告警每 6 小时、运维告警每 24 小时最多重发一次；仅持续异常发送恢复通知。
      </div>
      <div class="notify-hint">
        伪装搜索引擎爬虫提醒默认关闭，不自动封禁。下方阈值和窗口现仅用于该提醒。
      </div>
      <a-button type="primary" :loading="saving.rules" @click="saveRules">保存规则</a-button>
    </a-card>

    <!-- 告警记录 -->
    <a-card title="告警记录（最近100条）" class="notify-card">
      <template #extra>
        <a-button size="small" :loading="loading.records" @click="fetchRecords">
          <template #icon><icon-refresh /></template>
          刷新
        </a-button>
      </template>
      <a-table
        :data="records"
        :loading="loading.records"
        :pagination="false"
        :scroll="{ y: 320 }"
        row-key="id"
      >
        <template #columns>
          <a-table-column title="时间" data-index="time" :width="170" />
          <a-table-column title="类型" data-index="type" :width="130" />
          <a-table-column title="级别" :width="90">
            <template #cell="{ record }">
              <a-tag :color="record.level === '恢复' ? 'green' : 'red'">
                {{ record.level === '恢复' ? '● 恢复' : '● 告警' }}
              </a-tag>
            </template>
          </a-table-column>
          <a-table-column title="内容" data-index="content" />
        </template>
      </a-table>
    </a-card>

    <!-- 导入配置 -->
    <a-modal v-model:visible="importVisible" title="导入 SMTP 配置" @ok="importConfig" :confirm-loading="importing">
      <a-input-textarea
        v-model="importCode"
        :auto-size="{ minRows: 4 }"
        placeholder="粘贴从面板复制的配置码"
      />
      <div class="notify-hint">导入后请检查表单内容并手动点击「保存」。</div>
    </a-modal>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { Message } from '@arco-design/web-vue'
import { IconRefresh } from '@arco-design/web-vue/es/icon'
import request from '@/utils/request'

const ruleDefs = [
  { key: 'cpu_high', label: 'CPU > 80% 持续 5 分钟' },
  { key: 'mem_low', label: '可用内存 < 10% 持续 5 分钟' },
  { key: 'oom', label: '系统内存耗尽并强制终止进程' },
  { key: 'disk_high', label: '磁盘 > 90%' },
  { key: 'service_restart', label: '服务进程异常重启' },
  { key: 'ssl_expiring', label: 'SSL 证书即将到期（14天内）' },
  { key: 'db_backup_fail', label: '数据库备份失败' },
  { key: 'remote_backup_fail', label: '远程备份失败（需先启用远程备份）' },
  { key: 'cron_fail', label: '计划任务执行失败' },
  { key: 'site_expiring', label: '网站即将到期（14天内）' },
  { key: 'system_update', label: '系统有可用更新' },
  { key: 'panel_update', label: '面板有新版本' },
  { key: 'fake_crawler', label: '同一 IP 触发伪装搜索引擎爬虫达到阈值' },
]

const smtp = reactive({
  host: '',
  port: 587,
  encryption: 'STARTTLS',
  username: '',
  password: '',
  from_email: '',
  admin_email: '',
})
const webhook = reactive({ channel: 'wecom', url: '' })
const rules = reactive({})
const thresholds = reactive({ hit_count: 10, window_hours: 24 })
const records = ref([])

const saving = reactive({ smtp: false, webhook: false, rules: false })
const testing = reactive({ smtp: false, webhook: false })
const diagnosing = ref(false)
const loading = reactive({ records: false })
const diagnosisReport = ref('')
const importVisible = ref(false)
const importCode = ref('')
const importing = ref(false)

const errMsg = (error, fallback) => Message.error(error.response?.data?.detail || fallback)

const fetchConfig = async () => {
  try {
    const res = await request.get('/notifications/config')
    if (res.smtp) Object.assign(smtp, res.smtp)
    if (res.webhook) Object.assign(webhook, res.webhook)
    if (res.rules) {
      ruleDefs.forEach((r) => {
        rules[r.key] = res.rules[r.key] !== undefined ? res.rules[r.key] : r.key !== 'fake_crawler'
      })
    } else {
      ruleDefs.forEach((r) => { rules[r.key] = r.key !== 'fake_crawler' })
    }
    if (res.thresholds) Object.assign(thresholds, res.thresholds)
  } catch (error) {
    errMsg(error, '加载通知配置失败')
  }
}

const fetchRecords = async () => {
  loading.records = true
  try {
    records.value = await request.get('/notifications/records')
  } catch (error) {
    errMsg(error, '加载告警记录失败')
  } finally {
    loading.records = false
  }
}

const saveSmtp = async () => {
  saving.smtp = true
  try {
    await request.post('/notifications/smtp', smtp)
    Message.success('SMTP 配置已保存')
  } catch (error) {
    errMsg(error, '保存 SMTP 配置失败')
  } finally {
    saving.smtp = false
  }
}

const testSmtp = async () => {
  testing.smtp = true
  try {
    const res = await request.post('/notifications/smtp/test', {})
    Message.success(res?.message || '测试邮件已发送')
  } catch (error) {
    errMsg(error, '测试发送失败')
  } finally {
    testing.smtp = false
  }
}

const diagnoseSmtp = async () => {
  diagnosing.value = true
  diagnosisReport.value = ''
  try {
    const res = await request.post('/notifications/smtp/diagnose')
    diagnosisReport.value = res.report || '无诊断结果'
  } catch (error) {
    errMsg(error, '诊断失败')
  } finally {
    diagnosing.value = false
  }
}

const copyConfig = async () => {
  try {
    const res = await request.get('/notifications/smtp/export')
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(res.code)
    } else {
      const textarea = document.createElement('textarea')
      textarea.value = res.code
      textarea.style.position = 'fixed'
      textarea.style.opacity = '0'
      document.body.appendChild(textarea)
      textarea.select()
      document.execCommand('copy')
      document.body.removeChild(textarea)
    }
    Message.success('配置码已复制')
  } catch (error) {
    errMsg(error, '复制配置失败')
  }
}

const importConfig = async () => {
  if (!importCode.value.trim()) {
    Message.warning('请粘贴配置码')
    return
  }
  importing.value = true
  try {
    const res = await request.post('/notifications/smtp/import', { code: importCode.value.trim() })
    if (res.smtp) Object.assign(smtp, res.smtp)
    Message.success('配置已导入，请检查后保存')
    importVisible.value = false
    importCode.value = ''
  } catch (error) {
    errMsg(error, '导入配置失败')
  } finally {
    importing.value = false
  }
}

const saveWebhook = async () => {
  saving.webhook = true
  try {
    await request.post('/notifications/webhook', webhook)
    Message.success(webhook.url ? 'Webhook 已保存并启用' : 'Webhook 已停用')
  } catch (error) {
    errMsg(error, '保存 Webhook 失败')
  } finally {
    saving.webhook = false
  }
}

const testWebhook = async () => {
  testing.webhook = true
  try {
    const res = await request.post('/notifications/webhook/test')
    Message.success(res?.message || '测试消息已发送')
  } catch (error) {
    errMsg(error, '测试发送失败')
  } finally {
    testing.webhook = false
  }
}

const saveRules = async () => {
  saving.rules = true
  try {
    await request.post('/notifications/rules', { rules, thresholds })
    Message.success('告警规则已保存')
  } catch (error) {
    errMsg(error, '保存告警规则失败')
  } finally {
    saving.rules = false
  }
}

onMounted(() => {
  fetchConfig()
  fetchRecords()
})
</script>

<style scoped>
.notification-settings {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.notify-hint {
  margin-top: 10px;
  font-size: 12px;
  color: var(--color-text-3);
  line-height: 1.6;
}
.diagnosis-report {
  margin-top: 10px;
  padding: 10px 12px;
  background: var(--color-fill-1);
  border-radius: 4px;
  font-size: 12px;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-all;
  max-height: 260px;
  overflow: auto;
}
.rule-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px 16px;
}
.rule-item {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  font-size: 13px;
}
</style>
