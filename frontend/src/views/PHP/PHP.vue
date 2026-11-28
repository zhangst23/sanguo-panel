<template>
  <div class="php-runtime">
    <PhpVersions />
    <PhpExtensions />
    <PhpRuntimeConfig />
    <PhpOpcache />
    <PhpWorkerPool />
    <PhpWorkerMonitor />
    <PhpHealth />
    <PhpAutoScaling />
    <PhpAiOptimizer />
  </div>
</template>

<script setup>
import PhpVersions from './PhpVersions.vue'
import PhpExtensions from './PhpExtensions.vue'
import PhpRuntimeConfig from './PhpRuntimeConfig.vue'
import PhpOpcache from './PhpOpcache.vue'
import PhpWorkerPool from './PhpWorkerPool.vue'
import PhpWorkerMonitor from './PhpWorkerMonitor.vue'
import PhpHealth from './PhpHealth.vue'
import PhpAutoScaling from './PhpAutoScaling.vue'
import PhpAiOptimizer from './PhpAiOptimizer.vue'
</script>

<style scoped>
.php-runtime {
  padding: 0;
}
</style>
