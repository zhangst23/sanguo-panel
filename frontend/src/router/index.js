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
