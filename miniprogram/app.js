App({
  onLaunch() {
    // 不再使用本地存储，数据从服务端获取
    this.globalData.reminders = []
  },
  globalData: {
    reminders: []
  }
})

