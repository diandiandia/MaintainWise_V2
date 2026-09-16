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
        path: 'docs',
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

  if (!to.meta.public && !token) {
    next({ name: 'Login' })
  } else if (to.name === 'Login' && token) {
    next({ name: 'Dashboard' })
  } else if (to.meta.roles && Array.isArray(to.meta.roles)) {
    if (!user || !(to.meta.roles as string[]).includes(user.role)) {
      next({ name: 'Dashboard' })
    } else {
      next()
    }
  } else {
    next()
  }
})

export default router
