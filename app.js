App({
  onLaunch() {
    // 初始化提醒数据
    const reminders = wx.getStorageSync('reminders') || []
    this.globalData.reminders = reminders
  },
  globalData: {
    reminders: []
  }
})

