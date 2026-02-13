<template>
  <div class="website-detail">
    <div class="header">
      <a-space size="large">
        <a-button @click="router.back()">
          <template #icon><icon-left /></template>
          返回列表
        </a-button>
        <a-typography-title :heading="3" style="margin: 0">
          {{ site.domain }}
        </a-typography-title>
        <a-tag :color="site.status === 'active' ? 'green' : 'red'">
          {{ site.status === 'active' ? '运行中' : '已停止' }}
        </a-tag>
      </a-space>
    </div>

    <a-tabs default-active-key="overview" class="detail-tabs">
      <!-- 概览页 -->
      <a-tab-pane key="overview" title="概览">
        <a-row :gutter="16">
          <a-col :span="6">
            <a-card title="速度评分" :bordered="false">
              <div class="score-display">
                <a-progress type="circle" :percent="site.speed_score / 100" :color="getScoreColor(site.speed_score)" />
                <div class="score-label">PageSpeed 移动端</div>
              </div>
            </a-card>
          </a-col>
          <a-col :span="6">
            <a-card title="缓存命中率" :bordered="false">
              <div class="score-display">
                <a-progress type="circle" :percent="0.98" color="#00b42a" />
                <div class="score-label">整体命中率 (LSCache + Redis)</div>
              </div>
            </a-card>
          </a-col>
          <a-col :span="12">
            <a-card title="站点信息" :bordered="false">
              <a-descriptions :data="siteInfo" :column="1" />
            </a-card>
          </a-col>
        </a-row>
      </a-tab-pane>

      <!-- 域名与 SSL -->
      <a-tab-pane key="ssl" title="域名与 SSL">
        <a-card :bordered="false">
          <a-typography-title :heading="5">域名管理</a-typography-title>
          <a-table :data="domainList" :pagination="false">
            <template #columns>
              <a-table-column title="域名" data-index="domain" />
              <a-table-column title="类型" data-index="type" />
              <a-table-column title="操作">
                <template #cell>
                  <a-button type="text" size="small">删除</a-button>
                </template>
              </a-table-column>
            </template>
          </a-table>
          <div style="margin-top: 16px">
            <a-button type="outline" size="small">添加域名</a-button>
          </div>

          <a-divider />

          <a-typography-title :heading="5">SSL 证书 (Let's Encrypt)</a-typography-title>
          <a-space direction="vertical" fill>
            <a-alert v-if="site.ssl_enabled" type="success">
              SSL 证书已生效。有效期至: 2026-05-13 (剩余 89 天)
            </a-alert>
            <a-alert v-else type="warning">
              当前未开启 SSL 加密，建议立即申请以保障访问安全。
            </a-alert>
            <a-space>
              <a-button type="primary" :loading="sslLoading" @click="handleApplySSL">
                {{ site.ssl_enabled ? '重签证书' : '立即申请' }}
              </a-button>
              <a-button v-if="site.ssl_enabled" status="danger">关闭 SSL</a-button>
            </a-space>
          </a-space>
        </a-card>
      </a-tab-pane>

      <!-- 缓存设置 -->
      <a-tab-pane key="cache" title="缓存设置">
        <a-card :bordered="false">
          <div class="optimization-card">
            <div class="opt-header">
              <icon-check-circle-fill class="opt-icon" />
              <span class="opt-title">WordPress 专项性能优化已开启</span>
            </div>
            <p class="opt-desc">
              当前站点正在使用“极致性能”预设。系统已自动配置 OpenLiteSpeed 页面缓存、Redis 对象缓存、浏览器长效缓存及静态资源合并压缩。
            </p>
          </div>
          
          <a-divider />
          
          <a-form layout="vertical">
            <a-form-item label="全站缓存开关">
              <a-switch default-checked />
            </a-form-item>
            <a-form-item label="缓存模式调整">
              <a-slider :marks="{ 0: '兼容', 50: '均衡', 100: '极速' }" :step="50" default-value="100" style="width: 400px" />
              <div class="form-help">
                切换模式后，系统将自动调整 LSCache 规则及 Redis 缓存策略。
              </div>
            </a-form-item>
            <a-form-item>
              <a-button type="primary" status="success" @click="handlePurgeCache">
                <template #icon><icon-empty /></template>
                立即清理全站缓存
              </a-button>
            </a-form-item>
          </a-form>
        </a-card>
      </a-tab-pane>

      <!-- 高级设置 -->
      <a-tab-pane key="advanced" title="高级设置">
        <a-collapse :bordered="false">
          <a-collapse-item header="PHP 设置 (php.ini)" key="php">
            <a-typography-text type="secondary">在此预览或快速修改常用 PHP 参数</a-typography-text>
            <a-form layout="vertical" style="margin-top: 16px">
              <a-row :gutter="16">
                <a-col :span="8">
                  <a-form-item label="memory_limit">
                    <a-input v-model="phpConfig.memory_limit" />
                  </a-form-item>
                </a-col>
                <a-col :span="8">
                  <a-form-item label="post_max_size">
                    <a-input v-model="phpConfig.post_max_size" />
                  </a-form-item>
                </a-col>
                <a-col :span="8">
                  <a-form-item label="max_execution_time">
                    <a-input v-model="phpConfig.max_execution_time" />
                  </a-form-item>
                </a-col>
              </a-row>
              <a-button type="outline">保存 PHP 配置</a-button>
            </a-form>
          </a-collapse-item>
          <a-collapse-item header="OpenLiteSpeed 虚拟主机配置" key="ols">
            <a-typography-text type="secondary">仅供参考，手动修改可能导致面板管理失效</a-typography-text>
            <pre class="config-preview">
docRoot                   $VH_ROOT/html/
vhDomain                  $VH_NAME
vhAliases                 www.$VH_NAME
index {
  useServer               0
  indexFiles              index.php, index.html
}
            </pre>
          </a-collapse-item>
        </a-collapse>
      </a-tab-pane>
    </a-tabs>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import request from '@/utils/request'
import { Message } from '@arco-design/web-vue'
import { IconLeft, IconCheckCircleFill, IconEmpty } from '@arco-design/web-vue/es/icon'

const route = useRoute()
const router = useRouter()
const siteId = route.params.id

const site = ref({
  domain: '',
  status: 'active',
  speed_score: 95,
  ssl_enabled: true,
  php_version: '8.2',
  root_path: ''
})

const sslLoading = ref(false)

const siteInfo = computed(() => [
  { label: 'PHP 版本', value: site.value.php_version },
  { label: '根目录', value: site.value.root_path },
  { label: '创建时间', value: '2024-08-13' },
  { label: '数据库', value: '默认 MariaDB' }
])

const domainList = computed(() => [
  { domain: site.value.domain, type: '主域名' },
  { domain: `www.${site.value.domain}`, type: '别名' }
])

const phpConfig = reactive({
  memory_limit: '256M',
  post_max_size: '64M',
  max_execution_time: '300'
})

const getScoreColor = (score) => {
  if (score >= 90) return '#00b42a'
  if (score >= 60) return '#ff7d00'
  return '#f53f3f'
}

const fetchSiteDetail = async () => {
  try {
    const res = await request.get(`/sites/${siteId}`)
    site.value = res
  } catch (error) {
    Message.error('获取站点详情失败')
  }
}

const handleApplySSL = async () => {
  sslLoading.value = true
  try {
    await request.post(`/sites/${siteId}/ssl`)
    Message.success('SSL 配置成功')
    fetchSiteDetail()
  } catch (error) {
    Message.error('SSL 配置失败')
  } finally {
    sslLoading.value = false
  }
}

const handlePurgeCache = async () => {
  try {
    await request.post(`/sites/${siteId}/purge-cache`)
    Message.success('全站缓存已清理')
  } catch (error) {
    Message.error('缓存清理失败')
  }
}

onMounted(() => {
  fetchSiteDetail()
})
</script>

<style scoped>
.website-detail {
  padding: 20px;
}
.header {
  margin-bottom: 24px;
}
.detail-tabs {
  background: #fff;
  padding: 16px;
  border-radius: 8px;
}
.score-display {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 16px 0;
}
.score-label {
  margin-top: 12px;
  font-size: 12px;
  color: var(--color-text-3);
}
.optimization-card {
  padding: 16px;
  background-color: var(--color-fill-1);
  border-radius: 8px;
  border-left: 4px solid var(--color-success);
}
.opt-header {
  display: flex;
  align-items: center;
  margin-bottom: 8px;
}
.opt-icon {
  color: var(--color-success);
  font-size: 18px;
  margin-right: 8px;
}
.opt-title {
  font-weight: 600;
  color: var(--color-text-1);
}
.opt-desc {
  color: var(--color-text-2);
  margin: 0;
  font-size: 13px;
  line-height: 1.6;
}
.form-help {
  font-size: 12px;
  color: var(--color-text-3);
  margin-top: 8px;
}
.config-preview {
  background: #1e1e1e;
  color: #d4d4d4;
  padding: 16px;
  border-radius: 4px;
  font-family: monospace;
  font-size: 12px;
  overflow-x: auto;
}
</style>
