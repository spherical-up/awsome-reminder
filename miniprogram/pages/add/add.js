// add.js
const subscribeMessage = require('../../utils/subscribeMessage.js')

Page({
  data: {
    thing1: '', // 事项主题
    thing4: '', // 事项描述
    enableSubscribe: false,
    formattedTime: '', // 格式化显示：2024-01-01 10:30:00
    reminderTime: null, // 存储时间戳（毫秒）
    minDate: '', // 最小日期（今天）
    minDateTimestamp: 0, // 最小日期时间戳
    showDateTimePicker: false, // 显示日期时间选择器
    dateTimePickerValue: Date.now(), // 日期时间选择器值（时间戳）
    textareaAutosize: {
      minHeight: 160, // 最小高度 160rpx (约 80px)
      maxHeight: 300  // 最大高度 300rpx (约 150px)
    }
  },

  onLoad() {
    // 设置最小日期为今天
    const today = new Date()
    today.setHours(0, 0, 0, 0)
    const year = today.getFullYear()
    const month = String(today.getMonth() + 1).padStart(2, '0')
    const day = String(today.getDate()).padStart(2, '0')
    const minDate = `${year}-${month}-${day}`
    
    this.setData({
      minDate: minDate,
      minDateTimestamp: today.getTime(),
      dateTimePickerValue: today.getTime()
    })
  },

  // 输入事项主题
  onThing1Input(e) {
    // van-field 的 input 事件直接返回 value
    const value = typeof e.detail === 'string' ? e.detail : (e.detail?.value || e.detail)
    this.setData({
      thing1: value
    })
  },

  // 输入事项描述
  onThing4Input(e) {
    // van-field 的 input 事件直接返回 value
    const value = typeof e.detail === 'string' ? e.detail : (e.detail?.value || e.detail)
    this.setData({
      thing4: value
    })
  },

  // 显示日期时间选择器
  showDateTimePicker() {
    // 如果有已选时间，使用已选时间；否则使用当前时间
    const currentValue = this.data.reminderTime || Date.now()
    this.setData({
      showDateTimePicker: true,
      dateTimePickerValue: currentValue
    })
  },

  // 隐藏日期时间选择器
  hideDateTimePicker() {
    this.setData({
      showDateTimePicker: false
    })
  },

  // 日期时间选择确认
  onDateTimeConfirm(e) {
    const timestamp = typeof e.detail === 'number' ? e.detail : (e.detail?.value || Date.now())
    const date = new Date(timestamp)
    
    // 检查时间是否有效
    if (isNaN(date.getTime())) {
      console.error('日期时间无效:', timestamp)
      return
    }
    
    // 格式化显示
    const formatted = this.formatDateTime(date)
    
    this.setData({
      reminderTime: timestamp,
      formattedTime: formatted,
      showDateTimePicker: false
    })
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
    // van-switch 的 change 事件返回 checked 值
    const enable = e.detail
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
        'is4mEq0nlt5fJRn-Pflnr-wJxoCKOz9qty857QmH7Bw'
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
    const thing1 = this.data.thing1.trim()
    const thing4 = this.data.thing4.trim()
    
    // 验证事项主题
    if (!thing1) {
      wx.showToast({
        title: '请输入事项主题',
        icon: 'none',
        duration: 2000
      })
      return
    }

    // 验证事项时间
    if (!this.data.reminderTime) {
      wx.showToast({
        title: '请选择事项时间',
        icon: 'none',
        duration: 2000
      })
      return
    }

    // 验证事项描述
    if (!thing4) {
      wx.showToast({
        title: '请输入事项描述',
        icon: 'none',
        duration: 2000
      })
      return
    }

    // 如果开启了订阅，确保已授权
    if (this.data.enableSubscribe) {
      // 检查是否已授权，如果没有则请求授权
      await this.requestSubscribe()
    }

    // 获取现有提醒列表
    const reminders = wx.getStorageSync('reminders') || []
    
    // 创建新提醒
    const newReminder = {
      id: Date.now(),
      title: thing1, // 保留 title 字段用于兼容
      thing1: thing1, // 事项主题
      thing4: thing4, // 事项描述
      time: this.data.formattedTime, // 事项时间（必填）
      reminderTime: this.data.reminderTime, // 事项时间戳（必填）
      completed: false,
      enableSubscribe: this.data.enableSubscribe,
      createTime: new Date().toLocaleString('zh-CN')
    }

    // 添加到列表开头
    reminders.unshift(newReminder)
    
    // 保存到本地存储
    wx.setStorageSync('reminders', reminders)

    // 如果开启了订阅，调用服务端API（时间现在是必填的）
    if (this.data.enableSubscribe) {
      // 调用服务端API，将提醒信息发送到服务器
      // 服务端会在提醒时间到达时发送订阅消息
      const api = require('../../utils/api.js')
      
      api.createReminder({
        title: thing1, // 保留 title 字段用于兼容
        thing1: thing1, // 事项主题
        thing4: thing4, // 事项描述
        time: this.data.formattedTime, // 事项时间
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

