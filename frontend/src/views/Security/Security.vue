<template>
  <div class="security-container">
    <a-typography-title :heading="2">安全防御</a-typography-title>

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

      <!-- Fail2ban 设置 -->
      <a-tab-pane key="fail2ban-settings" title="Fail2ban 设置">
        <a-grid :cols="24" :col-gap="16" :row-gap="16">
          <!-- 基本封禁策略 -->
          <a-grid-item :span="4">
            <a-card title="基本封禁策略" class="setting-card">
              <a-form :model="fail2ban.config" layout="vertical" @submit="handleUpdateF2bConfig">
                <a-form-item label="封禁时长 (秒)" field="bantime">
                  <a-input-number v-model="fail2ban.config.bantime" :min="60" />
                </a-form-item>
                <a-form-item label="检测窗口 (秒)" field="findtime">
                  <a-input-number v-model="fail2ban.config.findtime" :min="60" />
                </a-form-item>
                <a-form-item label="最大重试次数" field="maxretry">
                  <a-input-number v-model="fail2ban.config.maxretry" :min="1" :max="20" />
                </a-form-item>
                <a-button type="primary" html-type="submit" long>保存策略</a-button>
              </a-form>
            </a-card>
          </a-grid-item>

          <!-- 请求频率限制 -->
          <a-grid-item :span="12">
            <a-card title="请求频率限制" class="setting-card">
              <template #extra>
                <a-button type="text" size="small" @click="showRateHelp = true">
                  <template #icon><icon-question-circle /></template>帮助说明
                </a-button>
              </template>
              <a-form :model="ratelimit" layout="vertical">
                <a-form-item>
                  <a-switch v-model="ratelimit.enabled" />
                  <span style="margin-left: 10px; font-weight: 600;">开启全局限速</span>
                  <span>（未登录访客受频率限制，已登录 WordPress 用户不影响。）</span>
                </a-form-item>
                <a-form-item
                  label="请求频率限制 (次/分钟)"
                  field="limit_per_minute"
                  help="非 Elementor 等重型页面建议 30-60。Elementor / 多插件站点建议 60-120。调整建议和测试方法详见右上角「帮助说明」"
                >
                  <a-input-number v-model="ratelimit.limit_per_minute" :min="1" :style="{ width: '180px' }" />
                </a-form-item>
                <a-form-item
                  label="突发缓冲 (次)"
                  field="burst"
                  help="页面首屏瞬间并发请求缓冲量。Elementor / 多插件站点建议 150-300，非 Elementor 建议 30-120。调整建议和测试方法详见右上角「帮助说明」"
                >
                  <a-input-number v-model="ratelimit.burst" :min="1" :style="{ width: '180px' }" />
                </a-form-item>
                <a-alert type="warning" style="margin-bottom: 16px;">
                  注意：多次触发 429 的 IP 将被 Fail2ban 自动封禁，请确保预留足够缓冲
                </a-alert>
                <a-button type="primary" long :loading="savingRatelimit" @click="handleSaveRatelimit">保存限速设置</a-button>
              </a-form>
            </a-card>
          </a-grid-item>

          <!-- 爬虫限速 -->
          <a-grid-item :span="8">
            <a-card title="爬虫限速" class="setting-card">
              <template #extra>
                <a-button type="text" size="small" @click="showBotHelp = true">
                  <template #icon><icon-question-circle /></template>帮助说明
                </a-button>
              </template>
              <a-form :model="botRatelimit" layout="vertical">
                <a-form-item>
                  <a-switch v-model="botRatelimit.enabled" />
                  <span style="margin-left: 10px; font-weight: 600;">开启 Bot UA 统一限速</span>
                </a-form-item>
                <a-alert type="info" style="margin-bottom: 16px;">
                  默认关闭。开启后，每个站点独立限速；同一站点内常见 Bot UA 共享该站点的限速桶，普通浏览器不受此层影响。
                </a-alert>
                <a-form-item
                  label="Bot 请求频率 (次/分钟)"
                  field="bot_limit_per_minute"
                  help="默认 30。用于压制多 IP 假爬虫持续扫站，避免打满 WordPress 动态 404。"
                >
                  <a-input-number v-model="botRatelimit.bot_limit_per_minute" :min="1" :style="{ width: '180px' }" />
                </a-form-item>
                <a-form-item
                  label="Bot 突发缓冲 (次)"
                  field="bot_burst"
                  help="默认 20。Googlebot/Bingbot 仅在来源 IP 属于官方段时豁免；假冒搜索爬虫会进入限速桶。"
                >
                  <a-input-number v-model="botRatelimit.bot_burst" :min="1" :style="{ width: '180px' }" />
                </a-form-item>
                <a-button type="primary" long :loading="savingBotRatelimit" @click="handleSaveBotRatelimit">保存爬虫限速</a-button>
              </a-form>
            </a-card>
          </a-grid-item>

          <!-- 白名单管理 -->
          <a-grid-item :span="24">
            <a-card title="白名单管理">
              <a-row :gutter="16">
                <a-col :span="14">
                  <a-card :bordered="false" class="whitelist-sub" title="官方白名单（由面板自动拉取）">
                    <template #extra>
                      <a-button size="small" type="outline" :loading="whitelistRefreshing" @click="handleRefreshWhitelist">
                        <template #icon><icon-refresh /></template>立即拉取
                      </a-button>
                    </template>
                    <a-list size="small" :max-height="320" :scrollbar="{ showScrollBar: 'always' }">
                      <a-list-item v-for="ip in whitelist.official" :key="ip">{{ ip }}</a-list-item>
                      <template #empty>暂无官方白名单</template>
                    </a-list>
                    <div class="whitelist-updated">上次更新：{{ whitelist.last_updated }}</div>
                  </a-card>
                </a-col>
                <a-col :span="10">
                  <a-card :bordered="false" class="whitelist-sub" title="自定义白名单（不会被官方拉取覆盖）">
                    <a-textarea
                      v-model="customWhitelistText"
                      placeholder="一行一个 IP 或 CIDR，例如：1.2.3.4 / 10.0.0.0/8"
                      :auto-size="{ minRows: 4, maxRows: 8 }"
                    />
                    <a-button type="primary" size="small" style="margin-top: 10px;" :loading="customSaving" @click="handleSaveCustomWhitelist">
                      保存自定义白名单
                    </a-button>
                  </a-card>
                  <a-card :bordered="false" class="whitelist-sub" title="WordPress 安全日志路径白名单" style="margin-top: 16px;">
                    <a-textarea
                      v-model="pathWhitelistText"
                      placeholder="一行一个路径，支持 * 通配符"
                      :auto-size="{ minRows: 4, maxRows: 8 }"
                    />
                    <div class="whitelist-help">
                      一行一个路径，可使用 * 通配符；必须以 / 开头。不支持正则，不允许空格、分号、引号或 ..。
                    </div>
                    <a-button type="primary" size="small" style="margin-top: 10px;" :loading="pathSaving" @click="handleSavePathWhitelist">
                      保存路径白名单
                    </a-button>
                  </a-card>
                </a-col>
              </a-row>
            </a-card>
          </a-grid-item>
        </a-grid>
      </a-tab-pane>

      <!-- IP 封禁列表 -->
      <a-tab-pane key="fail2ban-list" title="IP 封禁列表">
        <a-grid :cols="24" :col-gap="16">
          <a-grid-item :span="24">
            <a-card title="IP 封禁列表">
              <template #extra>
                <a-space>
                  <a-tag :color="fail2ban.active ? 'green' : 'red'">{{ fail2ban.active ? '运行中' : '已停止' }}</a-tag>
                  <a-button size="small" :loading="restarting" @click="handleStartFail2ban">
                    <template #icon><icon-refresh /></template>
                    重新启动
                  </a-button>
                </a-space>
              </template>

              <!-- 手动封禁 IP -->
              <a-card :bordered="false" class="manual-ban-card" title="手动封禁 IP">
                <a-space wrap>
                  <a-input
                    v-model="manualBanIp"
                    placeholder="请输入要封禁的 IP 地址"
                    allow-clear
                    style="width: 260px;"
                  />
                  <a-select v-model="manualBanLevel" style="width: 150px;">
                    <a-option value="permanent">永久封禁</a-option>
                    <a-option value="temp_24h">临时 24h</a-option>
                    <a-option value="temp_10m">临时 10 分钟</a-option>
                    <a-option value="ratelimit">限速</a-option>
                  </a-select>
                  <a-button
                    type="primary"
                    status="danger"
                    :loading="manualBanLoading"
                    @click="handleBanIp"
                  >
                    封禁
                  </a-button>
                </a-space>
              </a-card>

              <!-- 当前封禁列表 -->
              <a-table
                :data="fail2ban.bans"
                :loading="banLoading"
                :pagination="false"
                :scroll="{ y: 380 }"
                style="margin-top: 16px;"
              >
                <template #columns>
                  <a-table-column title="IP 地址" data-index="ip" :width="140" />
                  <a-table-column title="等级" :width="100" >
                    <template #cell="{ record }">
                      <a-tag :color="levelMap[record.level] ? levelMap[record.level].color : 'gray'">
                        {{ levelMap[record.level] ? levelMap[record.level].text : record.level }}
                      </a-tag>
                    </template>
                  </a-table-column>
                  <a-table-column title="原因" data-index="reason"  :width="170" />
                  <a-table-column title="来源" :width="80" >
                    <template #cell="{ record }">
                      <a-tag :color="sourceMap[record.source] ? sourceMap[record.source].color : 'gray'">
                        {{ sourceMap[record.source] ? sourceMap[record.source].text : record.source }}
                      </a-tag>
                    </template>
                  </a-table-column>
                  <a-table-column title="访问路径" :width="240" >
                    <template #cell="{ record }">
                      <span v-if="!(record.paths && record.paths.length)">-</span>
                      <span v-else>
                        {{ record.paths.slice(0, 3).join('、') }}<template v-if="record.paths.length > 3">…</template>
                      </span>
                    </template>
                  </a-table-column>
                  <a-table-column title="封禁时间" data-index="banned_at" :width="110" />
                  <a-table-column title="过期时间" data-index="expire_at" :width="110" />
                  <a-table-column title="累计次数" data-index="count" :width="70" />
                  <a-table-column title="操作" fixed="right" :width="140" >
                    <template #cell="{ record }">
                      <a-space>
                        <a-button type="text" size="small" @click="handleUnbanIp(record.ip)">解封</a-button>
                        <a-button
                          v-if="record.level !== 'permanent'"
                          type="text"
                          size="small"
                          status="danger"
                          @click="handlePermanent(record.ip)"
                        >
                          永久封禁
                        </a-button>
                      </a-space>
                    </template>
                  </a-table-column>
                </template>
              </a-table>
            </a-card>
          </a-grid-item>
        </a-grid>
      </a-tab-pane>

      <!-- 系统安全标签页 -->
      <a-tab-pane key="system" title="UFW 防火墙">
        <a-card title="系统防火墙" hoverable>
          <template #extra>
            <a-space>
              <a-switch :model-value="firewall.active" @change="handleFirewallToggle" :loading="loading.firewall" />
              <a-button type="primary" size="small" @click="showAddRuleModal = true">
                <template #icon><icon-plus /></template>
                添加规则
              </a-button>
            </a-space>
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
              <a-table-column title="备注" data-index="description" />
              <a-table-column title="操作" :width="100">
                <template #cell="{ record }">
                  <a-button type="text" status="danger" size="small" @click="handleDeleteFirewallRule(record)">删除</a-button>
                </template>
              </a-table-column>
            </template>
          </a-table>
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

    <!-- 请求频率限制 帮助说明 -->
    <a-modal v-model:visible="showRateHelp" title="请求频率限制 · 帮助说明" :footer="false">
      <a-typography-paragraph>
        <strong>调整建议：</strong>
      </a-typography-paragraph>
      <a-typography-paragraph>
        · 非 Elementor 等轻量站点：请求频率限制 30-60 次/分钟，突发缓冲 30-120。<br />
        · Elementor / 多插件重型站点：请求频率限制 60-120 次/分钟，突发缓冲 150-300。
      </a-typography-paragraph>
      <a-typography-paragraph>
        <strong>测试方法：</strong>
      </a-typography-paragraph>
      <a-typography-paragraph>
        开启后使用无痕窗口（未登录）连续刷新页面或批量请求，观察是否返回 429；已登录管理员用户不受影响。
        触发阈值后该 IP 将自动进入 Fail2ban 封禁列表。请务必预留足够突发缓冲，避免误封正常访客。
      </a-typography-paragraph>
    </a-modal>

    <!-- 爬虫限速 帮助说明 -->
    <a-modal v-model:visible="showBotHelp" title="爬虫限速 · 帮助说明" :footer="false">
      <a-typography-paragraph>
        <strong>适用场景：</strong>
      </a-typography-paragraph>
      <a-typography-paragraph>
        用于压制多 IP 假爬虫持续扫站，避免打满 WordPress 动态 404，保护服务器资源。
      </a-typography-paragraph>
      <a-typography-paragraph>
        <strong>豁免规则：</strong>
      </a-typography-paragraph>
      <a-typography-paragraph>
        Googlebot / Bingbot 仅在来源 IP 属于官方段时豁免；假冒搜索爬虫会进入限速桶。
        普通浏览器 UA 不受此层限速影响。每个站点独立限速，同一站点内常见 Bot UA 共享该站点的限速桶。
      </a-typography-paragraph>
    </a-modal>

    <!-- 添加防火墙规则弹窗 -->
    <a-modal v-model:visible="showAddRuleModal" title="添加防火墙规则" :ok-loading="addingRule" @ok="handleAddFirewallRule">
      <a-form layout="vertical">
        <a-form-item label="端口" help="需要开放的端口号，例如 8080">
          <a-input-number v-model="addRulePort" :min="1" :max="65535" style="width: 100%;" />
        </a-form-item>
        <a-form-item label="协议">
          <a-select v-model="addRuleProtocol" style="width: 100%;">
            <a-option value="tcp">TCP</a-option>
            <a-option value="udp">UDP</a-option>
          </a-select>
        </a-form-item>
        <a-form-item label="备注" help="给该端口规则添加一个备注说明（可选）">
          <a-input v-model="addRuleComment" placeholder="例如：网站管理后台" allow-clear />
        </a-form-item>
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

const showRateHelp = ref(false)
const showBotHelp = ref(false)

const banLoading = ref(false)
const manualBanIp = ref('')
const manualBanLevel = ref('permanent')
const manualBanLoading = ref(false)
const restarting = ref(false)

const levelMap = {
  permanent: { text: '永久封禁', color: 'red' },
  temp_24h: { text: '临时 24h', color: 'orange' },
  temp_10m: { text: '临时 10 分钟', color: 'arcoblue' },
  ratelimit: { text: '限速', color: 'purple' }
}

const sourceMap = {
  web: { text: 'Web 防护', color: 'blue' },
  '404': { text: '404 防御', color: 'cyan' },
  ssh: { text: 'SSH 防护', color: 'green' },
  panel_scan: { text: '面板扫描防御', color: 'magenta' },
  manual: { text: '手动封禁', color: 'red' }
}

const ratelimit = reactive({
  enabled: false,
  limit_per_minute: 60,
  burst: 300,
  last_updated: null
})
const botRatelimit = reactive({
  enabled: false,
  bot_limit_per_minute: 30,
  bot_burst: 20,
  last_updated: null
})
const whitelist = reactive({
  official: [],
  custom: [],
  paths: [],
  last_updated: ''
})
const customWhitelistText = ref('')
const pathWhitelistText = ref('')

const savingRatelimit = ref(false)
const savingBotRatelimit = ref(false)
const whitelistRefreshing = ref(false)
const customSaving = ref(false)
const pathSaving = ref(false)

const firewall = reactive({
  active: false,
  rules: []
})

const showAddRuleModal = ref(false)
const addRulePort = ref(80)
const addRuleProtocol = ref('tcp')
const addRuleComment = ref('')
const addingRule = ref(false)

const fail2ban = reactive({
  active: false,
  banned_ips: [],
  bans: [],
  config: {
    bantime: 600,
    findtime: 600,
    maxretry: 5
  }
})

const fetchData = async () => {
  try {
    const fw = await request.get('/security/firewall/status')
    Object.assign(firewall, fw)
    
    const f2b = await request.get('/security/fail2ban/status')
    Object.assign(fail2ban, f2b)

    const sitesRes = await request.get('/sites/')
    sites.value = sitesRes

    const rl = await request.get('/security/ratelimit')
    Object.assign(ratelimit, rl)

    const bot = await request.get('/security/bot-ratelimit')
    Object.assign(botRatelimit, bot)

    const wl = await request.get('/security/whitelist')
    Object.assign(whitelist, wl)
    customWhitelistText.value = (wl.custom || []).join('\n')
    pathWhitelistText.value = (wl.paths || []).join('\n')
  } catch (error) {
    console.error(error)
  }
}

const handleSaveRatelimit = async () => {
  savingRatelimit.value = true
  try {
    await request.post('/security/ratelimit', {
      enabled: ratelimit.enabled,
      limit_per_minute: ratelimit.limit_per_minute,
      burst: ratelimit.burst
    })
    Message.success('限速设置已保存')
    fetchData()
  } catch (error) {
    Message.error('保存失败')
  } finally {
    savingRatelimit.value = false
  }
}

const handleSaveBotRatelimit = async () => {
  savingBotRatelimit.value = true
  try {
    await request.post('/security/bot-ratelimit', {
      enabled: botRatelimit.enabled,
      bot_limit_per_minute: botRatelimit.bot_limit_per_minute,
      bot_burst: botRatelimit.bot_burst
    })
    Message.success('爬虫限速已保存')
    fetchData()
  } catch (error) {
    Message.error('保存失败')
  } finally {
    savingBotRatelimit.value = false
  }
}

const handleRefreshWhitelist = async () => {
  whitelistRefreshing.value = true
  try {
    const res = await request.post('/security/whitelist/refresh')
    Object.assign(whitelist, res.whitelist)
    Message.success('官方白名单已更新')
  } catch (error) {
    Message.error('拉取失败')
  } finally {
    whitelistRefreshing.value = false
  }
}

const handleSaveCustomWhitelist = async () => {
  customSaving.value = true
  try {
    const custom = customWhitelistText.value.split('\n').map(s => s.trim()).filter(Boolean)
    const res = await request.post('/security/whitelist/custom', { custom })
    Object.assign(whitelist, res.whitelist)
    customWhitelistText.value = (res.whitelist.custom || []).join('\n')
    Message.success('自定义白名单已保存')
  } catch (error) {
    Message.error('保存失败')
  } finally {
    customSaving.value = false
  }
}

const handleSavePathWhitelist = async () => {
  pathSaving.value = true
  try {
    const paths = pathWhitelistText.value.split('\n').map(s => s.trim()).filter(Boolean)
    const res = await request.post('/security/whitelist/paths', { paths })
    Object.assign(whitelist, res.whitelist)
    pathWhitelistText.value = (res.whitelist.paths || []).join('\n')
    Message.success('路径白名单已保存')
  } catch (error) {
    Message.error('保存失败')
  } finally {
    pathSaving.value = false
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

const handleAddFirewallRule = async () => {
  if (!addRulePort.value) {
    Message.warning('请输入端口号')
    return
  }
  addingRule.value = true
  try {
    await request.post('/security/firewall/rule', null, {
      params: { port: addRulePort.value, protocol: addRuleProtocol.value, comment: addRuleComment.value || undefined }
    })
    Message.success(`已开放端口 ${addRulePort.value}/${addRuleProtocol.value}`)
    showAddRuleModal.value = false
    addRuleComment.value = ''
    fetchData()
  } catch (error) {
    Message.error('添加失败')
  } finally {
    addingRule.value = false
  }
}

const handleDeleteFirewallRule = async (record) => {
  try {
    await request.post('/security/firewall/rule/delete', null, {
      params: { port: record.port, protocol: record.protocol }
    })
    Message.success(`已删除端口 ${record.port}/${record.protocol} 规则`)
    fetchData()
  } catch (error) {
    Message.error('删除失败')
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

const handleBanIp = async () => {
  const ip = manualBanIp.value.trim()
  if (!ip) {
    Message.warning('请输入要封禁的 IP 地址')
    return
  }
  manualBanLoading.value = true
  try {
    await request.post('/security/fail2ban/ban', null, {
      params: { ip, level: manualBanLevel.value, source: 'manual' }
    })
    Message.success(`IP ${ip} 已封禁`)
    manualBanIp.value = ''
    fetchData()
  } catch (error) {
    Message.error('操作失败')
  } finally {
    manualBanLoading.value = false
  }
}

const handlePermanent = async (ip) => {
  try {
    await request.post('/security/fail2ban/permanent', null, { params: { ip } })
    Message.success(`IP ${ip} 已设为永久封禁`)
    fetchData()
  } catch (error) {
    Message.error('操作失败')
  }
}

const handleStartFail2ban = async () => {
  restarting.value = true
  try {
    await request.post('/security/fail2ban/start')
    Message.success('Fail2ban 已启动')
    fetchData()
  } catch (error) {
    Message.error('启动失败')
  } finally {
    restarting.value = false
  }
}

const handleUpdateF2bConfig = async () => {
  try {
    await request.post('/security/fail2ban/config', fail2ban.config)
    Message.success('封禁策略已更新')
    fetchData()
  } catch (error) {
    Message.error('策略更新失败')
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
  .whitelist-sub {
    background-color: var(--color-fill-1);
    .whitelist-updated {
      margin-top: 10px;
      font-size: 12px;
      color: var(--color-text-3);
    }
    .whitelist-help {
      margin-top: 8px;
      font-size: 12px;
      color: var(--color-text-3);
      line-height: 1.6;
    }
  }
  .manual-ban-card {
    background-color: var(--color-fill-1);
    margin-bottom: 4px;
  }
  .setting-card {
    height: 100%;
    :deep(.arco-card-body) {
      display: flex;
      flex-direction: column;
      height: 100%;
    }
    :deep(.arco-card-body > .arco-btn) {
      margin-top: auto;
    }
  }
}
</style>
