<template>
  <div class="security-container">
    <a-typography-title :heading="2">安全中心</a-typography-title>

    <a-tabs v-model:active-key="activeTab">
      <!-- 系统与网站安全标签页 -->
      <a-tab-pane key="system" title="系统与网站安全">
        <a-row :gutter="20">
          <a-col :span="16">
            <a-card title="系统防火墙" hoverable>
              <template #extra>
                <a-switch :model-value="firewall.active" @change="handleFirewallToggle" :loading="loading.firewall" />
              </template>
              <a-table :data="firewall.rules" :pagination="false">
                <template #columns>
                  <a-table-column title="端口" data-index="port" />
                  <a-table-column title="协议" data-index="protocol" />
                  <a-table-column title="状态">
                    <template #cell>
                      <a-tag color="green">允许</a-tag>
                    </template>
                  </a-table-column>
                  <a-table-column title="操作">
                    <template #cell="{ record }">
                      <a-button type="text" status="danger" size="small">删除</a-button>
                    </template>
                  </a-table-column>
                </template>
              </a-table>
              <div style="margin-top: 15px;">
                <a-button type="outline" size="small">
                  <template #icon><icon-plus /></template>
                  添加规则
                </a-button>
              </div>
            </a-card>

            <a-card title="WordPress 安全加固" style="margin-top: 20px;">
              <template #extra>
                <a-select v-model="selectedSiteId" placeholder="选择站点" style="width: 200px" @change="handleSiteChange">
                  <a-option v-for="site in sites" :key="site.id" :value="site.id">{{ site.domain }}</a-option>
                </a-select>
              </template>
              <a-list>
                <a-list-item>
                  <a-list-item-meta title="后台路径隐藏" :description="currentSite?.wp_hide_login_path ? `当前路径: /${currentSite.wp_hide_login_path}` : '修改 /wp-admin 为自定义随机路径'" />
                  <template #actions>
                    <a-space>
                      <a-button v-if="currentSite?.wp_hide_login_path" type="text" size="small" @click="handleHideLogin(null)">禁用</a-button>
                      <a-button type="outline" size="small" @click="showHideLoginModal = true">配置</a-button>
                    </a-space>
                  </template>
                </a-list-item>
                <a-list-item>
                  <a-list-item-meta title="禁用 XML-RPC" description="防止针对 xmlrpc.php 的暴力破解与 DDoS" />
                  <template #actions>
                    <a-switch :model-value="currentSite?.wp_disable_xmlrpc" @change="handleToggleXmlRpc" />
                  </template>
                </a-list-item>
                <a-list-item>
                  <a-list-item-meta title="文件权限修复" description="恢复 WP 目录 755、文件 644 的标准权限" />
                  <template #actions>
                    <a-button type="outline" size="small" @click="handleFixPermissions">立即修复</a-button>
                  </template>
                </a-list-item>
              </a-list>
            </a-card>
          </a-col>

          <a-col :span="8">
            <a-card title="入侵防御 (Fail2ban)">
              <div class="status-item">
                <span class="label">服务状态:</span>
                <a-tag :color="fail2ban.active ? 'green' : 'red'">{{ fail2ban.active ? '运行中' : '已停止' }}</a-tag>
              </div>
              <a-divider />
              <div class="banned-ips">
                <div style="margin-bottom: 10px; font-weight: bold;">已封禁 IP 列表:</div>
                <a-list size="small" :max-height="300">
                  <a-list-item v-for="ip in fail2ban.banned_ips" :key="ip">
                    {{ ip }}
                    <template #actions>
                      <a-button type="text" size="small" @click="handleUnbanIp(ip)">解封</a-button>
                    </template>
                  </a-list-item>
                  <template #empty>暂无封禁记录</template>
                </a-list>
              </div>
            </a-card>
          </a-col>
        </a-row>
      </a-tab-pane>

      <!-- 管理安全标签页 -->
      <a-tab-pane key="admin" title="管理安全">
        <a-row :gutter="20">
          <a-col :span="12">
            <a-card title="修改管理密码">
              <a-form :model="passwordForm" layout="vertical" @submit="handlePasswordChange">
                <a-form-item label="当前密码" required>
                  <a-input-password v-model="passwordForm.old_password" placeholder="请输入当前密码" />
                </a-form-item>
                <a-form-item label="新密码" required>
                  <a-input-password v-model="passwordForm.new_password" placeholder="请输入新密码" />
                </a-form-item>
                <a-form-item label="确认新密码" required>
                  <a-input-password v-model="passwordForm.confirm_password" placeholder="请再次输入新密码" />
                </a-form-item>
                <a-button type="primary" html-type="submit" :loading="loading.password">更新密码</a-button>
              </a-form>
            </a-card>
          </a-col>
          <a-col :span="12">
            <a-card title="面板访问设置">
              <a-form :model="panelConfig" layout="vertical">
                <a-form-item label="登录超时时间 (分钟)">
                  <a-input-number v-model="panelConfig.session_timeout" :min="5" :max="1440" />
                </a-form-item>
                <a-form-item label="两步验证 (2FA)">
                  <a-switch v-model="panelConfig.enable_2fa" disabled />
                  <span style="margin-left: 10px; color: #86909c;">(开发中)</span>
                </a-form-item>
                <a-button type="outline" @click="handleSavePanelConfig">保存设置</a-button>
              </a-form>
            </a-card>
          </a-col>
        </a-row>
      </a-tab-pane>
    </a-tabs>

    <!-- 隐藏后台路径弹窗 -->
    <a-modal v-model:visible="showHideLoginModal" title="配置隐藏后台路径" @ok="handleHideLogin(hideLoginPath)">
      <a-form layout="vertical">
        <a-form-item label="自定义登录路径" help="例如: my-login。设置后，原 /wp-admin 将无法直接访问。">
          <a-input v-model="hideLoginPath" placeholder="请输入自定义路径字符串" />
        </a-form-item>
        <a-alert type="warning">请务必牢记此路径，否则您将无法进入 WordPress 后台。</a-alert>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed } from 'vue'
import request from '@/utils/request'
import { Message } from '@arco-design/web-vue'

const activeTab = ref('system')
const loading = reactive({
  firewall: false,
  wp: false,
  password: false
})

const sites = ref([])
const selectedSiteId = ref(null)
const currentSite = computed(() => sites.value.find(s => s.id === selectedSiteId.value))

const showHideLoginModal = ref(false)
const hideLoginPath = ref('')

const firewall = reactive({
  active: false,
  rules: []
})

const fail2ban = reactive({
  active: false,
  banned_ips: []
})

const passwordForm = reactive({
  old_password: '',
  new_password: '',
  confirm_password: ''
})

const panelConfig = reactive({
  session_timeout: 60,
  enable_2fa: false
})

const fetchData = async () => {
  try {
    const fw = await request.get('/security/firewall/status')
    Object.assign(firewall, fw)
    
    const f2b = await request.get('/security/fail2ban/status')
    Object.assign(fail2ban, f2b)

    const sitesRes = await request.get('/sites')
    sites.value = sitesRes
    if (sitesRes.length > 0 && !selectedSiteId.value) {
      selectedSiteId.value = sitesRes[0].id
    }
  } catch (error) {
    console.error(error)
  }
}

const handleFirewallToggle = async (val) => {
  loading.firewall = true
  try {
    await request.post(`/security/firewall/toggle?enable=${val}`)
    firewall.active = val
    Message.success(val ? '防火墙已开启' : '防火墙已关闭')
  } catch (error) {
    Message.error('操作失败')
  } finally {
    loading.firewall = false
  }
}

const handleSiteChange = (val) => {
  if (currentSite.value) {
    hideLoginPath.value = currentSite.value.wp_hide_login_path || ''
  }
}

const handleHideLogin = async (path) => {
  if (!selectedSiteId.value) return
  loading.wp = true
  try {
    await request.post(`/security/wordpress/hide-login?site_id=${selectedSiteId.value}&path=${path || ''}`)
    Message.success(path ? '隐藏后台路径已生效' : '已禁用隐藏后台路径')
    showHideLoginModal.value = false
    fetchData()
  } catch (error) {
    Message.error('操作失败')
  } finally {
    loading.wp = false
  }
}

const handleToggleXmlRpc = async (val) => {
  if (!selectedSiteId.value) return
  try {
    await request.post(`/security/wordpress/toggle-xmlrpc?site_id=${selectedSiteId.value}&enable=${val}`)
    Message.success(val ? '已启用 XML-RPC' : '已禁用 XML-RPC')
    fetchData()
  } catch (error) {
    Message.error('操作失败')
  }
}

const handleFixPermissions = async () => {
  if (!selectedSiteId.value) return
  try {
    await request.post(`/security/wordpress/fix-permissions?site_id=${selectedSiteId.value}`)
    Message.success('文件权限修复任务已启动')
  } catch (error) {
    Message.error('操作失败')
  }
}

const handleUnbanIp = async (ip) => {
  try {
    await request.post(`/security/fail2ban/unban?ip=${ip}`)
    Message.success(`IP ${ip} 已解封`)
    fetchData()
  } catch (error) {
    Message.error('操作失败')
  }
}

const handlePasswordChange = async () => {
  if (passwordForm.new_password !== passwordForm.confirm_password) {
    Message.error('两次输入的新密码不一致')
    return
  }
  loading.password = true
  try {
    await request.post(`/security/password?old_password=${passwordForm.old_password}&new_password=${passwordForm.new_password}`)
    Message.success('密码更新成功')
    passwordForm.old_password = ''
    passwordForm.new_password = ''
    passwordForm.confirm_password = ''
  } catch (error) {
    Message.error(error.response?.data?.detail || '密码更新失败')
  } finally {
    loading.password = false
  }
}

const handleSavePanelConfig = async () => {
  try {
    await request.post('/security/panel-config', panelConfig)
    Message.success('面板配置已保存')
  } catch (error) {
    Message.error('保存失败')
  }
}

onMounted(fetchData)
</script>

<style scoped lang="scss">
.security-container {
  padding: 0 0 20px 0;
  .status-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    .label { font-weight: bold; }
  }
}
</style>
