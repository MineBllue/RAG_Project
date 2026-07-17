import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/login',
      name: 'Login',
      component: () => import('../views/Login.vue'),
    },
    {
      path: '/register',
      name: 'Register',
      component: () => import('../views/Register.vue'),
    },
    {
      path: '/',
      redirect: '/chat',
    },
    {
      path: '/chat',
      name: 'Chat',
      component: () => import('../views/Chat.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/knowledge',
      name: 'Knowledge',
      component: () => import('../views/Knowledge.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/faq-management',
      name: 'FAQManagement',
      component: () => import('../views/FAQManagement.vue'),
      meta: { requiresAuth: true },
    },
  ],
})

router.beforeEach((to, _from, next) => {
  const token = localStorage.getItem('access_token')

  // 检查 token 是否有效（简单 JWT 过期检查）
  let tokenValid = !!token
  if (token) {
    try {
      const payload = JSON.parse(atob(token.split('.')[1]))
      if (payload.exp && payload.exp * 1000 < Date.now()) {
        // token 已过期，尝试用 refresh_token 续期（不阻塞路由）
        tokenValid = false
      }
    } catch {
      tokenValid = false
    }
  }

  if (to.meta.requiresAuth && !tokenValid) {
    next('/login')
  } else if ((to.path === '/login' || to.path === '/register') && tokenValid) {
    next('/chat')
  } else {
    next()
  }
})

export default router
