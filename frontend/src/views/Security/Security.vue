<template>
  <div class="security-container">
    <a-typography-title :heading="2">安全中心</a-typography-title>

    <a-tabs v-model:active-key="activeTab">
      

      <!-- WordPress 安全加固标签页 -->
      <a-tab-pane key="wordpress" title="WordPress 安全加固">
        <a-card title="一键安全加固 (针对所有站点)" :loading="loading.wp">
          <template #extra>
            <a-tag color="arcoblue">共检测到 {{ sites.length }} 个 WordPress 站点</a-tag>
          </template>
          <a-list>
            <a-list-item>
              <a-list-item-meta title="后台路径隐藏" description="将所有 WordPress 站点的 /wp-admin 修改为统一的自定义随机路径，防止扫描与暴力破解。" />
              <div v-if="commonLoginPath" style="margin-right: 20px;">
                <a-tag color="green" bordered>当前统一路径: /{{ commonLoginPath }}</a-tag>
              </div>
              <template #actions>
                <a-button type="outline" size="small" @click="showHideLoginModal = true">一键配置</a-button>
              </template>
            </a-list-item>
            <a-list-item>
              <a-list-item-meta title="禁用 XML-RPC" description="在所有站点中禁用 xmlrpc.php，防止针对该接口的暴力破解与 DDoS 攻击。" />
              <template #actions>
                <a-button type="outline" size="small" @click="handleBatchAction('toggle-xmlrpc', { enable: true })">一键禁用</a-button>
              </template>
            </a-list-item>
            <a-list-item>
              <a-list-item-meta title="文件权限修复" description="批量恢复所有站点的目录 755、文件 644 的标准安全权限。" />
              <template #actions>
                <a-button type="outline" size="small" @click="handleBatchAction('fix-permissions')">立即修复</a-button>
              </template>
            </a-list-item>
          </a-list>
        </a-card>
      </a-tab-pane>

      <!-- 入侵防御标签页 -->
      <a-tab-pane key="fail2ban" title="入侵防御">
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
      </a-tab-pane>

      <!-- 系统安全标签页 -->
      <a-tab-pane key="system" title="系统安全">
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
      </a-tab-pane>

    </a-tabs>

    <!-- 隐藏后台路径弹窗 -->
    <a-modal v-model:visible="showHideLoginModal" title="配置隐藏后台路径" @ok="handleHideLogin(hideLoginPath)">
      <a-form :model="{ path: hideLoginPath }" layout="vertical">
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

const activeTab = ref('wordpress')
const loading = reactive({
  firewall: false,
  wp: false
})

const sites = ref([])

const commonLoginPath = computed(() => {
  if (!sites.value || sites.value.length === 0) return ''
  // 打印调试信息，确保数据已加载
  console.log('Current sites:', sites.value)
  // 获取第一个有配置路径的站点路径作为展示
  const siteWithPath = sites.value.find(s => s.wp_hide_login_path)
  return siteWithPath ? siteWithPath.wp_hide_login_path : ''
})

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

const fetchData = async () => {
  try {
    const fw = await request.get('/security/firewall/status')
    Object.assign(firewall, fw)
    
    const f2b = await request.get('/security/fail2ban/status')
    Object.assign(fail2ban, f2b)

    const sitesRes = await request.get('/sites/')
    sites.value = sitesRes
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

const handleBatchAction = async (action, params = {}) => {
  if (sites.value.length === 0) {
    Message.warning('未检测到 WordPress 站点')
    return
  }
  
  loading.wp = true
  try {
    // 这里循环调用现有 API 实现批量操作，未来可由后端提供批量接口优化
    const promises = sites.value.map(site => {
      if (action === 'hide-login') {
        return request.post(`/security/wordpress/hide-login?site_id=${site.id}&path=${params.path || ''}`)
      } else if (action === 'toggle-xmlrpc') {
        return request.post(`/security/wordpress/toggle-xmlrpc?site_id=${site.id}&enable=${params.enable}`)
      } else if (action === 'fix-permissions') {
        return request.post(`/security/wordpress/fix-permissions?site_id=${site.id}`)
      }
    })
    
    await Promise.all(promises)
    Message.success('一键加固操作已成功应用至所有站点')
    if (action === 'hide-login') showHideLoginModal.value = false
    fetchData()
  } catch (error) {
    Message.error('部分或全部站点操作失败，请检查系统日志')
  } finally {
    loading.wp = false
  }
}

const handleHideLogin = (path) => {
  handleBatchAction('hide-login', { path })
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
