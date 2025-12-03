// index.js
const app = getApp()

Page({
  data: {
    reminders: [],
    showModal: false,
    newReminderTitle: '',
    newReminderTime: '',
    inputFocus: false,
    totalCount: 0,
    completedCount: 0
  },

  onLoad() {
    this.loadReminders()
  },

  onShow() {
    this.loadReminders()
  },

  // 加载提醒列表
  loadReminders() {
    const reminders = wx.getStorageSync('reminders') || []
    const completedCount = reminders.filter(r => r.completed).length
    this.setData({
      reminders: reminders,
      totalCount: reminders.length,
      completedCount: completedCount
    })
    app.globalData.reminders = reminders
  },

  // 跳转到添加页面
  showAddModal() {
    wx.navigateTo({
      url: '/pages/add/add'
    })
  },

  // 隐藏添加弹窗
  hideAddModal() {
    this.setData({
      showModal: false,
      inputFocus: false
    })
  },

  // 阻止事件冒泡
  stopPropagation() {
    // 空函数，用于阻止事件冒泡
  },

  // 输入提醒标题
  onTitleInput(e) {
    // van-field 的 input 事件直接返回 value
    const value = typeof e.detail === 'string' ? e.detail : (e.detail?.value || e.detail)
    this.setData({
      newReminderTitle: value
    })
  },

  // 输入提醒时间
  onTimeInput(e) {
    // van-field 的 input 事件直接返回 value
    const value = typeof e.detail === 'string' ? e.detail : (e.detail?.value || e.detail)
    this.setData({
      newReminderTime: value
    })
  },

  // 添加提醒
  addReminder() {
    const title = this.data.newReminderTitle.trim()
    if (!title) {
      wx.showToast({
        title: '请输入提醒内容',
        icon: 'none'
      })
      return
    }

    const reminders = this.data.reminders
    const newReminder = {
      id: Date.now(),
      title: title,
      time: this.data.newReminderTime.trim() || '',
      completed: false,
      createTime: new Date().toLocaleString('zh-CN')
    }

    reminders.unshift(newReminder)
    wx.setStorageSync('reminders', reminders)
    
    this.loadReminders()
    this.hideAddModal()
    
    wx.showToast({
      title: '添加成功',
      icon: 'success'
    })
  },

  // 切换提醒完成状态
  toggleReminder(e) {
    const index = e.currentTarget.dataset.index
    const reminders = this.data.reminders
    reminders[index].completed = !reminders[index].completed
    
    wx.setStorageSync('reminders', reminders)
    this.loadReminders()
    
    const status = reminders[index].completed ? '已完成' : '未完成'
    wx.showToast({
      title: status,
      icon: 'success',
      duration: 1000
    })
  },

  // 删除提醒
  deleteReminder(e) {
    const index = e.currentTarget.dataset.index
    const that = this
    
    wx.showModal({
      title: '确认删除',
      content: '确定要删除这条提醒吗？',
      success(res) {
        if (res.confirm) {
          const reminders = that.data.reminders
          reminders.splice(index, 1)
          wx.setStorageSync('reminders', reminders)
          that.loadReminders()
          
          wx.showToast({
            title: '删除成功',
            icon: 'success'
          })
        }
      }
    })
  }
})

