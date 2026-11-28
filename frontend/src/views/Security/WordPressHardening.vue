<template>
  <div class="wp-hardening">
    <a-card title="一键安全加固 (针对所有站点)" :loading="loading">
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
import { ref, computed, onMounted } from 'vue'
import { Message } from '@arco-design/web-vue'
import request from '@/utils/request'

const loading = ref(false)
const sites = ref([])
const showHideLoginModal = ref(false)
const hideLoginPath = ref('')

const commonLoginPath = computed(() => {
  if (!sites.value || sites.value.length === 0) return ''
  const siteWithPath = sites.value.find((s) => s.wp_hide_login_path)
  return siteWithPath ? siteWithPath.wp_hide_login_path : ''
})

const fetchSites = async () => {
  try {
    const res = await request.get('/sites/')
    sites.value = res || []
  } catch (error) {
    console.error(error)
  }
}

const handleBatchAction = async (action, params = {}) => {
  if (sites.value.length === 0) {
    Message.warning('未检测到 WordPress 站点')
    return
  }
  loading.value = true
  try {
    // 循环调用现有 API 实现批量操作
    const promises = sites.value.map((site) => {
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
    fetchSites()
  } catch (error) {
    Message.error('部分或全部站点操作失败，请检查系统日志')
  } finally {
    loading.value = false
  }
}

const handleHideLogin = (path) => {
  handleBatchAction('hide-login', { path })
}

onMounted(fetchSites)
</script>

<style scoped>
.wp-hardening :deep(.arco-list-item) {
  align-items: center;
}
</style>
