<template>
  <div class="php-runtime">
    <a-tabs v-model:active-key="active" type="card" size="small" lazy-load>
      <a-tab-pane key="versions" title="PHP 版本">
        <PhpVersions />
      </a-tab-pane>
      <a-tab-pane key="extensions" title="扩展管理">
        <PhpExtensions />
      </a-tab-pane>
      <a-tab-pane key="config" title="运行配置">
        <PhpRuntimeConfig />
      </a-tab-pane>
      <a-tab-pane key="opcache" title="字节码缓存">
        <PhpOpcache />
      </a-tab-pane>
      <a-tab-pane key="workerpool" title="进程池配置">
        <PhpWorkerPool />
      </a-tab-pane>
      <a-tab-pane key="workermonitor" title="进程监控">
        <PhpWorkerMonitor />
      </a-tab-pane>
      <a-tab-pane key="health" title="健康检查">
        <PhpHealth />
      </a-tab-pane>
      <a-tab-pane key="autoscaling" title="自动伸缩">
        <PhpAutoScaling />
      </a-tab-pane>
      <a-tab-pane key="ai" title="AI 优化建议">
        <PhpAiOptimizer />
      </a-tab-pane>
    </a-tabs>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import PhpVersions from './PhpVersions.vue'
import PhpExtensions from './PhpExtensions.vue'
import PhpRuntimeConfig from './PhpRuntimeConfig.vue'
import PhpOpcache from './PhpOpcache.vue'
import PhpWorkerPool from './PhpWorkerPool.vue'
import PhpWorkerMonitor from './PhpWorkerMonitor.vue'
import PhpHealth from './PhpHealth.vue'
import PhpAutoScaling from './PhpAutoScaling.vue'
import PhpAiOptimizer from './PhpAiOptimizer.vue'

const active = ref('versions')
</script>

<style scoped>
.php-runtime {
  padding: 0;
}
</style>
