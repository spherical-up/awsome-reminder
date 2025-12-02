// add.js
const subscribeMessage = require('../../utils/subscribeMessage.js')

Page({
  data: {
    reminderTitle: '',
    enableSubscribe: false,
    selectedDate: '', // 日期：YYYY-MM-DD
    selectedTime: '', // 时间显示：HH:mm:ss
    formattedTime: '', // 格式化显示：2024-01-01 10:30:00
    reminderTime: null, // 存储时间戳（毫秒）
    minDate: '', // 最小日期（今天）
    timeRange: [
      // 小时：00-23
      Array.from({ length: 24 }, (_, i) => String(i).padStart(2, '0')),
      // 分钟：00-59
      Array.from({ length: 60 }, (_, i) => String(i).padStart(2, '0')),
      // 秒：00-59
      Array.from({ length: 60 }, (_, i) => String(i).padStart(2, '0'))
    ],
    timeIndex: [0, 0, 0] // [小时, 分钟, 秒]
  },

  onLoad() {
    // 设置最小日期为今天
    const today = new Date()
    const year = today.getFullYear()
    const month = String(today.getMonth() + 1).padStart(2, '0')
    const day = String(today.getDate()).padStart(2, '0')
    const minDate = `${year}-${month}-${day}`
    
    this.setData({
      minDate: minDate
    })
  },

  // 输入提醒内容
  onTitleInput(e) {
    this.setData({
      reminderTitle: e.detail.value
    })
  },

  // 日期选择器改变
  onDateChange(e) {
    const date = e.detail.value // 格式：YYYY-MM-DD
    this.setData({
      selectedDate: date
    })
    this.updateReminderTime()
  },

  // 时间选择器列改变
  onTimeColumnChange(e) {
    const column = e.detail.column
    const value = e.detail.value
    const timeIndex = this.data.timeIndex
    timeIndex[column] = value
    this.setData({
      timeIndex: timeIndex
    })
    this.updateTimeDisplay()
    this.updateReminderTime()
  },

  // 时间选择器改变
  onTimeChange(e) {
    this.setData({
      timeIndex: e.detail.value
    })
    this.updateTimeDisplay()
    this.updateReminderTime()
  },

  // 更新时间显示（HH:mm:ss）
  updateTimeDisplay() {
    const timeIndex = this.data.timeIndex
    const hour = this.data.timeRange[0][timeIndex[0]]
    const minute = this.data.timeRange[1][timeIndex[1]]
    const second = this.data.timeRange[2][timeIndex[2]]
    const timeString = `${hour}:${minute}:${second}`
    
    this.setData({
      selectedTime: timeString
    })
  },

  // 更新提醒时间戳和格式化显示
  updateReminderTime() {
    const date = this.data.selectedDate
    const time = this.data.selectedTime
    
    if (date && time) {
      // 组合日期和时间：YYYY-MM-DD HH:mm:ss
      const dateTimeString = `${date} ${time}`
      
      // 转换为时间戳（毫秒）
      // 注意：小程序中 Date 构造函数需要将 - 替换为 /
      const targetDate = new Date(dateTimeString.replace(/-/g, '/'))
      const timestamp = targetDate.getTime()
      
      // 检查时间是否有效
      if (isNaN(timestamp)) {
        console.error('时间格式错误:', dateTimeString)
        return
      }
      
      // 格式化显示
      const formatted = this.formatDateTime(targetDate)
      
      this.setData({
        reminderTime: timestamp,
        formattedTime: formatted
      })
    } else {
      this.setData({
        reminderTime: null,
        formattedTime: ''
      })
    }
  },

  // 格式化日期时间显示
  formatDateTime(date) {
    const year = date.getFullYear()
    const month = String(date.getMonth() + 1).padStart(2, '0')
    const day = String(date.getDate()).padStart(2, '0')
    const hours = String(date.getHours()).padStart(2, '0')
    const minutes = String(date.getMinutes()).padStart(2, '0')
    const seconds = String(date.getSeconds()).padStart(2, '0')
    
    return `${year}-${month}-${day} ${hours}:${minutes}:${seconds}`
  },

  // 订阅开关改变
  onSubscribeChange(e) {
    const enable = e.detail.value
    this.setData({
      enableSubscribe: enable
    })

    // 如果开启订阅，请求订阅消息授权
    if (enable) {
      this.requestSubscribe()
    }
  },

  // 请求订阅消息
  async requestSubscribe() {
    try {
      // 订阅消息模板ID
      const tmplIds = [
        '_qZfC75otflYg8nc1suRZK27Ke-mzc_sh3Vtpv8tr2w'
      ]

      const res = await subscribeMessage.requestSubscribeMessage(tmplIds)
      
      // 检查订阅结果
      let hasAccepted = false
      for (let tmplId of tmplIds) {
        if (res[tmplId] === 'accept') {
          hasAccepted = true
          break
        }
      }

      if (hasAccepted) {
        wx.showToast({
          title: '订阅成功',
          icon: 'success'
        })
      } else {
        wx.showToast({
          title: '需要授权才能接收提醒',
          icon: 'none'
        })
      }
    } catch (err) {
      console.error('订阅消息失败', err)
      wx.showToast({
        title: '订阅失败，请重试',
        icon: 'none'
      })
    }
  },

  // 保存提醒
  async saveReminder() {
    const title = this.data.reminderTitle.trim()
    
    if (!title) {
      wx.showToast({
        title: '请输入提醒内容',
        icon: 'none',
        duration: 2000
      })
      return
    }

    // 如果开启了订阅但没有选择时间
    if (this.data.enableSubscribe && !this.data.reminderTime) {
      wx.showToast({
        title: '请选择提醒时间',
        icon: 'none',
        duration: 2000
      })
      return
    }

    // 如果选择了时间但未开启订阅，提示用户
    if (this.data.reminderTime && !this.data.enableSubscribe) {
      const res = await new Promise((resolve) => {
        wx.showModal({
          title: '提示',
          content: '已选择提醒时间，是否开启消息提醒？',
          success: (res) => resolve(res.confirm),
          fail: () => resolve(false)
        })
      })

      if (res) {
        this.setData({ enableSubscribe: true })
        await this.requestSubscribe()
      }
    }

    // 获取现有提醒列表
    const reminders = wx.getStorageSync('reminders') || []
    
    // 创建新提醒
    const newReminder = {
      id: Date.now(),
      title: title,
      time: this.data.formattedTime || '',
      reminderTime: this.data.reminderTime,
      completed: false,
      enableSubscribe: this.data.enableSubscribe,
      createTime: new Date().toLocaleString('zh-CN')
    }

    // 添加到列表开头
    reminders.unshift(newReminder)
    
    // 保存到本地存储
    wx.setStorageSync('reminders', reminders)

    // 如果开启了订阅且有提醒时间，调用服务端API
    if (this.data.enableSubscribe && this.data.reminderTime) {
      // 调用服务端API，将提醒信息发送到服务器
      // 服务端会在提醒时间到达时发送订阅消息
      const api = require('../../utils/api.js')
      
      api.createReminder({
        title: title,
        time: this.data.formattedTime,
        reminderTime: this.data.reminderTime,
        enableSubscribe: true
      }).then(() => {
        console.log('提醒已保存到服务端，将在指定时间发送订阅消息')
      }).catch((err) => {
        console.error('保存到服务端失败', err)
        // 即使服务端保存失败，本地也保存了，不影响使用
      })
    }
    
    // 显示成功提示
    wx.showToast({
      title: '添加成功',
      icon: 'success',
      duration: 1500
    })

    // 延迟返回上一页，让用户看到成功提示
    setTimeout(() => {
      wx.navigateBack({
        delta: 1
      })
    }, 1500)
  }
})

