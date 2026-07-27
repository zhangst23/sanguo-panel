<template>
  <div class="wp-runtime">
    <!-- 顶部：标题 + 控制 -->
    <div class="wp-header">
      <div>
        <div class="wp-title">
          <span class="wp-logo">W</span>
          WordPress 运行时可观测性
        </div>
        <div class="wp-subtitle">
          全栈 Runtime Observability · L1 指标采集 · L2 链路关联 · L3 AI 分析 · L4 自动优化
          <span v-if="data" class="wp-updated">更新于 {{ data.generated_at }}</span>
        </div>
      </div>
      <div class="wp-controls">
        <a-switch v-model="autoRefresh" @change="toggleAuto">
          <template #checked>自动刷新</template>
          <template #unchecked>手动</template>
        </a-switch>
        <a-button type="primary" :loading="loading" @click="fetchData">
          <template #icon><icon-refresh /></template>
          刷新
        </a-button>
      </div>
    </div>

    <a-spin :loading="loading && !data" tip="正在采集运行时指标...">
      <template v-if="data">
        <!-- L4 综合健康评分 -->
        <a-card class="wp-score-card" :bordered="false">
          <div class="wp-score-main">
            <div class="wp-score-ring" :style="{ '--c': gradeColor(data.score.grade) }">
              <div class="wp-score-num">{{ data.score.total }}</div>
              <div class="wp-score-grade">{{ data.score.grade }} 级</div>
            </div>
            <div class="wp-score-meta">
              <div class="wp-score-label">综合性能评分 (L4 Health)</div>
              <div class="wp-score-desc">{{ aiSummary }}</div>
              <div class="wp-kpi-row">
                <div class="wp-kpi">
                  <div class="wp-kpi-v">{{ data.request.qps }}</div>
                  <div class="wp-kpi-l">QPS</div>
                </div>
                <div class="wp-kpi">
                  <div class="wp-kpi-v">{{ data.request.p95 }}<i>ms</i></div>
                  <div class="wp-kpi-l">P95 延迟</div>
                </div>
                <div class="wp-kpi">
                  <div class="wp-kpi-v">{{ data.request.avg }}<i>ms</i></div>
                  <div class="wp-kpi-l">平均 TTFB</div>
                </div>
                <div class="wp-kpi">
                  <div class="wp-kpi-v">{{ data.cache.overall_hit }}<i>%</i></div>
                  <div class="wp-kpi-l">缓存命中</div>
                </div>
                <div class="wp-kpi">
                  <div class="wp-kpi-v" :class="errClass">{{ data.request.error_rate }}<i>%</i></div>
                  <div class="wp-kpi-l">错误率</div>
                </div>
              </div>
            </div>
          </div>
          <a-divider direction="vertical" class="wp-divider" />
          <div class="wp-score-grid">
            <div
              v-for="(c, key) in data.score.components"
              :key="key"
              class="wp-comp"
              :style="{ '--c': scoreColor(c.score) }"
            >
              <a-progress
                type="circle"
                :percent="c.score"
                :size="46"
                :stroke-color="scoreColor(c.score)"
                :trail-color="'rgba(255,255,255,0.08)'"
              />
              <div class="wp-comp-meta">
                <div class="wp-comp-label">{{ c.label }}</div>
                <a-tag :color="c.source === 'real' ? 'green' : 'gray'" size="small" class="wp-comp-src">
                  {{ c.source === 'real' ? '真实' : '模拟' }}
                </a-tag>
              </div>
            </div>
          </div>
        </a-card>

        <!-- Runtime Performance Tree -->
        <a-tabs v-model:active-key="activeTab" class="wp-tabs" type="rounded">
          <!-- 请求监控 -->
          <a-tab-pane key="request" title="请求 Request">
            <a-row :gutter="16">
              <a-col :span="12">
                <a-card title="QPS 实时趋势" :bordered="false" class="wp-card">
                  <WpEchart :option="qpsOption" :height="240" />
                </a-card>
              </a-col>
              <a-col :span="12">
                <a-card title="P95 / P99 延迟" :bordered="false" class="wp-card">
                  <WpEchart :option="p95Option" :height="240" />
                </a-card>
              </a-col>
            </a-row>
            <a-row :gutter="16" class="wp-mt">
              <a-col :span="12">
                <a-card title="请求生命周期耗时分解 (L2)" :bordered="false" class="wp-card">
                  <WpEchart :option="lifecycleOption" :height="240" />
                  <a-alert class="wp-mt" type="info">{{ data.request.error_rate < 1 ? '请求链路健康，PHP 与数据库为耗时主要来源。' : '错误率偏高，建议查看「错误中心」。' }}</a-alert>
                </a-card>
              </a-col>
              <a-col :span="12">
                <a-card title="热门接口 TOP" :bordered="false" class="wp-card">
                  <a-table :columns="urlCols" :data="data.request.top_urls" :pagination="false" size="small" />
                </a-card>
              </a-col>
            </a-row>
            <a-row :gutter="16" class="wp-mt">
              <a-col :span="24">
                <a-card title="错误分布" :bordered="false" class="wp-card">
                  <a-space>
                    <a-tag color="red">500: {{ data.request.errors['500'] }}</a-tag>
                    <a-tag color="orange">404: {{ data.request.errors['404'] }}</a-tag>
                    <a-tag color="arcoblue">403: {{ data.request.errors['403'] }}</a-tag>
                  </a-space>
                </a-card>
              </a-col>
            </a-row>
          </a-tab-pane>

          <!-- 缓存 -->
          <a-tab-pane key="cache" title="缓存 Cache">
            <a-row :gutter="16">
              <a-col :span="8">
                <a-card title="整体命中率" :bordered="false" class="wp-card">
                  <WpEchart :option="cacheGaugeOption" :height="240" />
                  <a-alert class="wp-mt" type="warning">{{ data.cache.miss_reason }}</a-alert>
                </a-card>
              </a-col>
              <a-col :span="8">
                <a-card title="各层命中率" :bordered="false" class="wp-card">
                  <WpEchart :option="cacheLayerOption" :height="240" />
                </a-card>
              </a-col>
              <a-col :span="8">
                <a-card title="命中率趋势" :bordered="false" class="wp-card">
                  <WpEchart :option="cacheTrendOption" :height="240" />
                </a-card>
              </a-col>
            </a-row>
            <a-card class="wp-card wp-mt" title="AI 洞察" :bordered="false">
              <a-alert type="info">{{ data.cache.ai_tip }}</a-alert>
              <a-space class="wp-mt">
                <a-tag :color="data.cache.guest_mode ? 'green' : 'gray'">Guest Mode {{ data.cache.guest_mode ? '开' : '关' }}</a-tag>
                <a-tag :color="data.cache.esi ? 'green' : 'gray'">ESI {{ data.cache.esi ? '开' : '关' }}</a-tag>
                <a-tag color="arcoblue">LSCache Public {{ data.cache.public }}%</a-tag>
                <a-tag color="arcoblue">Private {{ data.cache.private }}%</a-tag>
                <a-tag color="arcoblue">Browser {{ data.cache.browser }}%</a-tag>
              </a-space>
            </a-card>
          </a-tab-pane>

          <!-- PHP -->
          <a-tab-pane key="php" title="PHP Runtime">
            <a-row :gutter="16">
              <a-col :span="12">
                <a-card title="OPcache 命中率" :bordered="false" class="wp-card">
                  <WpEchart :option="opcacheOption" :height="240" />
                </a-card>
              </a-col>
              <a-col :span="12">
                <a-card title="慢脚本 TOP (ms)" :bordered="false" class="wp-card">
                  <WpEchart :option="phpSlowOption" :height="240" />
                </a-card>
              </a-col>
            </a-row>
            <a-card class="wp-card wp-mt" title="真实运行时信号 (OLS / PHP)" :bordered="false">
              <a-descriptions :column="2" bordered size="small">
                <a-descriptions-item label="OpenLiteSpeed">
                  <a-tag :color="ols.running ? 'green' : 'red'">{{ ols.running ? '运行中' : '未运行' }}</a-tag>
                </a-descriptions-item>
                <a-descriptions-item label="OLS 版本">{{ ols.version || '未知' }}</a-descriptions-item>
                <a-descriptions-item label="PHP 版本">{{ phpReal.version || '未知' }}</a-descriptions-item>
                <a-descriptions-item label="OPcache">
                  <a-tag :color="phpReal.opcache_enabled ? 'green' : (phpReal.opcache_enabled === false ? 'orange' : 'gray')">
                    {{ phpReal.opcache_enabled === null ? '未探测' : (phpReal.opcache_enabled ? '已启用' : '未启用') }}
                  </a-tag>
                </a-descriptions-item>
                <a-descriptions-item label="OPcache 内存">{{ phpReal.opcache_total_mb != null ? phpReal.opcache_total_mb + ' MB' : '未知' }}</a-descriptions-item>
              </a-descriptions>
              <a-alert v-if="ols.error" class="wp-mt" type="warning">{{ ols.error }}</a-alert>
              <a-alert v-else-if="phpReal.error" class="wp-mt" type="warning">{{ phpReal.error }}</a-alert>
            </a-card>
            <a-row :gutter="16" class="wp-mt">
              <a-col :span="24">
                <a-card title="PHP 错误统计" :bordered="false" class="wp-card">
                  <a-space>
                    <a-tag color="red">Fatal {{ data.php.errors.fatal }}</a-tag>
                    <a-tag color="orange">Warning {{ data.php.errors.warning }}</a-tag>
                    <a-tag color="arcoblue">Notice {{ data.php.errors.notice }}</a-tag>
                    <a-tag color="gray">Deprecated {{ data.php.errors.deprecated }}</a-tag>
                    <a-tag color="green">平均执行 {{ data.php.avg_time }}ms</a-tag>
                  </a-space>
                </a-card>
              </a-col>
            </a-row>
          </a-tab-pane>

          <!-- Worker -->
          <a-tab-pane key="worker" title="进程 Worker">
            <a-row :gutter="16">
              <a-col :span="12">
                <a-card title="连接池利用率" :bordered="false" class="wp-card">
                  <WpEchart :option="workerGaugeOption" :height="240" />
                </a-card>
              </a-col>
              <a-col :span="12">
                <a-card title="进程状态" :bordered="false" class="wp-card">
                  <a-descriptions :column="2" bordered size="small">
                    <a-descriptions-item label="Worker 总数">{{ data.worker.total }}</a-descriptions-item>
                    <a-descriptions-item label="忙碌">{{ data.worker.busy.length }}</a-descriptions-item>
                    <a-descriptions-item label="空闲">{{ data.worker.idle.length }}</a-descriptions-item>
                    <a-descriptions-item label="排队">{{ data.worker.queue }}</a-descriptions-item>
                    <a-descriptions-item label="重启次数">{{ data.worker.restarts }}</a-descriptions-item>
                    <a-descriptions-item label="内存">{{ data.worker.memory_mb }} MB</a-descriptions-item>
                  </a-descriptions>
                  <a-alert class="wp-mt" type="warning">{{ data.worker.ai_tip }}</a-alert>
                </a-card>
              </a-col>
            </a-row>
          </a-tab-pane>

          <!-- 数据库 -->
          <a-tab-pane key="database" title="数据库 Database">
            <a-row :gutter="16">
              <a-col :span="12">
                <a-card title="查询 QPS 趋势" :bordered="false" class="wp-card">
                  <WpEchart :option="dbTrendOption" :height="240" />
                </a-card>
              </a-col>
              <a-col :span="12">
                <a-card title="慢表 TOP (ms)" :bordered="false" class="wp-card">
                  <WpEchart :option="dbTableOption" :height="240" />
                </a-card>
              </a-col>
            </a-row>
            <a-row :gutter="16" class="wp-mt">
              <a-col :span="24">
                <a-card title="慢查询 SQL (插件归属)" :bordered="false" class="wp-card">
                  <a-table :columns="sqlCols" :data="data.database.top_sql" :pagination="false" size="small">
                    <template #plugin="{ record }">
                      <a-tag color="purple">{{ record.plugin }}</a-tag>
                    </template>
                  </a-table>
                </a-card>
              </a-col>
            </a-row>
            <a-card class="wp-card wp-mt" title="真实 MariaDB 信号" :bordered="false">
              <a-descriptions :column="3" bordered size="small">
                <a-descriptions-item label="状态">
                  <a-tag :color="mariadb.running ? 'green' : 'red'">{{ mariadb.running ? '运行中' : '未连接' }}</a-tag>
                </a-descriptions-item>
                <a-descriptions-item label="连接数">{{ mariadb.threads_connected ?? '-' }} / {{ mariadb.max_connections ?? '-' }}</a-descriptions-item>
                <a-descriptions-item label="连接利用率">{{ mariadb.connection_util ?? '-' }}%</a-descriptions-item>
                <a-descriptions-item label="QPS (查询/秒)">{{ mariadb.qps ?? '-' }}</a-descriptions-item>
                <a-descriptions-item label="慢查询总数">{{ mariadb.slow_queries ?? '-' }}</a-descriptions-item>
                <a-descriptions-item label="慢查询率">{{ mariadb.slow_rate ?? '-' }}%</a-descriptions-item>
              </a-descriptions>
              <a-alert v-if="mariadb.error" class="wp-mt" type="warning">{{ mariadb.error }}</a-alert>
            </a-card>
          </a-tab-pane>

          <!-- Redis -->
          <a-tab-pane key="redis" title="Redis">
            <a-row :gutter="16">
              <a-col :span="8">
                <a-card title="命中 / 未命中" :bordered="false" class="wp-card">
                  <WpEchart :option="redisPieOption" :height="240" />
                </a-card>
              </a-col>
              <a-col :span="8">
                <a-card title="内存占用" :bordered="false" class="wp-card">
                  <WpEchart :option="redisMemOption" :height="240" />
                </a-card>
              </a-col>
              <a-col :span="8">
                <a-card title="Key 前缀分布" :bordered="false" class="wp-card">
                  <WpEchart :option="redisPrefixOption" :height="240" />
                </a-card>
              </a-col>
            </a-row>
            <a-card class="wp-card wp-mt" title="AI 洞察" :bordered="false">
              <a-alert type="info">{{ data.redis.ai_tip }}</a-alert>
            </a-card>
          </a-tab-pane>

          <!-- WordPress -->
          <a-tab-pane key="wordpress" title="WordPress">
            <a-row :gutter="16">
              <a-col :span="12">
                <a-card title="插件耗时 TOP (ms)" :bordered="false" class="wp-card">
                  <WpEchart :option="pluginOption" :height="240" />
                </a-card>
              </a-col>
              <a-col :span="12">
                <a-card title="Hook 耗时 (ms)" :bordered="false" class="wp-card">
                  <WpEchart :option="hookOption" :height="240" />
                </a-card>
              </a-col>
            </a-row>
            <a-row :gutter="16" class="wp-mt">
              <a-col :span="24">
                <a-card title="运行时概览 (WP {{ data.wordpress.version }})" :bordered="false" class="wp-card">
                  <a-space wrap>
                    <a-tag color="green">REST API {{ data.wordpress.rest_api.qps }} QPS / {{ data.wordpress.rest_api.avg_ms }}ms</a-tag>
                    <a-tag color="arcoblue">Cron 待执行 {{ data.wordpress.cron.pending }}</a-tag>
                    <a-tag color="gray">Heartbeat {{ data.wordpress.heartbeat.enabled ? '开' : '关' }} / {{ data.wordpress.heartbeat.interval_s }}s</a-tag>
                    <a-tag color="orange">插件总耗时 {{ data.wordpress.plugin_total_ms }}ms</a-tag>
                  </a-space>
                </a-card>
              </a-col>
            </a-row>
          </a-tab-pane>

          <!-- 存储 -->
          <a-tab-pane key="storage" title="存储 Storage">
            <a-row :gutter="16">
              <a-col :span="12">
                <a-card title="磁盘占用构成" :bordered="false" class="wp-card">
                  <WpEchart :option="storageOption" :height="260" />
                </a-card>
              </a-col>
              <a-col :span="12">
                <a-card title="目录 TOP (GB)" :bordered="false" class="wp-card">
                  <WpEchart :option="storageFolderOption" :height="260" />
                </a-card>
              </a-col>
            </a-row>
          </a-tab-pane>

          <!-- 网络 -->
          <a-tab-pane key="network" title="网络 Network">
            <a-card title="带宽出入 (Mbps)" :bordered="false" class="wp-card">
              <WpEchart :option="networkOption" :height="260" />
            </a-card>
            <a-row :gutter="16" class="wp-mt">
              <a-col :span="24">
                <a-card title="协议与握手" :bordered="false" class="wp-card">
                  <a-space wrap>
                    <a-tag color="green">HTTP/3 {{ data.network.http3_pct }}%</a-tag>
                    <a-tag color="arcoblue">HTTP/2 {{ data.network.http2_pct }}%</a-tag>
                    <a-tag color="orange">TLS 握手 {{ data.network.tls_handshake_ms }}ms</a-tag>
                    <a-tag color="gray">单 IP 连接 {{ data.network.conn_per_ip }}</a-tag>
                    <a-tag color="green">入 {{ data.network.bandwidth_in_mbps }} Mbps</a-tag>
                    <a-tag color="green">出 {{ data.network.bandwidth_out_mbps }} Mbps</a-tag>
                  </a-space>
                </a-card>
              </a-col>
            </a-row>
          </a-tab-pane>

          <!-- 错误中心 -->
          <a-tab-pane key="errors" title="错误中心 Issues">
            <a-row :gutter="16">
              <a-col :span="8" v-for="lvl in ['critical', 'warning', 'info']" :key="lvl">
                <a-card :title="levelMeta[lvl].title" :bordered="false" class="wp-card">
                  <a-empty v-if="!data.errors[lvl].length" description="无" />
                  <a-alert
                    v-for="(e, i) in data.errors[lvl]"
                    :key="i"
                    :type="levelMeta[lvl].type"
                    class="wp-issue"
                  >{{ e.text }}</a-alert>
                </a-card>
              </a-col>
            </a-row>
          </a-tab-pane>

          <!-- 时间线 -->
          <a-tab-pane key="timeline" title="时间线 Timeline">
            <a-card :bordered="false" class="wp-card">
              <a-timeline>
                <a-timeline-item
                  v-for="(t, i) in data.timeline"
                  :key="i"
                  :label="t.time"
                  :dot-color="timelineColor(t.type)"
                >
                  {{ t.text }}
                </a-timeline-item>
              </a-timeline>
            </a-card>
          </a-tab-pane>

          <!-- AI 分析 -->
          <a-tab-pane key="ai" title="AI 分析 Analysis">
            <a-card :bordered="false" class="wp-card">
              <div class="wp-ai-summary">
                <icon-bulb class="wp-ai-icon" />
                <span>{{ data.ai_analysis.summary }}</span>
              </div>
              <a-table :columns="aiCols" :data="data.ai_analysis.items" :pagination="false" class="wp-mt">
                <template #status="{ record }">
                  <a-tag :color="aiStatusColor(record.status)">{{ record.status }}</a-tag>
                </template>
                <template #score="{ record }">
                  <a-progress :percent="record.score" size="small" :stroke-color="scoreColor(record.score)" />
                </template>
              </a-table>
            </a-card>
          </a-tab-pane>

          <!-- 自动优化 -->
          <a-tab-pane key="optimize" title="自动优化 Auto-Opt">
            <a-card :bordered="false" class="wp-card">
              <a-alert type="info" class="wp-mt-none">L4 自愈：一键应用优化策略，配置将即时生效并反映在指标中。</a-alert>
              <div class="wp-opt-list">
                <div v-for="opt in data.optimizations" :key="opt.id" class="wp-opt">
                  <div class="wp-opt-main">
                    <div class="wp-opt-title">
                      {{ opt.title }}
                      <a-tag v-if="opt.applied" color="green">已应用</a-tag>
                    </div>
                    <div class="wp-opt-desc">{{ opt.desc }}</div>
                    <div class="wp-opt-effect">预期效果：{{ opt.effect }}</div>
                  </div>
                  <a-button
                    :type="opt.applied ? 'secondary' : 'primary'"
                    :disabled="opt.applied"
                    :loading="optLoading === opt.id"
                    @click="applyOpt(opt.id)"
                  >{{ opt.applied ? '已完成' : '应用' }}</a-button>
                </div>
              </div>
            </a-card>
          </a-tab-pane>
        </a-tabs>
      </template>
    </a-spin>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { IconRefresh, IconBulb } from '@arco-design/web-vue/es/icon'
import { Message } from '@arco-design/web-vue'
import WpEchart from '../../components/wp/WpEchart.vue'
import { getWpRuntime, applyWpOptimize } from '../../api/wordpressRuntime.js'

const data = ref(null)
const loading = ref(false)
const activeTab = ref('request')
const autoRefresh = ref(true)
const optLoading = ref('')
let timer = null

const COLORS = {
  blue: '#165DFF', green: '#00B42A', orange: '#FF7D00', red: '#F53F3F',
  purple: '#722ED1', cyan: '#14C9C9', gray: '#86909C',
}

async function fetchData() {
  loading.value = true
  try {
    const res = await getWpRuntime()
    data.value = res
  } catch (e) {
    Message.error('获取 WordPress 运行时数据失败')
  } finally {
    loading.value = false
  }
}

function toggleAuto(v) {
  if (v) startTimer()
  else stopTimer()
}
function startTimer() {
  stopTimer()
  timer = setInterval(fetchData, 5000)
}
function stopTimer() {
  if (timer) clearInterval(timer)
  timer = null
}

async function applyOpt(id) {
  optLoading.value = id
  try {
    const res = await applyWpOptimize(id)
    if (res.ok) {
      Message.success(res.message)
      await fetchData()
    } else {
      Message.warning(res.message)
    }
  } catch (e) {
    Message.error('优化执行失败')
  } finally {
    optLoading.value = ''
  }
}

// ---- helpers ----
const scoreColor = (s) => (s >= 90 ? COLORS.green : s >= 80 ? COLORS.cyan : s >= 70 ? COLORS.orange : COLORS.red)
const gradeColor = (g) => ({ A: COLORS.green, B: COLORS.cyan, C: COLORS.orange, D: COLORS.red }[g] || COLORS.gray)
const errClass = computed(() => (data.value && data.value.request.error_rate < 1 ? '' : 'wp-err'))
const aiSummary = computed(() => (data.value ? data.value.ai_analysis.summary : ''))
const realSignals = computed(() => (data.value ? data.value.real_signals || {} : {}))
const ols = computed(() => realSignals.value.ols || {})
const phpReal = computed(() => realSignals.value.php || {})
const mariadb = computed(() => realSignals.value.mariadb || {})

const levelMeta = {
  critical: { title: '严重 Critical', type: 'error' },
  warning: { title: '警告 Warning', type: 'warning' },
  info: { title: '提示 Info', type: 'info' },
}
const timelineColor = (t) =>
  ({ deploy: COLORS.blue, cache: COLORS.green, warning: COLORS.orange, plugin: COLORS.purple,
     db: COLORS.cyan, optimize: COLORS.green, worker: COLORS.blue, network: COLORS.gray }[t] || COLORS.gray)
const aiStatusColor = (s) => ({ 健康: 'green', 良好: 'cyan', 需关注: 'orange', 异常: 'red' }[s] || 'gray')

// ---- chart option builders ----
function lineOption(series, name, color, unit = '') {
  return {
    grid: { left: 44, right: 16, top: 24, bottom: 28 },
    tooltip: { trigger: 'axis', valueFormatter: (v) => v + unit },
    xAxis: { type: 'category', data: series.map((p) => ''), show: false },
    yAxis: { type: 'value', splitLine: { lineStyle: { color: 'rgba(255,255,255,0.06)' } } },
    series: [{
      name, type: 'line', smooth: true, showSymbol: false,
      data: series.map((p) => p.v),
      lineStyle: { color, width: 2 },
      areaStyle: { color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [
        { offset: 0, color: color + '55' }, { offset: 1, color: color + '05' }] } },
    }],
  }
}
function hbarOption(items, color) {
  return {
    grid: { left: 130, right: 30, top: 10, bottom: 10 },
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    xAxis: { type: 'value', splitLine: { lineStyle: { color: 'rgba(255,255,255,0.06)' } } },
    yAxis: { type: 'category', data: items.map((i) => i.name || i.path || i.table || i.script || i.prefix || i.hook), inverse: true },
    series: [{ type: 'bar', data: items.map((i) => i.ms ?? i.gb ?? i.pct ?? i.v ?? 0),
      itemStyle: { color, borderRadius: [0, 4, 4, 0] }, barWidth: '55%' }],
  }
}
function gaugeOption(value, color, title) {
  return {
    series: [{
      type: 'gauge', radius: '92%', center: ['50%', '58%'],
      progress: { show: true, width: 12, itemStyle: { color } },
      axisLine: { lineStyle: { width: 12, color: [[1, 'rgba(255,255,255,0.08)']] } },
      axisTick: { show: false }, splitLine: { show: false }, axisLabel: { show: false },
      pointer: { show: false },
      detail: { valueAnimation: true, fontSize: 30, color, offsetCenter: [0, '5%'], formatter: '{value}' + (title === '命中率' ? '%' : '') },
      data: [{ value: Math.round(value) }],
      title: { show: true, offsetCenter: [0, '32%'], color: '#86909C', fontSize: 12 },
    }],
  }
}
function pieOption(items, names) {
  return {
    tooltip: { trigger: 'item' },
    legend: { bottom: 0, textStyle: { color: '#86909C' } },
    series: [{
      type: 'pie', radius: ['45%', '70%'], center: ['50%', '45%'],
      label: { color: '#c9cdd4' },
      data: items.map((v, i) => ({ name: names[i], value: v, itemStyle: { color: [COLORS.green, COLORS.red, COLORS.orange, COLORS.blue][i] } })),
    }],
  }
}

// ---- computed options ----
const qpsOption = computed(() => data.value ? lineOption(data.value.request.qps_series, 'QPS', COLORS.blue) : {})
const p95Option = computed(() => data.value ? lineOption(data.value.request.p95_series, 'P95', COLORS.orange, 'ms') : {})
const cacheTrendOption = computed(() => data.value ? lineOption(data.value.cache.series, '命中率', COLORS.green, '%') : {})
const dbTrendOption = computed(() => data.value ? lineOption(data.value.database.series, 'QPS', COLORS.cyan) : {})
const networkOption = computed(() => {
  if (!data.value) return {}
  const d = data.value.network
  return {
    grid: { left: 50, right: 16, top: 30, bottom: 28 },
    tooltip: { trigger: 'axis' },
    legend: { data: ['入站', '出站'], textStyle: { color: '#86909C' } },
    xAxis: { type: 'category', data: Array.from({ length: 60 }, (_, i) => i), show: false },
    yAxis: { type: 'value', splitLine: { lineStyle: { color: 'rgba(255,255,255,0.06)' } } },
    series: [
      { name: '入站', type: 'line', smooth: true, showSymbol: false, data: d.series_in.map((p) => p.v), lineStyle: { color: COLORS.blue }, areaStyle: { color: COLORS.blue + '33' } },
      { name: '出站', type: 'line', smooth: true, showSymbol: false, data: d.series_out.map((p) => p.v), lineStyle: { color: COLORS.green }, areaStyle: { color: COLORS.green + '33' } },
    ],
  }
})

const cacheGaugeOption = computed(() => data.value ? gaugeOption(data.value.cache.overall_hit, COLORS.green, '命中率') : {})
const cacheLayerOption = computed(() => {
  if (!data.value) return {}
  const c = data.value.cache
  return {
    grid: { left: 60, right: 20, top: 10, bottom: 10 },
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' }, valueFormatter: (v) => v + '%' },
    xAxis: { type: 'value', max: 100, splitLine: { lineStyle: { color: 'rgba(255,255,255,0.06)' } } },
    yAxis: { type: 'category', data: ['Public', 'Private', 'Browser', 'Redis'], inverse: true },
    series: [{ type: 'bar', barWidth: '55%', data: [c.public, c.private, c.browser, c.redis],
      itemStyle: { borderRadius: [0, 4, 4, 0], color: (p) => [COLORS.green, COLORS.orange, COLORS.blue, COLORS.purple][p.dataIndex] } }],
  }
})
const workerGaugeOption = computed(() => data.value ? gaugeOption(data.value.worker.utilization, data.value.worker.queue > 200 ? COLORS.red : COLORS.blue, '利用率') : {})
const opcacheOption = computed(() => data.value ? gaugeOption(data.value.php.opcache.hit_rate, COLORS.green, '命中率') : {})
const phpSlowOption = computed(() => data.value ? hbarOption(data.value.php.slow_scripts, COLORS.orange) : {})
const dbTableOption = computed(() => data.value ? hbarOption(data.value.database.top_tables, COLORS.cyan) : {})
const redisPieOption = computed(() => data.value ? pieOption([data.value.redis.hit, data.value.redis.miss], ['命中', '未命中']) : {})
const redisMemOption = computed(() => data.value ? gaugeOption(data.value.redis.memory_mb, COLORS.purple, '内存') : {})
const redisPrefixOption = computed(() => data.value ? pieOption(data.value.redis.top_prefix.map((p) => p.pct), data.value.redis.top_prefix.map((p) => p.prefix)) : {})
const pluginOption = computed(() => data.value ? hbarOption(data.value.wordpress.plugin_time, COLORS.purple) : {})
const hookOption = computed(() => data.value ? hbarOption(data.value.wordpress.hook_time, COLORS.cyan) : {})
const storageOption = computed(() => {
  if (!data.value) return {}
  const s = data.value.storage
  const used = s.total_gb
  const free = Math.max(0, s.disk_total_gb - used)
  return {
    tooltip: { trigger: 'item' },
    legend: { bottom: 0, textStyle: { color: '#86909C' } },
    series: [{
      type: 'pie', radius: ['45%', '70%'], center: ['50%', '45%'],
      label: { color: '#c9cdd4', formatter: '{b}\n{c}GB' },
      data: [
        { name: 'Uploads', value: s.uploads_gb, itemStyle: { color: COLORS.blue } },
        { name: 'Cache', value: s.cache_gb, itemStyle: { color: COLORS.green } },
        { name: 'Logs', value: s.logs_gb, itemStyle: { color: COLORS.orange } },
        { name: 'Backups', value: s.backups_gb, itemStyle: { color: COLORS.purple } },
        { name: '可用', value: free, itemStyle: { color: COLORS.gray } },
      ],
    }],
  }
})
const storageFolderOption = computed(() => data.value ? hbarOption(data.value.storage.top_folders, COLORS.blue) : {})
const lifecycleOption = computed(() => {
  if (!data.value) return {}
  const d = data.value
  const net = +(d.request.avg * 0.25).toFixed(0)
  const cacheL = +(d.request.avg * 0.1).toFixed(0)
  const php = +(d.php.avg_time).toFixed(0)
  const db = +(d.database.avg_query_ms * 3).toFixed(0)
  const plugins = +(d.wordpress.plugin_total_ms).toFixed(0)
  const theme = d.wordpress.theme_time.reduce((a, b) => a + b.ms, 0)
  const render = Math.max(2, d.request.avg - net - cacheL - php - db - plugins - theme)
  const segs = [
    { name: '网络/TTFB', v: net, c: COLORS.gray },
    { name: '缓存查找', v: cacheL, c: COLORS.cyan },
    { name: 'PHP 执行', v: php, c: COLORS.orange },
    { name: '数据库', v: db, c: COLORS.blue },
    { name: '插件', v: plugins, c: COLORS.purple },
    { name: '主题', v: theme, c: COLORS.green },
    { name: '渲染输出', v: render, c: COLORS.red },
  ]
  return {
    grid: { left: 80, right: 30, top: 20, bottom: 20 },
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' }, valueFormatter: (v) => v + 'ms' },
    xAxis: { type: 'value', splitLine: { lineStyle: { color: 'rgba(255,255,255,0.06)' } } },
    yAxis: { type: 'category', data: ['单次请求'], },
    series: segs.map((s) => ({ type: 'bar', stack: 'life', data: [s.v], itemStyle: { color: s.c }, barWidth: '40%' })),
  }
})

// ---- table columns ----
const urlCols = [
  { title: '接口', dataIndex: 'path' },
  { title: '占比', dataIndex: 'pct', render: (record) => record.pct + '%' },
]
const sqlCols = [
  { title: 'SQL', dataIndex: 'sql' },
  { title: '耗时(ms)', dataIndex: 'ms' },
  { title: '归属', slotName: 'plugin' },
]
const aiCols = [
  { title: '指标', dataIndex: 'metric' },
  { title: '评分', slotName: 'score', width: 140 },
  { title: '状态', slotName: 'status', width: 100 },
  { title: '原因', dataIndex: 'cause' },
  { title: '建议', dataIndex: 'suggestion' },
]

onMounted(() => {
  fetchData()
  if (autoRefresh.value) startTimer()
})
onBeforeUnmount(stopTimer)
</script>

<style scoped>
.wp-runtime { padding: 16px; color: #c9cdd4; }
.wp-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 16px; }
.wp-title { font-size: 20px; font-weight: 600; color: #fff; display: flex; align-items: center; gap: 10px; }
.wp-logo { display: inline-flex; align-items: center; justify-content: center; width: 30px; height: 30px; border-radius: 8px;
  background: linear-gradient(135deg, #21759b, #165DFF); color: #fff; font-weight: 700; }
.wp-subtitle { font-size: 12px; color: #86909c; margin-top: 6px; }
.wp-updated { margin-left: 10px; color: #4e5969; }
.wp-controls { display: flex; align-items: center; gap: 12px; }

.wp-score-card { background: #16171a; border-radius: 12px; }
.wp-score-main { display: flex; align-items: center; gap: 24px; }
.wp-score-ring { width: 110px; height: 110px; border-radius: 50%; display: flex; flex-direction: column;
  align-items: center; justify-content: center; border: 8px solid var(--c); position: relative; flex-shrink: 0; }
.wp-score-ring::after { content: ''; position: absolute; inset: -8px; border-radius: 50%; border: 2px solid var(--c); opacity: .25; }
.wp-score-num { font-size: 38px; font-weight: 700; color: #fff; line-height: 1; }
.wp-score-grade { font-size: 12px; color: var(--c); margin-top: 4px; font-weight: 600; }
.wp-score-meta { flex: 1; }
.wp-score-label { font-size: 13px; color: #86909c; }
.wp-score-desc { font-size: 13px; color: #c9cdd4; margin: 6px 0 12px; line-height: 1.6; }
.wp-kpi-row { display: flex; gap: 28px; flex-wrap: wrap; }
.wp-kpi-v { font-size: 22px; font-weight: 700; color: #fff; }
.wp-kpi-v i { font-size: 12px; font-weight: 400; color: #86909c; margin-left: 2px; font-style: normal; }
.wp-kpi-v.wp-err { color: var(--color-danger, #f53f3f); }
.wp-kpi-l { font-size: 12px; color: #86909c; margin-top: 2px; }

.wp-divider { height: 90px; }
.wp-score-grid { display: flex; flex-wrap: wrap; gap: 10px; flex: 1; }
.wp-comp { display: flex; align-items: center; gap: 10px; padding: 8px 10px; border-radius: 8px; background: rgba(255,255,255,0.03); flex: 1 1 130px; }
.wp-comp-meta { display: flex; flex-direction: column; gap: 4px; }
.wp-comp-label { font-size: 12px; color: #c9cdd4; }
.wp-comp-src { align-self: flex-start; }

.wp-tabs { margin-top: 16px; }
.wp-card { background: #16171a; border-radius: 12px; }
.wp-mt { margin-top: 16px; }
.wp-mt-none { margin-bottom: 12px; }
.wp-issue { margin-bottom: 8px; }
.wp-ai-summary { display: flex; gap: 10px; align-items: flex-start; background: rgba(22,93,255,0.08);
  border: 1px solid rgba(22,93,255,0.25); border-radius: 8px; padding: 12px 14px; line-height: 1.7; color: #e5e6eb; }
.wp-ai-icon { color: #165DFF; font-size: 18px; margin-top: 2px; flex-shrink: 0; }

.wp-opt-list { margin-top: 12px; display: flex; flex-direction: column; gap: 12px; }
.wp-opt { display: flex; justify-content: space-between; align-items: center; gap: 16px;
  padding: 14px 16px; border-radius: 10px; background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.05); }
.wp-opt-title { font-size: 14px; font-weight: 600; color: #fff; display: flex; align-items: center; gap: 8px; }
.wp-opt-desc { font-size: 12px; color: #86909c; margin-top: 4px; }
.wp-opt-effect { font-size: 12px; color: #00b42a; margin-top: 4px; }
</style>
