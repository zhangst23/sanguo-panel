import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    redirect: '/dashboard',
  },
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/Login/Login.vue'),
    meta: { requiresAuth: false },
  },
  {
    path: '/',
    component: () => import('@/components/layout/BaseLayout.vue'),
    children: [
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: () => import('@/views/Dashboard/Dashboard.vue'),
        meta: { requiresAuth: true },
      },
      {
        path: 'website',
        name: 'Website',
        component: () => import('@/views/Website/WebsiteList.vue'),
        meta: { requiresAuth: true },
      },
      {
        path: 'cache',
        name: 'Cache',
        component: () => import('@/views/Cache/Cache.vue'),
        meta: { requiresAuth: true },
      },
      {
        path: 'ssl',
        name: 'SSL',
        component: () => import('@/views/SSL/SSL.vue'),
        meta: { requiresAuth: true },
      },
      {
        path: 'image',
        name: 'Image',
        component: () => import('@/views/Image/Image.vue'),
        meta: { requiresAuth: true },
      },
      {
        path: 'database-adv',
        name: 'DatabaseAdv',
        component: () => import('@/views/Database/DatabaseAdv.vue'),
        meta: { requiresAuth: true },
      },
      {
        path: 'assets',
        name: 'Assets',
        component: () => import('@/views/Assets/Assets.vue'),
        meta: { requiresAuth: true },
      },
      {
        path: 'cdn',
        name: 'CDN',
        component: () => import('@/views/CDN/CDN.vue'),
        meta: { requiresAuth: true },
      },
      {
        path: 'ultimate',
        name: 'Ultimate',
        component: () => import('@/views/Ultimate/Ultimate.vue'),
        meta: { requiresAuth: true },
      },
      {
        path: 'litespeed',
        name: 'LiteSpeed',
        component: () => import('@/views/LiteSpeed/LiteSpeed.vue'),
        meta: { requiresAuth: true },
      },
      {
        path: 'php',
        name: 'PHP',
        component: () => import('@/views/PHP/PHP.vue'),
        meta: { requiresAuth: true },
      },
      {
        path: 'mariadb',
        name: 'MariaDB',
        component: () => import('@/views/MariaDB/MariaDB.vue'),
        meta: { requiresAuth: true },
      },
      {
        path: 'redis',
        name: 'Redis',
        component: () => import('@/views/Redis/Redis.vue'),
        meta: { requiresAuth: true },
      },
      {
        path: 'security',
        name: 'Security',
        component: () => import('@/views/Security/Security.vue'),
        meta: { requiresAuth: true },
      },
      {
        path: 'system',
        name: 'System',
        component: () => import('@/views/System/System.vue'),
        meta: { requiresAuth: true },
      },
      {
        path: 'monitor',
        name: 'Monitor',
        component: () => import('@/views/Monitor/Monitor.vue'),
        meta: { requiresAuth: true },
      },
      {
        path: 'apps',
        name: 'Apps',
        component: () => import('@/views/Apps/OneClick.vue'),
        meta: { requiresAuth: true },
      },
      {
        path: 'backup',
        name: 'Backup',
        component: () => import('@/views/Backup/Backup.vue'),
        meta: { requiresAuth: true },
      },
    ],
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

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

export default router
