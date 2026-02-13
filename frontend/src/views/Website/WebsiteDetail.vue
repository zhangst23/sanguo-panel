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
          <div class="setting-row">
            <a-typography-title :heading="5" style="margin: 0">域名管理</a-typography-title>
          </div>
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

          <div class="setting-row" style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
            <a-typography-title :heading="5" style="margin: 0">SSL 证书 (Let's Encrypt)</a-typography-title>
            <a-space>
              <span style="font-size: 14px; color: var(--color-text-2);">HTTPS</span>
              <a-switch v-model="site.https_force" type="round" @change="handleUpdateSite({ https_force: $event })">
                <template #checked>开启</template>
                <template #unchecked>关闭</template>
              </a-switch>
              <span style="font-size: 12px; color: #165dff;">(默认开启)</span>
            </a-space>
          </div>

          <a-radio-group v-model="site.ssl_mode" direction="vertical" style="width: 100%" @change="handleUpdateSite({ ssl_mode: $event })">
            <!-- 选项 1: Cloudflare -->
            <a-radio value="cloudflare" class="ssl-radio-item">
              <div class="ssl-option-content">
                <div class="ssl-option-title">不设置，去 Cloudflare 设置 SSL</div>
                <div class="ssl-option-desc">适用于使用 Cloudflare CDN 的站点，由 Cloudflare 提供端到端加密。</div>
              </div>
            </a-radio>

            <!-- 选项 2: Let's Encrypt -->
            <a-radio value="letsencrypt" class="ssl-radio-item">
              <div class="ssl-option-content">
                <div class="ssl-option-title">一键申请 Let's Encrypt 证书</div>
                <div class="ssl-option-desc">免费、自动化的证书申请服务，由本面板自动管理。</div>
                
                <div v-if="site.ssl_mode === 'letsencrypt'" class="ssl-form-inline" @click.stop>
                  <a-space direction="vertical" size="medium" style="width: 100%; margin-top: 12px;">
                    <a-input v-model="site.ssl_email" placeholder="请输入通知邮箱 (用于接收证书到期提醒)" style="width: 320px">
                      <template #prepend>邮箱</template>
                    </a-input>
                    <a-checkbox v-model="site.ssl_auto_renew" @change="handleUpdateSite({ ssl_auto_renew: $event })">
                      自动续费 (默认勾选)
                    </a-checkbox>
                    <a-button type="primary" size="small" :loading="sslLoading" @click="handleApplySSL">
                      立即申请 / 重签
                    </a-button>
                  </a-space>
                </div>
              </div>
            </a-radio>

            <!-- 选项 3: 关闭 -->
            <a-radio value="none" class="ssl-radio-item">
              <div class="ssl-option-content">
                <div class="ssl-option-title">暂不配置 SSL</div>
                <div class="ssl-option-desc">站点将仅支持 HTTP 访问。</div>
              </div>
            </a-radio>
          </a-radio-group>

          <div v-if="site.ssl_mode === 'letsencrypt' && site.ssl_expire_at" style="margin-top: 20px;">
            <a-alert type="success">
              SSL 证书已生效。有效期至: {{ site.ssl_expire_at }}
            </a-alert>
          </div>
        </a-card>
      </a-tab-pane>

      <!-- 性能优化 (原缓存设置) -->
      <a-tab-pane key="cache" title="性能优化">
        <a-card :bordered="false">
          <div class="optimization-card">
            <div class="opt-header">
              <icon-check-circle-fill class="opt-icon" />
              <span class="opt-title">性能加速引擎已就绪</span>
            </div>
            <p class="opt-desc">
              系统已根据“极致性能”预设为您配置了以下优化项。您可以根据需求手动微调。
            </p>
          </div>
          
          <a-divider />
          
          <div class="performance-grid">
            <div class="perf-item">
              <div class="perf-info">
                <div class="perf-name">OpenLiteSpeed 技术底座 <a-tag size="mini" color="blue" bordered>核心</a-tag></div>
                <div class="perf-desc">使用高性能 LSCache 引擎，响应速度提升 3-5 倍</div>
              </div>
              <a-switch :model-value="true" disabled />
            </div>

            <div class="perf-item">
              <div class="perf-info">
                <div class="perf-name">MariaDB 专属优化 <a-tag size="mini" color="blue" bordered>核心</a-tag></div>
                <div class="perf-desc">针对数据库查询索引、缓存及连接池深度调优</div>
              </div>
              <a-switch :model-value="true" disabled />
            </div>

            <div class="perf-item">
              <div class="perf-info">
                <div class="perf-name">Redis 对象缓存 <a-tag size="mini" color="blue" bordered>核心</a-tag></div>
                <div class="perf-desc">减少数据库压力，毫秒级读取常用数据对象</div>
              </div>
              <a-switch :model-value="true" disabled />
            </div>

            <div class="perf-item">
              <div class="perf-info">
                <div class="perf-name">OPcache 深度优化 <a-tag size="mini" color="blue" bordered>核心</a-tag></div>
                <div class="perf-desc">PHP 脚本字节码缓存，消除重复编译开销</div>
              </div>
              <a-switch :model-value="true" disabled />
            </div>

            <div class="perf-item">
              <div class="perf-info">
                <div class="perf-name">浏览器缓存</div>
                <div class="perf-desc">配置静态资源长效缓存，减少重复请求流量</div>
              </div>
              <a-switch v-model="site.browser_cache_enabled" @change="handleUpdateSite({ browser_cache_enabled: $event })" />
            </div>

            <div class="perf-item">
              <div class="perf-info">
                <div class="perf-name">全站静态化</div>
                <div class="perf-desc">将动态页面生成静态 HTML，应对高并发访问</div>
              </div>
              <a-switch v-model="site.static_optimization" @change="handleUpdateSite({ static_optimization: $event })" />
            </div>

            <div class="perf-item">
              <div class="perf-info">
                <div class="perf-name">图片自动化压缩</div>
                <div class="perf-desc">无损压缩 WebP 格式，大幅缩短页面首屏加载时间</div>
              </div>
              <a-switch v-model="site.image_optimization" @change="handleUpdateSite({ image_optimization: $event })" />
            </div>

            <div class="perf-item">
              <div class="perf-info">
                <div class="perf-name">CSS/JS 合并</div>
                <div class="perf-desc">合并压缩前端资源，减少 HTTP 请求次数</div>
              </div>
              <a-switch v-model="site.assets_optimization" @change="handleUpdateSite({ assets_optimization: $event })" />
            </div>
          </div>

          <a-divider />
          
          <div style="text-align: center;">
            <a-button type="primary" status="success" size="large" @click="handlePurgeCache">
              <template #icon><icon-empty /></template>
              立即清理全站缓存
            </a-button>
          </div>
        </a-card>
      </a-tab-pane>

      <!-- 高级设置 -->
      <a-tab-pane key="advanced" title="高级设置">
        <a-collapse :bordered="false" default-active-key="wp">
          <a-collapse-item header="wp-config.php 配置管理" key="wp">
            <a-typography-text type="secondary">在此修改 WordPress 核心配置文件，修改前请确保了解各参数含义</a-typography-text>
            <div style="margin-top: 16px">
              <a-textarea 
                v-model="wpConfigContent" 
                :auto-size="{ minRows: 10, maxRows: 20 }" 
                style="font-family: monospace; background-color: #f8f9fa"
                placeholder="正在加载 wp-config.php 内容..."
              />
              <div style="margin-top: 16px">
                <a-button type="primary" @click="saveWpConfig" :loading="wpConfigLoading">
                  保存 wp-config 配置
                </a-button>
                <a-button type="outline" style="margin-left: 12px" @click="fetchWpConfig">
                  重置/刷新
                </a-button>
              </div>
            </div>
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
  ssl_mode: 'none',
  ssl_email: '',
  ssl_auto_renew: true,
  https_force: true,
  lscache_enabled: true,
  mariadb_optimized: true,
  redis_enabled: true,
  opcache_enabled: true,
  browser_cache_enabled: true,
  static_optimization: true,
  image_optimization: true,
  assets_optimization: true,
  php_version: '8.2',
  root_path: '',
  ssl_expire_at: ''
})

const sslLoading = ref(false)

const siteInfo = computed(() => [
  { label: 'PHP 版本', value: site.value.php_version || '-' },
  { label: '根目录', value: site.value.root_path || '-' },
  { label: '创建时间', value: site.value.created_at ? new Date(site.value.created_at).toLocaleDateString() : '-' },
  { label: '数据库', value: '默认 MariaDB' }
])

const domainList = computed(() => [
  { domain: site.value.domain, type: '主域名' },
  { domain: `www.${site.value.domain}`, type: '别名' }
])

const wpConfigContent = ref('')
const wpConfigLoading = ref(false)

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

const fetchWpConfig = async () => {
  wpConfigLoading.value = true
  try {
    const res = await request.get(`/sites/${siteId}/wp-config`)
    wpConfigContent.value = res.content
  } catch (error) {
    // 如果不是 WordPress 站点，可能会报错，静默处理或提示
    console.error('获取 wp-config.php 失败:', error)
  } finally {
    wpConfigLoading.value = false
  }
}

const saveWpConfig = async () => {
  wpConfigLoading.value = true
  try {
    await request.post(`/sites/${siteId}/wp-config`, { content: wpConfigContent.value })
    Message.success('wp-config.php 已保存')
  } catch (error) {
    Message.error('保存失败: ' + (error.response?.data?.detail || error.message))
  } finally {
    wpConfigLoading.value = false
  }
}

const handleUpdateSite = async (data) => {
  try {
    await request.put(`/sites/${siteId}`, data)
    Message.success('配置已更新')
  } catch (error) {
    Message.error('更新配置失败')
  }
}

const handleApplySSL = async () => {
  if (site.value.ssl_mode === 'letsencrypt' && !site.value.ssl_email) {
    Message.error('请先输入通知邮箱')
    return
  }
  
  sslLoading.value = true
  try {
    await request.post(`/sites/${siteId}/ssl`, {
      email: site.value.ssl_email,
      auto_renew: site.value.ssl_auto_renew
    })
    Message.success('SSL 证书申请成功')
    fetchSiteDetail()
  } catch (error) {
    Message.error('SSL 证书申请失败')
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
  fetchWpConfig()
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
  background: var(--color-fill-2);
  padding: 12px;
  border-radius: 4px;
  font-family: monospace;
  font-size: 13px;
  color: var(--color-text-2);
}

.ssl-radio-item {
  padding: 12px;
  border: 1px solid var(--color-fill-3);
  border-radius: 8px;
  margin-bottom: 12px;
  transition: all 0.2s;
  width: 100%;
}

.ssl-radio-item:hover {
  background: var(--color-fill-1);
}

.arco-radio-checked.ssl-radio-item {
  border-color: rgb(var(--arcoblue-6));
  background: var(--color-primary-light-1);
}

.ssl-option-content {
  margin-left: 8px;
}

.ssl-option-title {
  font-weight: 500;
  font-size: 14px;
  color: var(--color-text-1);
  margin-bottom: 4px;
}

.ssl-option-desc {
  font-size: 12px;
  color: var(--color-text-3);
}

.ssl-form-inline {
  background: #fff;
  padding: 12px;
  border-radius: 4px;
  border: 1px dashed var(--color-fill-3);
}

.performance-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 20px;
}

.perf-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px;
  background: var(--color-fill-1);
  border-radius: 8px;
  border: 1px solid var(--color-fill-2);
  transition: all 0.2s;
}

.perf-item:hover {
  background: var(--color-fill-2);
  border-color: var(--color-fill-3);
}

.perf-info {
  flex: 1;
  margin-right: 16px;
}

.perf-name {
  font-weight: 500;
  font-size: 14px;
  color: var(--color-text-1);
  margin-bottom: 4px;
}

.perf-desc {
  font-size: 12px;
  color: var(--color-text-3);
  line-height: 1.4;
}
</style>
