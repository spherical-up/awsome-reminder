// index.js
const app = getApp()
const api = require('../../utils/api.js')
const subscribeMessage = require('../../utils/subscribeMessage.js')

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
    // 防止重复加载
    if (this.data.loading) {
      console.log('正在加载中，跳过重复请求')
      return
    }
    
    this.setData({ loading: true })
    try {
      // getReminders 已经返回了所有提醒（包括被分配的）
      const reminders = await api.getReminders()
      
      // 获取当前用户的 openid，用于安全检查
      const currentOpenid = await api.getUserOpenid()
      
      // 对提醒列表进行安全检查，确保 fromOwner 字段正确
      // 同时检查是否过期
      const now = Date.now()
      const safeReminders = reminders.map(reminder => {
        // 安全检查：确保 fromOwner 字段正确
        // 核心判断逻辑：如果 ownerOpenid === openid，说明是自己创建的提醒，fromOwner = false
        // 如果 ownerOpenid !== openid，说明是被分享的提醒，fromOwner = true
        
        // 确保 ownerOpenid 和 openid 都存在
        const ownerOpenid = reminder.ownerOpenid || reminder.owner_openid || ''
        const reminderOpenid = reminder.openid || ''
        
        // 判断是否是自己创建的提醒
        // 条件：ownerOpenid === openid 且 ownerOpenid === currentOpenid
        // 或者 ownerOpenid === openid（即使 ownerOpenid !== currentOpenid，只要 ownerOpenid === openid 就是自己创建的）
        if (ownerOpenid && reminderOpenid && ownerOpenid === reminderOpenid) {
          // 自己创建的提醒，强制设置 fromOwner = false
          if (reminder.fromOwner) {
            console.warn('检测到数据不一致：自己创建的提醒被标记为 fromOwner，已修正', {
              id: reminder.id,
              ownerOpenid: ownerOpenid,
              openid: reminderOpenid,
              currentOpenid: currentOpenid,
              fromOwner: reminder.fromOwner
            })
          }
          reminder.fromOwner = false
        } else if (ownerOpenid && reminderOpenid && ownerOpenid !== reminderOpenid) {
          // 被分享的提醒，设置 fromOwner = true
          reminder.fromOwner = true
        } else {
          // 如果 ownerOpenid 或 openid 为空，默认认为是自己创建的（兼容旧数据）
          console.warn('提醒数据异常，ownerOpenid 或 openid 为空，默认设置为非分享', {
            id: reminder.id,
            ownerOpenid: ownerOpenid,
            openid: reminderOpenid
          })
          reminder.fromOwner = false
        }
        
        // 检查是否过期：如果提醒时间已过且未完成，标记为过期
        if (reminder.reminderTime && !reminder.completed) {
          const reminderTime = reminder.reminderTime
          reminder.isExpired = reminderTime < now
        } else {
          reminder.isExpired = false
        }
        
        // 确保 fromOwner 是布尔值，不能是 undefined
        reminder.fromOwner = Boolean(reminder.fromOwner)
        
        // 记录日志，便于调试（只在开发环境或数据异常时记录）
        if (reminder.fromOwner) {
          console.log('来自分享的提醒:', {
            id: reminder.id,
            thing1: reminder.thing1,
            ownerOpenid: ownerOpenid,
            openid: reminderOpenid,
            currentOpenid: currentOpenid,
            isExpired: reminder.isExpired,
            fromOwner: reminder.fromOwner
          })
        } else {
          // 只在数据异常时记录日志
          if (ownerOpenid && reminderOpenid && ownerOpenid !== reminderOpenid) {
            console.warn('数据异常：ownerOpenid !== openid 但 fromOwner = false', {
              id: reminder.id,
              ownerOpenid: ownerOpenid,
              openid: reminderOpenid,
              currentOpenid: currentOpenid,
              fromOwner: reminder.fromOwner
            })
          }
        }
        
        return reminder
      })
      
      const completedCount = safeReminders.filter(r => r.completed).length
      
      // 强制更新数据，确保安卓手机也能正常刷新
      this.setData({
        reminders: safeReminders,
        totalCount: safeReminders.length,
        completedCount: completedCount,
        loading: false
      }, () => {
        // setData 完成后的回调，确保数据已更新
        console.log('提醒列表已更新，数量:', safeReminders.length)
      })
      
      app.globalData.reminders = safeReminders
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
    
    // 如果是被分享的提醒，跳转到只读详情页
    if (reminder.fromOwner) {
      wx.navigateTo({
        url: `/pages/add/add?id=${reminder.id}&readonly=true`
      })
      return
    }
    
    // 自己的提醒，可以编辑
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
      
      // 检查订阅消息授权状态，如果未授权则请求授权
      // 这样当B拒绝提醒时，A才能收到通知
      try {
        const tmplId = 'is4mEq0nlt5fJRn-Pflnr-wJxoCKOz9qty857QmH7Bw'
        const authStatus = await subscribeMessage.checkSubscribeMessageStatus(tmplId)
        
        // 如果未授权或已拒绝，请求授权
        if (!authStatus || authStatus === 'reject') {
          console.log('订阅消息未授权，请求授权...')
          const tmplIds = [tmplId]
          const subscribeRes = await subscribeMessage.requestSubscribeMessage(tmplIds)
          
          // 检查授权结果
          let hasAccepted = false
          for (let id of tmplIds) {
            if (subscribeRes[id] === 'accept') {
              hasAccepted = true
              break
            }
          }
          
          if (hasAccepted) {
            console.log('✅ 订阅消息授权成功，可以接收拒绝通知')
          } else {
            console.log('⚠️ 用户未授权订阅消息，拒绝提醒时将无法收到通知')
          }
        } else if (authStatus === 'accept') {
          console.log('✅ 订阅消息已授权')
        } else if (authStatus === 'ban') {
          console.log('⚠️ 订阅消息被永久拒绝，无法接收通知')
        }
      } catch (err) {
        console.error('检查/请求订阅消息授权失败', err)
        // 授权失败不影响分享操作
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
      // 先加载提醒列表，检查是否已经接受过
      const reminders = await api.getReminders()
      const currentOpenid = await api.getUserOpenid()
      
      // 获取分享的提醒详情
      let sharedReminder = null
      try {
        sharedReminder = await api.getReminder(reminderId)
      } catch (err) {
        console.error('获取分享提醒详情失败', err)
        // 如果获取失败，直接加载列表
        this.loadReminders()
        return
      }
      
      // 检查当前用户是否已经接受过这个提醒
      // 通过 owner_openid 和 reminder_time 匹配来判断
      const ownerOpenid = sharedReminder.ownerOpenid || sharedReminder.owner_openid
      const reminderTime = sharedReminder.reminderTime
      
      const alreadyAccepted = reminders.some(reminder => {
        // 检查是否是同一个提醒（通过 owner_openid 和 reminder_time 匹配）
        const reminderOwnerOpenid = reminder.ownerOpenid || reminder.owner_openid
        return reminderOwnerOpenid === ownerOpenid && 
               reminder.reminderTime === reminderTime &&
               reminder.openid === currentOpenid
      })
      
      if (alreadyAccepted) {
        // 已经接受过，直接加载列表，不显示弹窗
        console.log('用户已经接受过此提醒，直接加载列表')
        this.loadReminders()
        return
      }
      
      // 没有接受过，显示接受/拒绝弹窗
      wx.showModal({
        title: '收到提醒分享',
        content: '是否接受这个提醒？',
        success: async (res) => {
          if (res.confirm) {
            await this.acceptSharedReminder(reminderId)
          } else {
            // 拒绝提醒，通知创建者
            await this.rejectSharedReminder(reminderId)
          }
        },
        fail: () => {
          // 取消操作，不记录为拒绝
          this.loadReminders()
        }
      })
    } catch (err) {
      console.error('处理分享提醒失败', err)
      this.loadReminders()
    }
  },

  // 拒绝分享的提醒
  async rejectSharedReminder(reminderId) {
    try {
      wx.showLoading({ title: '处理中...' })
      
      const openid = await api.getUserOpenid()
      await api.rejectReminder(reminderId, openid)
      
      wx.hideLoading()
      
      wx.showToast({
        title: '已拒绝提醒',
        icon: 'success',
        duration: 1500
      })
      
      // 加载列表
      await this.loadReminders()
    } catch (err) {
      wx.hideLoading()
      console.error('拒绝提醒失败', err)
      wx.showToast({
        title: err.message || '拒绝失败',
        icon: 'none',
        duration: 2000
      })
      // 即使失败也加载列表
      this.loadReminders()
    }
  },

  // 接受分享的提醒
  async acceptSharedReminder(reminderId) {
    try {
      // 先检查订阅消息授权状态，如果没有授权，先请求授权
      const tmplId = 'is4mEq0nlt5fJRn-Pflnr-wJxoCKOz9qty857QmH7Bw'
      let hasAuthorized = false
      
      try {
        // 检查当前授权状态
        const authStatus = await subscribeMessage.checkSubscribeMessageStatus(tmplId)
        console.log('当前订阅消息授权状态:', authStatus)
        
        if (authStatus === 'accept') {
          // 已经授权
          hasAuthorized = true
          console.log('✅ 订阅消息已授权')
        } else if (authStatus === 'ban') {
          // 被永久拒绝，提示用户去设置中开启
          wx.showModal({
            title: '订阅消息被拒绝',
            content: '您已永久拒绝订阅消息，无法接收提醒通知。如需接收通知，请在"设置-订阅消息"中开启。',
            showCancel: false,
            confirmText: '知道了',
            success: () => {
              // 即使被拒绝，也允许接受提醒（只是收不到通知）
              this.doAcceptReminder(reminderId)
            }
          })
          return
        } else {
          // 未授权或被拒绝，请求授权
          console.log('订阅消息未授权，请求授权...')
          const tmplIds = [tmplId]
          const subscribeRes = await subscribeMessage.requestSubscribeMessage(tmplIds)
          
          // 检查授权结果
          for (let id of tmplIds) {
            if (subscribeRes[id] === 'accept') {
              hasAuthorized = true
              console.log('✅ 订阅消息授权成功')
              break
            }
          }
          
          if (!hasAuthorized) {
            // 用户拒绝了授权，询问是否继续接受提醒
            const res = await new Promise((resolve) => {
              wx.showModal({
                title: '需要授权',
                content: '您未授权订阅消息，提醒时间到达时将无法收到通知。是否继续接受此提醒？',
                success: (result) => resolve(result.confirm),
                fail: () => resolve(false)
              })
            })
            
            if (!res) {
              // 用户取消，不接受提醒
              return
            }
            // 用户选择继续，即使未授权也接受提醒
          }
        }
      } catch (err) {
        console.error('检查/请求订阅消息授权失败', err)
        // 授权失败不影响接受提醒，但询问用户是否继续
        const res = await new Promise((resolve) => {
          wx.showModal({
            title: '授权失败',
            content: '订阅消息授权失败，提醒时间到达时可能无法收到通知。是否继续接受此提醒？',
            success: (result) => resolve(result.confirm),
            fail: () => resolve(false)
          })
        })
        
        if (!res) {
          // 用户取消，不接受提醒
          return
        }
      }
      
      // 授权检查完成，执行接受提醒
      await this.doAcceptReminder(reminderId)
      
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

  // 执行接受提醒的操作
  async doAcceptReminder(reminderId) {
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
      
      // 显示接受成功提示
      if (result.message) {
        wx.showToast({
          title: result.message,
          icon: 'none',
          duration: 1500
        })
      } else {
        wx.showToast({
          title: '已接受提醒',
          icon: 'success',
          duration: 1500
        })
      }
      
      // 立即刷新列表（不等待toast）
      await this.loadReminders()
      
      // 多次刷新确保数据同步（解决安卓手机有时不刷新的问题）
      // 第一次刷新：立即刷新
      // 第二次刷新：500ms后刷新（确保数据已同步）
      // 第三次刷新：2000ms后刷新（toast消失后再次刷新）
      setTimeout(() => {
        this.loadReminders()
      }, 500)
      
      setTimeout(() => {
        this.loadReminders()
      }, 2000)
    } catch (err) {
      wx.hideLoading()
      console.error('执行接受提醒失败', err)
      throw err // 重新抛出错误，让上层处理
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

