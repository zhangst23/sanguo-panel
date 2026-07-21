<template>
  <div class="mariadb-container">
    <div class="section-header">
      <a-typography-title :heading="2">MariaDB 数据库管理</a-typography-title>
    </div>

    <a-tabs default-active-key="dbList" type="card-gutter" class="mariadb-tabs">
      <!-- 标签 1: 数据库列表 -->
      <a-tab-pane key="dbList" title="数据库列表">
        <a-row :gutter="20">
          <!-- 服务状态 -->
          <a-col :span="24" style="margin-bottom: 20px">
            <a-card title="服务状态" hoverable>
              <template #extra>
                <a-tag :color="serviceStatus === 'running' ? 'green' : 'red'">{{ serviceStatus === 'running' ? '运行中' : '已停止' }}</a-tag>
              </template>
              <a-space size="large">
                <a-statistic title="端口" :value="3306" />
                <a-statistic title="当前连接" :value="connections" />
                <a-space style="margin-left: 40px">
                  <a-button type="primary" @click="handleServiceAction('restart')" :loading="serviceLoading">
                    <template #icon><icon-refresh /></template>
                    重启服务
                  </a-button>
                  <a-button @click="fetchServiceStatus">刷新状态</a-button>
                  
                  <!-- 管理员凭据展示 -->
                  <a-popover title="管理员数据库凭据">
                    <a-button type="outline" size="small" style="margin-left: 10px">
                      <template #icon><icon-safe /></template>
                      查看管理员凭据
                    </a-button>
                    <template #content>
                      <div class="admin-creds">
                        <p><b>库名:</b> {{ adminCreds.db_name }}</p>
                        <p><b>用户:</b> {{ adminCreds.db_user }}</p>
                        <p>
                          <b>密码:</b> {{ showAdminPass ? adminCreds.db_password : '******' }}
                          <a-button type="text" size="mini" @click="showAdminPass = !showAdminPass">
                            <icon-eye v-if="!showAdminPass" /><icon-eye-invisible v-else />
                          </a-button>
                        </p>
                      </div>
                    </template>
                  </a-popover>
                </a-space>
              </a-space>
            </a-card>
          </a-col>

          <!-- 数据库列表 -->
          <a-col :span="24">
            <a-card title="WordPress 站点数据库列表">
              <a-table :data="dbList" :loading="loading" :pagination="false">
                <template #columns>
                  <a-table-column title="站点域名" data-index="domain" />
                  <a-table-column title="数据库名" data-index="db_name" />
                  <a-table-column title="用户名" data-index="db_user" />
                  <a-table-column title="密码">
                    <template #cell="{ record }">
                      <a-space>
                        <span class="password-text">{{ showPassword[record.site_id] ? record.db_password : '******' }}</span>
                        <a-button type="text" size="mini" @click="togglePassword(record.site_id)">
                          <template #icon>
                            <icon-eye v-if="!showPassword[record.site_id]" />
                            <icon-eye-invisible v-else />
                          </template>
                        </a-button>
                        <a-button type="text" size="mini" @click="copyToClipboard(record.db_password)">
                          <template #icon><icon-copy /></template>
                        </a-button>
                      </a-space>
                    </template>
                  </a-table-column>
                  <a-table-column title="创建时间" data-index="created_at" />
                  <a-table-column title="操作">
                    <template #cell="{ record }">
                      <a-space>
                        <a-link @click="handleOpenPMA(record)">管理</a-link>
                        <a-popconfirm content="确定要重置该数据库的密码吗？" @ok="handleChangePassword(record)">
                          <a-link>改密</a-link>
                        </a-popconfirm>
                        <a-dropdown @select="(val) => handleSetPermission(record, val)">
                          <a-link>
                            权限: {{ record.db_permission === 'all_dbs' ? '所有人' : '仅自己' }}
                            <icon-down />
                          </a-link>
                          <template #content>
                            <a-doption value="site_only">仅自己站点数据库</a-doption>
                            <a-doption value="all_dbs">访问所有人数据库</a-doption>
                          </template>
                        </a-dropdown>
                        <a-popconfirm content="确定要清理该数据库的碎片吗？" @ok="handleOptimize(record)">
                          <a-link>优化</a-link>
                        </a-popconfirm>
                        <a-popconfirm content="确定要删除该数据库吗？此操作不可撤销！" type="warning" @ok="handleDelete(record)">
                          <a-link status="danger">删除</a-link>
                        </a-popconfirm>
                      </a-space>
                    </template>
                  </a-table-column>
                </template>
              </a-table>
            </a-card>
          </a-col>
        </a-row>
      </a-tab-pane>

      <!-- 标签 2: 慢查询日志分析 -->
      <a-tab-pane key="slowQuery" title="慢查询日志分析">
        <a-card>
          <template #extra>
            <a-space>
              <span style="font-size: 14px; color: var(--color-text-2);">记录慢查询</span>
              <a-switch v-model="slowQueryEnabled" @change="handleToggleSlowQuery" />
            </a-space>
          </template>
          <a-table :data="slowQueries" :pagination="true">
            <template #columns>
              <a-table-column title="发生时间" data-index="timestamp" :width="200" />
              <a-table-column title="耗时" data-index="execution_time" :width="120">
                <template #cell="{ record }">
                  <a-tag color="red">{{ record.execution_time }}</a-tag>
                </template>
              </a-table-column>
              <a-table-column title="查询语句" data-index="query">
                <template #cell="{ record }">
                  <code class="sql-code">{{ record.query }}</code>
                </template>
              </a-table-column>
            </template>
          </a-table>
        </a-card>
      </a-tab-pane>
    </a-tabs>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import request from '@/utils/request'
import { Message } from '@arco-design/web-vue'
import { 
  IconRefresh, 
  IconEye, 
  IconEyeInvisible, 
  IconCopy,
  IconSafe,
  IconDown
} from '@arco-design/web-vue/es/icon'

const serviceStatus = ref('running')
const serviceLoading = ref(false)
const loading = ref(false)
const dbList = ref([])
const connections = ref(0)
const showPassword = reactive({})
const slowQueries = ref([])
const slowQueryEnabled = ref(true)
const adminCreds = ref({ db_name: '', db_user: '', db_password: '' })
const showAdminPass = ref(false)

const fetchAdminCreds = async () => {
  try {
    const res = await request.get('/database/admin-credentials')
    adminCreds.value = res
  } catch (error) {
    console.error('获取管理凭据失败:', error)
  }
}

const fetchServiceStatus = async () => {
  try {
    const res = await request.get('/service/mariadb/status')
    serviceStatus.value = res.status
    connections.value = res.connections || 0
  } catch (error) {
    console.error('获取服务状态失败:', error)
  }
}

const fetchDbList = async () => {
  loading.value = true
  try {
    const res = await request.get('/database/list')
    dbList.value = res
  } catch (error) {
    Message.error('获取数据库列表失败')
  } finally {
    loading.value = false
  }
}

const fetchSlowQueries = async () => {
  try {
    const res = await request.get('/database/slow-queries')
    slowQueries.value = res
  } catch (error) {
    console.error('获取慢查询失败:', error)
  }
}

const handleServiceAction = async (action) => {
  serviceLoading.value = true
  try {
    await request.post(`/service/mariadb/${action}`)
    Message.success('操作成功')
    await fetchServiceStatus()
  } catch (error) {
    Message.error('操作失败')
  } finally {
    serviceLoading.value = false
  }
}

const togglePassword = (id) => {
  showPassword[id] = !showPassword[id]
}

const copyToClipboard = (text) => {
  navigator.clipboard.writeText(text)
  Message.success('已复制到剪贴板')
}

const handleOpenPMA = async (record) => {
  try {
    const res = await request.get(`/database/pma-jump/${record.site_id}`)
    if (res.url) {
      window.open(res.url, '_blank')
    } else {
      Message.error('获取 phpMyAdmin 跳转地址失败')
    }
  } catch (error) {
    Message.error('跳转失败: ' + (error.response?.data?.detail || error.message))
  }
}

const handleChangePassword = async (record) => {
  try {
    const res = await request.post(`/database/change-password/${record.site_id}`)
    Message.success(`密码已重置为: ${res.new_password}`)
    fetchDbList()
  } catch (error) {
    Message.error('重置密码失败')
  }
}

const handleOptimize = async (record) => {
  try {
    await request.post(`/database/optimize`, { db_name: record.db_name })
    Message.success('碎片清理成功')
  } catch (error) {
    Message.error('优化失败')
  }
}

const handleSetPermission = async (record, val) => {
  try {
    await request.post(`/database/set-permission/${record.site_id}`, null, { params: { permission: val } })
    Message.success('权限更新成功')
    fetchDbList()
  } catch (error) {
    Message.error('更新权限失败')
  }
}

const handleDelete = async (record) => {
  try {
    await request.delete(`/database/${record.site_id}`)
    Message.success('数据库已删除')
    fetchDbList()
  } catch (error) {
    Message.error('删除失败: ' + (error.response?.data?.detail || error.message))
  }
}

const handleToggleSlowQuery = async (val) => {
  try {
    await request.post('/database/slow-query/toggle', { enabled: val })
    Message.success(val ? '慢查询日志已开启' : '慢查询日志已关闭')
  } catch (error) {
    Message.error('设置失败')
    slowQueryEnabled.value = !val // 恢复状态
  }
}

onMounted(() => {
  fetchServiceStatus()
  fetchDbList()
  fetchSlowQueries()
  fetchAdminCreds()
})
</script>

<style scoped>
.mariadb-container {
  padding: 0;
}
.section-header {
  margin-bottom: 24px;
}
.mariadb-tabs {
  background: var(--arco-color-bg-2);
  padding: 16px;
  border-radius: 4px;
}
.password-text {
  font-family: monospace;
  font-size: 13px;
}
.sql-code {
  font-family: monospace;
  background: var(--arco-color-fill-2);
  padding: 2px 4px;
  border-radius: 2px;
  color: #d91d1d;
}
</style>
