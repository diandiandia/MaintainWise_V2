import { createRouter, createWebHistory, RouteRecordRaw } from 'vue-router'
import MainLayout from '../layout/MainLayout.vue'

const routes: RouteRecordRaw[] = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('../views/login/LoginView.vue'),
    meta: { title: '用户登录', public: true }
  },
  {
    path: '/force-change-password',
    name: 'ForceChangePassword',
    component: () => import('../views/auth/ForceChangePasswordView.vue'),
    meta: { title: '首次登录安全改密' }
  },
  {
    path: '/',
    component: MainLayout,
    redirect: '/dashboard',
    children: [
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: () => import('../views/dashboard/DashboardView.vue'),
        meta: { title: '数据平台' }
      },
      {
        path: 'equipments',
        name: 'Equipments',
        component: () => import('../views/equipments/EquipmentListView.vue'),
        meta: { title: '设备信息' }
      },
      {
        path: 'maintenance',
        name: 'Maintenance',
        component: () => import('../views/maintenance/MaintenanceListView.vue'),
        meta: { title: '设备维护' }
      },
      {
        path: 'workorders',
        name: 'WorkOrders',
        component: () => import('../views/workorders/WorkOrderKanbanView.vue'),
        meta: { title: '现场维护单' }
      },
      {
        path: 'knowledge',
        name: 'Knowledge',
        component: () => import('../views/knowledge/KnowledgeListView.vue'),
        meta: { title: '后来人知识库' }
      },
      {
        path: 'users',
        name: 'Users',
        component: () => import('../views/users/UserManagementView.vue'),
        meta: { title: '用户管理', roles: ['ADMIN'] }
      },
      {
        path: 'settings',
        name: 'Settings',
        component: () => import('../views/settings/SettingsView.vue'),
        meta: { title: '系统设置与热备', roles: ['ADMIN'] }
      },
      {
        path: 'system-docs',
        alias: ['/docs', 'docs'],
        name: 'SystemDocs',
        component: () => import('../views/docs/DocsReaderView.vue'),
        meta: { title: '系统设计文档与帮助' }
      }
    ]
  },
  {
    path: '/:pathMatch(.*)*',
    redirect: '/dashboard'
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('maintainwise_token')
  const userStr = localStorage.getItem('maintainwise_user')
  const user = userStr ? JSON.parse(userStr) : null

  // 1. 未登录拦截
  if (!to.meta.public && !token) {
    return next({ name: 'Login' })
  }

  // 2. 登录状态下的安全隔离拦截
  if (token && user) {
    // 若处于首次登录或重置后的强制改密状态，绝对禁止访问除改密页以外的任何页面
    if (user.must_change_password) {
      if (to.name !== 'ForceChangePassword') {
        return next({ name: 'ForceChangePassword' })
      }
      return next()
    }

    // 密码已达标正常用户，禁止重复进入强制改密页或登录页
    if (to.name === 'ForceChangePassword' || to.name === 'Login') {
      return next({ name: 'Dashboard' })
    }

    // 角色鉴权拦截
    if (to.meta.roles && Array.isArray(to.meta.roles)) {
      if (!user.role || !(to.meta.roles as string[]).includes(user.role)) {
        return next({ name: 'Dashboard' })
      }
    }
  }

  next()
})

export default router
