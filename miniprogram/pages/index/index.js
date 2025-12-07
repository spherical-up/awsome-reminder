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
    loading: false,
    shareReminderId: null,  // 用于分享的提醒ID
    currentShareReminder: null  // 当前正在分享的提醒信息
  },

  onLoad(options) {
    // 检查是否是分享的提醒
    if (options.reminder_id && options.action === 'accept') {
      this.handleSharedReminder(options.reminder_id)
      return
    }
    
    this.loadReminders()
  },

  onShow() {
    this.loadReminders()
  },

  // 加载提醒列表
  async loadReminders() {
    this.setData({ loading: true })
    try {
      // getReminders 已经返回了所有提醒（包括被分配的）
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
    
    // 权限检查：如果是被分享的提醒（fromOwner为true），不能编辑
    if (reminder.fromOwner) {
      wx.showToast({
        title: '不能编辑他人分享的提醒',
        icon: 'none',
        duration: 2000
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
    
    // 权限检查：如果是被分享的提醒（fromOwner为true），不能删除
    if (reminder.fromOwner) {
      wx.showToast({
        title: '不能删除他人分享的提醒',
        icon: 'none',
        duration: 2000
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
  },

  // 分享提醒给好友（点击分享按钮时调用，用于权限验证）
  async shareReminder(e) {
    const reminder = e.currentTarget.dataset.reminder
    if (!reminder || !reminder.id) {
      wx.showToast({
        title: '提醒信息错误',
        icon: 'none'
      })
      return
    }
    
    try {
      const openid = await api.getUserOpenid()
      
      // 权限控制1：前端验证是否是提醒创建者
      if (reminder.ownerOpenid && reminder.ownerOpenid !== openid) {
        wx.showToast({
          title: '只有创建者可以分享',
          icon: 'none',
          duration: 2000
        })
        return
      }
      
      // 权限控制2：如果是被分配的提醒，不能分享
      if (reminder.fromOwner) {
        wx.showToast({
          title: '不能分享他人分享的提醒',
          icon: 'none',
          duration: 2000
        })
        return
      }
      
      // 设置分享数据，用于onShareAppMessage
      this.setData({
        shareReminderId: reminder.id,
        currentShareReminder: reminder
      })
      
      // 注意：使用 open-type="share" 的 button 会自动触发分享菜单
      // 不需要调用 wx.showShareMenu
    } catch (err) {
      console.error('分享提醒验证失败', err)
      wx.showToast({
        title: '分享验证失败',
        icon: 'none',
        duration: 2000
      })
    }
  },

  // 处理分享的提醒
  async handleSharedReminder(reminderId) {
    try {
      wx.showModal({
        title: '收到提醒分享',
        content: '是否接受这个提醒？',
        success: async (res) => {
          if (res.confirm) {
            await this.acceptSharedReminder(reminderId)
          } else {
            // 拒绝或取消，正常加载列表
            this.loadReminders()
          }
        },
        fail: () => {
          this.loadReminders()
        }
      })
    } catch (err) {
      console.error('处理分享提醒失败', err)
      this.loadReminders()
    }
  },

  // 接受分享的提醒
  async acceptSharedReminder(reminderId) {
    try {
      wx.showLoading({ title: '接受中...' })
      
      const openid = await api.getUserOpenid()
      const result = await api.acceptReminder(reminderId, openid)
      
      wx.hideLoading()
      
      // 处理重复接受的情况
      if (result.alreadyAccepted) {
        wx.showModal({
          title: '提示',
          content: result.message || '您已经接受过此提醒',
          showCancel: false,
          success: () => {
            this.loadReminders()
          }
        })
        return
      }
      
      if (result.message) {
        wx.showToast({
          title: result.message,
          icon: 'none',
          duration: 2000
        })
      } else {
        wx.showToast({
          title: '已接受提醒',
          icon: 'success'
        })
      }
      
      // 重新加载列表
      await this.loadReminders()
    } catch (err) {
      wx.hideLoading()
      console.error('接受提醒失败', err)
      
      // 处理各种错误情况
      let errorMsg = err.message || '接受失败'
      
      if (errorMsg.includes('已经接受') || errorMsg.includes('alreadyAccepted')) {
        errorMsg = '您已经接受过此提醒'
      } else if (errorMsg.includes('不能接受自己')) {
        errorMsg = '不能接受自己创建的提醒'
      } else if (errorMsg.includes('400')) {
        errorMsg = '无法接受此提醒，可能已经接受过'
      }
      
      wx.showModal({
        title: '接受失败',
        content: errorMsg,
        showCancel: false,
        success: () => {
          this.loadReminders()
        }
      })
    }
  },

  // 页面分享配置
  onShareAppMessage(options) {
    // 获取分享的提醒ID
    const reminderId = options.from === 'button' 
      ? (options.target.dataset.reminderId || this.data.shareReminderId)
      : this.data.shareReminderId
    
    if (reminderId) {
      // 异步调用后端API记录分享（不阻塞分享流程）
      api.getUserOpenid().then(openid => {
        return api.shareReminder(reminderId, openid)
      }).then(() => {
        console.log('分享记录成功')
      }).catch(err => {
        console.error('分享记录失败:', err)
        // 记录失败不影响分享流程
      })
      
      // 获取提醒信息用于分享标题
      const reminder = this.data.currentShareReminder || 
        this.data.reminders.find(r => r.id === reminderId)
      
      const shareTitle = reminder 
        ? `[提醒] ${reminder.thing1 || reminder.title || '我有一个提醒想分享给你'}`
        : '我有一个提醒想分享给你'
      
      const assignerOpenid = reminder?.ownerOpenid || this.data.currentShareReminder?.ownerOpenid || ''
      
      return {
        title: shareTitle,
        path: `/pages/index/index?reminder_id=${reminderId}&action=accept&assigner_openid=${assignerOpenid}`,
        imageUrl: '' // 可选：分享图片
      }
    }
    
    return {
      title: '松鼠小记 - 提醒助手',
      path: '/pages/index/index'
    }
  }
})

