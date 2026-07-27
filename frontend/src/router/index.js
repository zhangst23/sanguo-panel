import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    redirect: '/dashboard',
    meta: { title: '仪表盘' },
  },
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/Login/Login.vue'),
    meta: { requiresAuth: false, title: '登录' },
  },
  {
    path: '/',
    component: () => import('@/components/layout/BaseLayout.vue'),
    children: [
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: () => import('@/views/Dashboard/Dashboard.vue'),
        meta: { requiresAuth: true, title: '仪表盘' },
      },
      {
        path: 'website',
        name: 'Website',
        component: () => import('@/views/Website/WebsiteList.vue'),
        meta: { requiresAuth: true, title: '网站管理' },
      },
      {
        path: 'website/:id',
        name: 'WebsiteDetail',
        component: () => import('@/views/Website/WebsiteDetail.vue'),
        meta: { requiresAuth: true, title: '网站详情' },
      },
      {
        path: 'cache',
        name: 'Cache',
        component: () => import('@/views/Cache/Cache.vue'),
        meta: { requiresAuth: true, title: '缓存管理' },
      },
      {
        path: 'ssl',
        name: 'SSL',
        component: () => import('@/views/SSL/SSL.vue'),
        meta: { requiresAuth: true, title: 'SSL证书' },
      },
      {
        path: 'image',
        name: 'Image',
        component: () => import('@/views/Image/Image.vue'),
        meta: { requiresAuth: true, title: '镜像管理' },
      },
      {
        path: 'database-adv',
        name: 'DatabaseAdv',
        component: () => import('@/views/Database/DatabaseAdv.vue'),
        meta: { requiresAuth: true, title: '数据库高级管理' },
      },
      {
        path: 'assets',
        name: 'Assets',
        component: () => import('@/views/Assets/Assets.vue'),
        meta: { requiresAuth: true, title: '资源管理' },
      },
      {
        path: 'cdn',
        name: 'CDN',
        component: () => import('@/views/Cdn/CDN.vue'),
        meta: { requiresAuth: true, title: 'CDN加速' },
      },
      {
        path: 'ultimate',
        name: 'Ultimate',
        component: () => import('@/views/Ultimate/Ultimate.vue'),
        meta: { requiresAuth: true, title: '终极配置' },
      },
      {
        path: 'litespeed',
        name: 'LiteSpeed',
        component: () => import('@/views/LiteSpeed/LiteSpeed.vue'),
        meta: { requiresAuth: true, title: 'LiteSpeed配置' },
      },
      {
        path: 'linux',
        name: 'Linux',
        component: () => import('@/views/System/SystemManage.vue'),
        meta: { requiresAuth: true, title: '系统管理', defaultTab: 'status' },
      },
      {
        path: 'system/settings',
        name: 'SystemSettings',
        component: () => import('@/views/System/Settings.vue'),
        meta: { requiresAuth: true, title: '系统设置' },
      },
      {
        path: 'mariadb',
        name: 'MariaDB',
        component: () => import('@/views/MariaDB/MariaDB.vue'),
        meta: { requiresAuth: true, title: 'MariaDB管理' },
      },
      {
        path: 'file-manager',
        name: 'FileManager',
        component: () => import('@/views/FileManager/FileManager.vue'),
        meta: { requiresAuth: true, title: '文件管理器' },
      },
      {
        path: 'security',
        name: 'Security',
        component: () => import('@/views/Security/Security.vue'),
        meta: { requiresAuth: true, title: '安全管理' },
      },
      {
        path: 'tools',
        name: 'OneClickTools',
        component: () => import('@/views/Tools/OneClickTools.vue'),
        meta: { requiresAuth: true, title: 'AI工具' },
      },
      {
        path: 'backup',
        name: 'Backup',
        component: () => import('@/views/Backup/Backup.vue'),
        meta: { requiresAuth: true, title: '备份管理' },
      },
      {
        path: 'tasks',
        name: 'TaskList',
        component: () => import('@/views/Task/TaskList.vue'),
        meta: { requiresAuth: true, title: '任务列表' },
      },
      {
        path: 'nginx',
        name: 'Nginx',
        component: () => import('@/views/System/SystemManage.vue'),
        meta: { requiresAuth: true, title: '系统管理', defaultTab: 'nginx' },
      },
      {
        path: 'system-manage',
        name: 'SystemManage',
        component: () => import('@/views/System/SystemManage.vue'),
        meta: { requiresAuth: true, title: '系统管理', defaultTab: 'status' },
      },
      {
        path: 'system',
        name: 'System',
        component: () => import('@/views/System/System.vue'),
        meta: { requiresAuth: true, title: '系统信息' },
      },
      {
        path: 'monitor',
        name: 'Monitor',
        component: () => import('@/views/Monitor/Monitor.vue'),
        meta: { requiresAuth: true, title: '监控中心' },
      },
      {
        path: 'apps',
        name: 'Apps',
        component: () => import('@/views/Apps/OneClick.vue'),
        meta: { requiresAuth: true, title: '一键应用' },
      },
    ],
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

// Set page title
function setPageTitle(title) {
  const newTitle = title ? `${title} - 三国面板` : '三国面板'
  console.log('Setting page title:', newTitle)
  document.title = newTitle
  console.log('Document.title after setting:', document.title)
}

// Navigation guard
router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('token')
  if (to.meta.requiresAuth && !token) {
    // For now, allow navigation if no token during development
    // next({ name: 'Login' })
    next()
  } else {
    next()
  }
})

// Set page title after navigation completes
router.afterEach((to) => {
  console.log('Navigation to:', to.path, 'meta.title:', to.meta.title)
  setPageTitle(to.meta.title)
})

export default router
