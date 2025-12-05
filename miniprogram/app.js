const api = require('./utils/api.js')

App({
  onLaunch() {
    // 不再使用本地存储，数据从服务端获取
    this.globalData.reminders = []
    
    // 开发环境：尝试自动检测开发服务器 IP（可选）
    try {
      const accountInfo = wx.getAccountInfoSync()
      if (accountInfo.miniProgram.envVersion === 'develop') {
        // 只在开发版时自动检测，避免影响性能
        // 如果需要自动检测，取消下面的注释
        // api.detectDevServerIP().then(ip => {
        //   console.log('自动检测到开发服务器 IP:', ip)
        // })
      }
    } catch (e) {
      // 忽略错误
    }
  },
  globalData: {
    reminders: []
  }
})

