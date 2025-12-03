// index.js
const app = getApp()
const api = require('../../utils/api.js')

Page({
  data: {
    reminders: [],
    showModal: false,
    newReminderTitle: '',
    newReminderTime: '',
    inputFocus: false,
    totalCount: 0,
    completedCount: 0,
    loading: false
  },

  onLoad() {
    this.loadReminders()
  },

  onShow() {
    this.loadReminders()
  },

  // 加载提醒列表
  async loadReminders() {
    this.setData({ loading: true })
    try {
      const reminders = await api.getReminders()
      const completedCount = reminders.filter(r => r.completed).length
      this.setData({
        reminders: reminders,
        totalCount: reminders.length,
        completedCount: completedCount,
        loading: false
      })
      app.globalData.reminders = reminders
    } catch (err) {
      console.error('加载提醒列表失败', err)
      wx.showToast({
        title: err.message || '加载失败',
        icon: 'none',
        duration: 2000
      })
      this.setData({ loading: false })
    }
  },

  // 跳转到添加页面
  showAddModal() {
    wx.navigateTo({
      url: '/pages/add/add'
    })
  },

  // 编辑提醒（跳转到编辑页面）
  editReminder(e) {
    const reminder = e.currentTarget.dataset.reminder
    if (!reminder || !reminder.id) {
      wx.showToast({
        title: '提醒信息错误',
        icon: 'none'
      })
      return
    }
    
    wx.navigateTo({
      url: `/pages/add/add?id=${reminder.id}`
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

  // 添加提醒（已废弃，现在通过 add 页面添加）
  addReminder() {
    // 此方法已废弃，添加提醒现在通过 add 页面完成
    wx.showToast({
      title: '请使用添加页面',
      icon: 'none'
    })
  },

  // 切换提醒完成状态
  async toggleReminder(e) {
    const reminder = e.currentTarget.dataset.reminder
    if (!reminder || !reminder.id) {
      wx.showToast({
        title: '提醒信息错误',
        icon: 'none'
      })
      return
    }
    
    const newCompleted = !reminder.completed
    
    try {
      await api.updateReminderComplete(reminder.id, newCompleted)
      
      // 更新本地数据
      const reminders = this.data.reminders.map(r => {
        if (r.id === reminder.id) {
          return { ...r, completed: newCompleted }
        }
        return r
      })
      
      const completedCount = reminders.filter(r => r.completed).length
      this.setData({
        reminders: reminders,
        completedCount: completedCount
      })
      
      const status = newCompleted ? '已完成' : '未完成'
      wx.showToast({
        title: status,
        icon: 'success',
        duration: 1000
      })
    } catch (err) {
      console.error('更新提醒状态失败', err)
      wx.showToast({
        title: err.message || '更新失败',
        icon: 'none',
        duration: 2000
      })
    }
  },

  // 删除提醒
  deleteReminder(e) {
    const reminder = e.currentTarget.dataset.reminder
    if (!reminder || !reminder.id) {
      wx.showToast({
        title: '提醒信息错误',
        icon: 'none'
      })
      return
    }
    
    const that = this
    
    wx.showModal({
      title: '确认删除',
      content: '确定要删除这条提醒吗？',
      success: async function(res) {
        if (res.confirm) {
          try {
            await api.deleteReminder(reminder.id)
            
            // 重新加载列表
            await that.loadReminders()
            
            wx.showToast({
              title: '删除成功',
              icon: 'success'
            })
          } catch (err) {
            console.error('删除提醒失败', err)
            wx.showToast({
              title: err.message || '删除失败',
              icon: 'none',
              duration: 2000
            })
          }
        }
      }
    })
  }
})

