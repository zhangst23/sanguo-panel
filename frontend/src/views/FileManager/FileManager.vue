<template>
  <div class="file-manager">
    <a-typography-title :heading="2">文件管理</a-typography-title>

    <a-row :gutter="16">
      <!-- 左侧：站点列表 -->
      <a-col :span="6">
        <a-card title="站点列表" hoverable class="site-list-card">
          <a-list :data="sites" :loading="loadingSites">
            <template #item="{ item }">
              <a-list-item
                class="site-item"
                :class="{ active: currentSiteId === item.id }"
                @click="selectSite(item)"
              >
                <a-list-item-meta :title="item.domain">
                  <template #description>
                    <a-typography-text type="secondary" style="font-size: 12px">
                      {{ item.root_path }}
                    </a-typography-text>
                  </template>
                </a-list-item-meta>
              </a-list-item>
            </template>
          </a-list>
        </a-card>
      </a-col>

      <!-- 右侧：文件浏览器 -->
      <a-col :span="18">
        <a-card class="file-card">
          <template #title>
            <a-space>
              <a-button size="small" @click="goUp" :disabled="!canGoUp">
                <template #icon><icon-arrow-up /></template>
                返回上级
              </a-button>
              <a-breadcrumb>
                <a-breadcrumb-item v-for="(seg, i) in pathSegments" :key="i" @click="navigateTo(i)">
                  {{ seg }}
                </a-breadcrumb-item>
              </a-breadcrumb>
            </a-space>
          </template>
          <template #extra>
            <a-space>
              <a-button size="small" type="outline" @click="fetchFiles" :loading="loadingFiles">
                <template #icon><icon-refresh /></template>
                刷新
              </a-button>
              <a-button size="small" type="primary" @click="showUpload = true">
                <template #icon><icon-upload /></template>
                上传
              </a-button>
              <a-button size="small" type="outline" @click="showCreateFolder = true">
                <template #icon><icon-folder-add /></template>
                新建文件夹
              </a-button>
            </a-space>
          </template>

          <div v-if="!currentSiteId" class="empty-state">
            <icon-folder style="font-size: 48px; color: var(--color-text-3)" />
            <p>请先从左侧选择一个站点</p>
          </div>

          <a-table
            v-else
            :data="files"
            :loading="loadingFiles"
            :pagination="false"
            row-key="name"
          >
            <template #columns>
              <a-table-column title="名称">
                <template #cell="{ record }">
                  <a-space>
                    <icon-folder v-if="record.is_dir" style="color: var(--color-primary)" />
                    <icon-file v-else style="color: var(--color-text-3)" />
                    <a-link @click="openItem(record)">{{ record.name }}</a-link>
                  </a-space>
                </template>
              </a-table-column>
              <a-table-column title="大小" :width="120">
                <template #cell="{ record }">
                  {{ record.is_dir ? '-' : formatSize(record.size) }}
                </template>
              </a-table-column>
              <a-table-column title="权限" :width="120" data-index="mode" />
              <a-table-column title="修改时间" :width="200" data-index="mtime" />
              <a-table-column title="操作" :width="200">
                <template #cell="{ record }">
                  <a-space>
                    <a-button
                      type="text"
                      size="small"
                      v-if="!record.is_dir"
                      @click="handleDownload(record)"
                    >
                      下载
                    </a-button>
                    <a-button
                      type="text"
                      size="small"
                      @click="handleRename(record)"
                    >
                      重命名
                    </a-button>
                    <a-popconfirm content="确定要删除吗？" @ok="handleDelete(record)">
                      <a-button type="text" size="small" status="danger">删除</a-button>
                    </a-popconfirm>
                  </a-space>
                </template>
              </a-table-column>
            </template>
          </a-table>
        </a-card>
      </a-col>
    </a-row>

    <!-- 新建文件夹 -->
    <a-modal v-model:visible="showCreateFolder" title="新建文件夹" @ok="handleCreateFolder">
      <a-form layout="vertical">
        <a-form-item label="文件夹名称" required>
          <a-input v-model="newFolderName" placeholder="请输入文件夹名称" />
        </a-form-item>
      </a-form>
    </a-modal>

    <!-- 重命名 -->
    <a-modal v-model:visible="showRename" title="重命名" @ok="handleSaveRename">
      <a-form layout="vertical">
        <a-form-item label="新名称" required>
          <a-input v-model="renameValue" />
        </a-form-item>
      </a-form>
    </a-modal>

    <!-- 上传文件 -->
    <a-modal v-model:visible="showUpload" title="上传文件" @ok="handleUploadFile" :width="500">
      <a-upload
        :auto-upload="false"
        :file-list="uploadList"
        @change="handleUploadChange"
        @remove="handleUploadRemove"
        drag
      />
      <a-typography-text type="secondary" style="display: block; margin-top: 10px">
        支持单个或多个文件上传，将上传至当前目录
      </a-typography-text>
    </a-modal>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { Message } from '@arco-design/web-vue'
import request from '@/utils/request'
import {
  IconFolder,
  IconFile,
  IconRefresh,
  IconUpload,
  IconArrowUp,
  IconFolderAdd
} from '@arco-design/web-vue/es/icon'

const route = useRoute()

const sites = ref([])
const loadingSites = ref(false)
const currentSiteId = ref(null)
const currentPath = ref('')
const files = ref([])
const loadingFiles = ref(false)

const showCreateFolder = ref(false)
const newFolderName = ref('')

const showRename = ref(false)
const renameValue = ref('')
const renamingItem = ref(null)

const showUpload = ref(false)
const uploadList = ref([])

const canGoUp = computed(() => currentPath.value && currentPath.value !== '/')
const pathSegments = computed(() => {
  if (!currentPath.value) return []
  return currentPath.value.split('/').filter(Boolean)
})

const fetchSites = async () => {
  loadingSites.value = true
  try {
    const res = await request.get('/sites/')
    sites.value = Array.isArray(res) ? res : (res.items || [])
    // 如果从 query 携带了 site_id 则自动选中
    if (route.query.site_id) {
      selectSite(sites.value.find(s => s.id === Number(route.query.site_id)))
    } else if (sites.value.length > 0 && !currentSiteId.value) {
      selectSite(sites.value[0])
    }
  } catch (e) {
    console.error(e)
  } finally {
    loadingSites.value = false
  }
}

const selectSite = (site) => {
  if (!site) return
  currentSiteId.value = site.id
  currentPath.value = site.root_path || ''
  fetchFiles()
}

const fetchFiles = async () => {
  if (!currentSiteId.value) return
  loadingFiles.value = true
  try {
    const res = await request.get('/files/list', {
      params: {
        site_id: currentSiteId.value,
        path: currentPath.value
      }
    })
    files.value = res.items || []
  } catch (e) {
    console.error(e)
    Message.error('获取文件列表失败')
  } finally {
    loadingFiles.value = false
  }
}

const openItem = (record) => {
  if (record.is_dir) {
    currentPath.value = joinPath(currentPath.value, record.name)
    fetchFiles()
  } else {
    // 预览文件（简单实现：如果是文本可下载/打开）
    handleDownload(record)
  }
}

const goUp = () => {
  const segs = currentPath.value.split('/').filter(Boolean)
  if (segs.length > 0) {
    segs.pop()
    currentPath.value = segs.length ? '/' + segs.join('/') : ''
  }
  fetchFiles()
}

const navigateTo = (index) => {
  const segs = currentPath.value.split('/').filter(Boolean)
  if (index < segs.length - 1) {
    currentPath.value = '/' + segs.slice(0, index + 1).join('/')
    fetchFiles()
  }
}

const joinPath = (parent, child) => {
  if (!parent) return '/' + child
  return parent.replace(/\/$/, '') + '/' + child
}

const formatSize = (bytes) => {
  if (!bytes) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB']
  let i = 0
  let n = bytes
  while (n >= 1024 && i < units.length - 1) {
    n /= 1024
    i++
  }
  return `${n.toFixed(2)} ${units[i]}`
}

const handleDownload = async (record) => {
  try {
    const response = await request.get('/files/download', {
      params: {
        site_id: currentSiteId.value,
        path: joinPath(currentPath.value, record.name)
      },
      responseType: 'blob'
    })
    const url = window.URL.createObjectURL(new Blob([response]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', record.name)
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
  } catch (e) {
    Message.error('下载失败')
  }
}

const handleCreateFolder = async () => {
  if (!newFolderName.value) {
    Message.warning('请输入文件夹名称')
    return
  }
  try {
    await request.post('/files/mkdir', {
      site_id: currentSiteId.value,
      path: joinPath(currentPath.value, newFolderName.value)
    })
    Message.success('创建成功')
    newFolderName.value = ''
    showCreateFolder.value = false
    fetchFiles()
  } catch (e) {
    Message.error('创建失败')
  }
}

const handleRename = (record) => {
  renamingItem.value = record
  renameValue.value = record.name
  showRename.value = true
}

const handleSaveRename = async () => {
  if (!renameValue.value) return
  try {
    await request.post('/files/rename', {
      site_id: currentSiteId.value,
      src: joinPath(currentPath.value, renamingItem.value.name),
      dst: joinPath(currentPath.value, renameValue.value)
    })
    Message.success('重命名成功')
    showRename.value = false
    fetchFiles()
  } catch (e) {
    Message.error('重命名失败')
  }
}

const handleDelete = async (record) => {
  try {
    await request.post('/files/delete', {
      site_id: currentSiteId.value,
      path: joinPath(currentPath.value, record.name),
      is_dir: record.is_dir
    })
    Message.success('删除成功')
    fetchFiles()
  } catch (e) {
    Message.error('删除失败')
  }
}

const handleUploadChange = (fileList) => {
  uploadList.value = fileList
}

const handleUploadRemove = (fileItem) => {
  uploadList.value = uploadList.value.filter(f => f.uid !== fileItem.uid)
}

const handleUploadFile = async () => {
  if (uploadList.value.length === 0) {
    Message.warning('请先选择文件')
    return
  }
  const formData = new FormData()
  formData.append('site_id', currentSiteId.value)
  formData.append('path', currentPath.value)
  uploadList.value.forEach(item => {
    if (item.file) formData.append('files', item.file)
  })
  try {
    await request.post('/files/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
    Message.success('上传成功')
    showUpload.value = false
    uploadList.value = []
    fetchFiles()
  } catch (e) {
    Message.error('上传失败')
  }
}

watch(() => route.query.site_id, (val) => {
  if (val) {
    const site = sites.value.find(s => s.id === Number(val))
    if (site) selectSite(site)
  }
})

onMounted(() => {
  fetchSites()
})
</script>

<style scoped>
.file-manager {
  padding: 0;
}
.site-list-card {
  height: calc(100vh - 180px);
  overflow: hidden;
  display: flex;
  flex-direction: column;
}
.site-list-card :deep(.arco-card-body) {
  flex: 1;
  overflow-y: auto;
  padding: 0;
}
.site-item {
  cursor: pointer;
  transition: background 0.2s;
}
.site-item:hover {
  background: var(--color-fill-2);
}
.site-item.active {
  background: var(--color-primary-light-1);
}
.file-card {
  min-height: calc(100vh - 180px);
}
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 80px 0;
  color: var(--color-text-3);
}
</style>
