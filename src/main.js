import { createApp } from 'vue'
import Antd from 'ant-design-vue'
import 'ant-design-vue/dist/reset.css'
import App from './App.vue'
import './style.css'
import { setupMockServer } from './utils/mock-server'

// 启动模拟服务器（仅用于演示）
setupMockServer()

const app = createApp(App)
app.use(Antd)
app.mount('#app')
