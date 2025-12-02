// add.js
const subscribeMessage = require('../../utils/subscribeMessage.js')

Page({
  data: {
    reminderTitle: '',
    enableSubscribe: false,
    selectedTime: '',
    reminderTime: null, // 存储时间戳
    timeRange: [
      [
        { label: '今天', value: 0 },
        { label: '明天', value: 1 },
        { label: '后天', value: 2 }
      ],
      [
        { label: '00:00', value: 0 },
        { label: '01:00', value: 1 },
        { label: '02:00', value: 2 },
        { label: '03:00', value: 3 },
        { label: '04:00', value: 4 },
        { label: '05:00', value: 5 },
        { label: '06:00', value: 6 },
        { label: '07:00', value: 7 },
        { label: '08:00', value: 8 },
        { label: '09:00', value: 9 },
        { label: '10:00', value: 10 },
        { label: '11:00', value: 11 },
        { label: '12:00', value: 12 },
        { label: '13:00', value: 13 },
        { label: '14:00', value: 14 },
        { label: '15:00', value: 15 },
        { label: '16:00', value: 16 },
        { label: '17:00', value: 17 },
        { label: '18:00', value: 18 },
        { label: '19:00', value: 19 },
        { label: '20:00', value: 20 },
        { label: '21:00', value: 21 },
        { label: '22:00', value: 22 },
        { label: '23:00', value: 23 }
      ]
    ],
    timeIndex: [0, 0]
  },

  onLoad() {
    // 页面加载
  },

  // 输入提醒内容
  onTitleInput(e) {
    this.setData({
      reminderTitle: e.detail.value
    })
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
    this.updateSelectedTime()
  },

  // 时间选择器改变
  onTimeChange(e) {
    this.setData({
      timeIndex: e.detail.value
    })
    this.updateSelectedTime()
  },

  // 更新选中的时间显示
  updateSelectedTime() {
    const timeRange = this.data.timeRange
    const timeIndex = this.data.timeIndex
    
    if (timeRange[0] && timeRange[0][timeIndex[0]] && timeRange[1] && timeRange[1][timeIndex[1]]) {
      const dayLabel = timeRange[0][timeIndex[0]].label
      const hourLabel = timeRange[1][timeIndex[1]].label
      
      // 计算实际时间戳
      const now = new Date()
      const day = timeIndex[0]
      const hour = timeIndex[1]
      
      const targetDate = new Date(now)
      targetDate.setDate(now.getDate() + day)
      targetDate.setHours(hour, 0, 0, 0)
      
      this.setData({
        selectedTime: `${dayLabel} ${hourLabel}`,
        reminderTime: targetDate.getTime()
      })
    }
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
      time: this.data.selectedTime || '',
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
        time: this.data.selectedTime,
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

