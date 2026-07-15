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
  ],
})

router.beforeEach((to, _from, next) => {
  const token = localStorage.getItem('access_token')
  if (to.meta.requiresAuth && !token) {
    next('/login')
  } else if ((to.path === '/login' || to.path === '/register') && token) {
    next('/chat')
  } else {
    next()
  }
})

export default router
