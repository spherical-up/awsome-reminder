// add.js
const subscribeMessage = require('../../utils/subscribeMessage.js')
const api = require('../../utils/api.js')

Page({
  data: {
    reminderId: null, // 编辑模式下的提醒ID
    isEditMode: false, // 是否为编辑模式
    originalEnableSubscribe: false, // 编辑模式下原始的订阅状态
    thing1: '', // 事项主题
    thing4: '', // 事项描述
    enableSubscribe: false,
    formattedTime: '', // 格式化显示：2024-01-01 10:30:00
    reminderTime: null, // 存储时间戳（毫秒）
    minDate: '', // 最小日期（今天）
    minDateTimestamp: 0, // 最小日期时间戳
    showDateTimePicker: false, // 显示日期时间选择器
    dateTimePickerValue: Date.now(), // 日期时间选择器值（时间戳）
    pickerValue: [0, 0, 0, 0, 0, 0], // 多列选择器的当前值 [年, 月, 日, 时, 分, 秒]
    pickerRange: [[], [], [], [], [], []], // 多列选择器的数据范围
    textareaAutosize: {
      minHeight: 160, // 最小高度 160rpx (约 80px)
      maxHeight: 300  // 最大高度 300rpx (约 150px)
    }
  },

  async onLoad(options) {
    // 设置最小日期为今天
    const today = new Date()
    today.setHours(0, 0, 0, 0)
    const year = today.getFullYear()
    const month = String(today.getMonth() + 1).padStart(2, '0')
    const day = String(today.getDate()).padStart(2, '0')
    const minDate = `${year}-${month}-${day}`
    
    // 初始化选择器数据（使用当前时间）
    const now = new Date()
    this.initPickerData(now)
    
    this.setData({
      minDate: minDate,
      minDateTimestamp: today.getTime(),
      dateTimePickerValue: today.getTime()
    })

    // 检查是否是编辑模式
    if (options.id) {
      // ID 现在是字符串格式（openid_reminderTime），不需要 parseInt
      const reminderId = options.id
      this.setData({
        reminderId: reminderId,
        isEditMode: true
      })
      
      // 设置页面标题
      wx.setNavigationBarTitle({
        title: '编辑提醒'
      })
      
      // 加载提醒详情
      await this.loadReminderDetail(reminderId)
    } else {
      // 设置页面标题
      wx.setNavigationBarTitle({
        title: '添加提醒'
      })
    }
  },

  // 加载提醒详情
  async loadReminderDetail(reminderId) {
    try {
      wx.showLoading({
        title: '加载中...',
        mask: true
      })
      
      const reminder = await api.getReminder(reminderId)
      
      // 权限检查：如果是被分享的提醒（openid != ownerOpenid），不能编辑
      const currentOpenid = await api.getUserOpenid()
      const ownerOpenid = reminder.ownerOpenid || reminder.owner_openid
      const reminderOpenid = reminder.openid
      
      // 如果当前用户不是创建者，说明这是被分享的提醒，禁止编辑
      if (reminderOpenid !== ownerOpenid || currentOpenid !== ownerOpenid) {
        wx.hideLoading()
        wx.showModal({
          title: '提示',
          content: '不能编辑他人分享的提醒',
          showCancel: false,
          success: () => {
            wx.navigateBack()
          }
        })
        return
      }
      
      // 回填数据
      const reminderTime = reminder.reminderTime || Date.now()
      const date = new Date(reminderTime)
      const formatted = this.formatDateTime(date)
      const enableSubscribe = reminder.enableSubscribe || false
      
      this.setData({
        thing1: reminder.thing1 || reminder.title || '',
        thing4: reminder.thing4 || '',
        formattedTime: formatted,
        reminderTime: reminderTime,
        enableSubscribe: enableSubscribe,
        originalEnableSubscribe: enableSubscribe, // 保存原始的订阅状态
        dateTimePickerValue: reminderTime
      })
      
      wx.hideLoading()
    } catch (err) {
      console.error('加载提醒详情失败', err)
      wx.hideLoading()
      wx.showToast({
        title: err.message || '加载失败',
        icon: 'none',
        duration: 2000
      })
      // 加载失败，返回上一页
      setTimeout(() => {
        wx.navigateBack()
      }, 2000)
    }
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
    const date = new Date(currentValue)
    
    // 初始化选择器数据
    this.initPickerData(date)
    
    // 确保数据已设置后再显示弹窗
    setTimeout(() => {
      this.setData({
        showDateTimePicker: true,
        dateTimePickerValue: currentValue
      })
    }, 50)
  },

  // 初始化选择器数据
  initPickerData(date) {
    const now = new Date()
    const currentYear = now.getFullYear()
    const currentMonth = now.getMonth() + 1
    const currentDay = now.getDate()
    const currentHour = now.getHours()
    const currentMinute = now.getMinutes()
    const currentSecond = now.getSeconds()
    
    const year = date.getFullYear()
    const month = date.getMonth() + 1
    const day = date.getDate()
    const hour = date.getHours()
    const minute = date.getMinutes()
    const second = date.getSeconds()
    
    // 生成年份数组（当前年份及以后10年）
    const years = []
    for (let i = currentYear; i <= currentYear + 10; i++) {
      years.push(String(i))
    }
    
    // 根据选中的年份生成月份数组
    const months = []
    const minMonth = (year === currentYear) ? currentMonth : 1
    for (let i = minMonth; i <= 12; i++) {
      months.push(String(i).padStart(2, '0'))
    }
    
    // 根据选中的年月生成日期数组
    const daysInMonth = new Date(year, month, 0).getDate()
    const days = []
    const minDay = (year === currentYear && month === currentMonth) ? currentDay : 1
    for (let i = minDay; i <= daysInMonth; i++) {
      days.push(String(i).padStart(2, '0'))
    }
    
    // 根据选中的年月日生成小时数组
    const hours = []
    const minHour = (year === currentYear && month === currentMonth && day === currentDay) ? currentHour : 0
    for (let i = minHour; i <= 23; i++) {
      hours.push(String(i).padStart(2, '0'))
    }
    
    // 根据选中的年月日时生成分钟数组
    const minutes = []
    const minMinute = (year === currentYear && month === currentMonth && day === currentDay && hour === currentHour) ? currentMinute : 0
    for (let i = minMinute; i <= 59; i++) {
      minutes.push(String(i).padStart(2, '0'))
    }
    
    // 根据选中的年月日时分生成秒数组
    const seconds = []
    const minSecond = (year === currentYear && month === currentMonth && day === currentDay && hour === currentHour && minute === currentMinute) ? currentSecond : 0
    for (let i = minSecond; i <= 59; i++) {
      seconds.push(String(i).padStart(2, '0'))
    }
    
    // 计算当前选中索引
    let yearIndex = years.indexOf(String(year))
    if (yearIndex < 0) {
      yearIndex = 0 // 如果不在范围内，使用最小值
    }
    const monthIndex = months.indexOf(String(month).padStart(2, '0'))
    const dayIndex = days.indexOf(String(day).padStart(2, '0'))
    const hourIndex = hours.indexOf(String(hour).padStart(2, '0'))
    const minuteIndex = minutes.indexOf(String(minute).padStart(2, '0'))
    const secondIndex = seconds.indexOf(String(second).padStart(2, '0'))
    
    // 确保索引有效
    const finalMonthIndex = monthIndex >= 0 ? monthIndex : 0
    const finalDayIndex = dayIndex >= 0 ? dayIndex : 0
    const finalHourIndex = hourIndex >= 0 ? hourIndex : 0
    const finalMinuteIndex = minuteIndex >= 0 ? minuteIndex : 0
    const finalSecondIndex = secondIndex >= 0 ? secondIndex : 0
    
    const pickerRange = [years, months, days, hours, minutes, seconds]
    const pickerValue = [yearIndex, finalMonthIndex, finalDayIndex, finalHourIndex, finalMinuteIndex, finalSecondIndex]
    
    console.log('初始化选择器数据:', {
      pickerRange: pickerRange.map((arr, i) => `${['年', '月', '日', '时', '分', '秒'][i]}: ${arr.length}项`),
      pickerValue: pickerValue
    })
    
    this.setData({
      pickerRange: pickerRange,
      pickerValue: pickerValue
    })
  },

  // picker-view 变化事件
  onPickerViewChange(e) {
    const pickerValue = e.detail.value
    const pickerRange = [...this.data.pickerRange]
    const now = new Date()
    const currentYear = now.getFullYear()
    const currentMonth = now.getMonth() + 1
    const currentDay = now.getDate()
    const currentHour = now.getHours()
    const currentMinute = now.getMinutes()
    const currentSecond = now.getSeconds()
    
    const newYear = parseInt(pickerRange[0][pickerValue[0]])
    const newMonth = parseInt(pickerRange[1][pickerValue[1]])
    const newDay = pickerValue[2] < pickerRange[2].length ? parseInt(pickerRange[2][pickerValue[2]]) : 1
    const newHour = pickerValue[3] < pickerRange[3].length ? parseInt(pickerRange[3][pickerValue[3]]) : 0
    const newMinute = pickerValue[4] < pickerRange[4].length ? parseInt(pickerRange[4][pickerValue[4]]) : 0
    
    // 如果年份改变，需要更新月份数组
    if (pickerValue[0] !== this.data.pickerValue[0]) {
      const months = []
      const minMonth = (newYear === currentYear) ? currentMonth : 1
      for (let i = minMonth; i <= 12; i++) {
        months.push(String(i).padStart(2, '0'))
      }
      pickerRange[1] = months
      pickerValue[1] = 0 // 重置月份索引
    }
    
    // 如果年份或月份改变，需要更新日期数组
    if (pickerValue[0] !== this.data.pickerValue[0] || pickerValue[1] !== this.data.pickerValue[1]) {
      const daysInMonth = new Date(newYear, newMonth, 0).getDate()
      const days = []
      const minDay = (newYear === currentYear && newMonth === currentMonth) ? currentDay : 1
      for (let i = minDay; i <= daysInMonth; i++) {
        days.push(String(i).padStart(2, '0'))
      }
      pickerRange[2] = days
      pickerValue[2] = 0 // 重置日期索引
    }
    
    // 如果年月日改变，需要更新小时数组
    if (pickerValue[0] !== this.data.pickerValue[0] || pickerValue[1] !== this.data.pickerValue[1] || pickerValue[2] !== this.data.pickerValue[2]) {
      const hours = []
      const minHour = (newYear === currentYear && newMonth === currentMonth && newDay === currentDay) ? currentHour : 0
      for (let i = minHour; i <= 23; i++) {
        hours.push(String(i).padStart(2, '0'))
      }
      pickerRange[3] = hours
      pickerValue[3] = 0 // 重置小时索引
    }
    
    // 如果年月日时改变，需要更新分钟数组
    if (pickerValue[0] !== this.data.pickerValue[0] || pickerValue[1] !== this.data.pickerValue[1] || 
        pickerValue[2] !== this.data.pickerValue[2] || pickerValue[3] !== this.data.pickerValue[3]) {
      const minutes = []
      const minMinute = (newYear === currentYear && newMonth === currentMonth && newDay === currentDay && newHour === currentHour) ? currentMinute : 0
      for (let i = minMinute; i <= 59; i++) {
        minutes.push(String(i).padStart(2, '0'))
      }
      pickerRange[4] = minutes
      pickerValue[4] = 0 // 重置分钟索引
    }
    
    // 如果年月日时分改变，需要更新秒数组
    if (pickerValue[0] !== this.data.pickerValue[0] || pickerValue[1] !== this.data.pickerValue[1] || 
        pickerValue[2] !== this.data.pickerValue[2] || pickerValue[3] !== this.data.pickerValue[3] || 
        pickerValue[4] !== this.data.pickerValue[4]) {
      const seconds = []
      const minSecond = (newYear === currentYear && newMonth === currentMonth && newDay === currentDay && 
                         newHour === currentHour && newMinute === currentMinute) ? currentSecond : 0
      for (let i = minSecond; i <= 59; i++) {
        seconds.push(String(i).padStart(2, '0'))
      }
      pickerRange[5] = seconds
      pickerValue[5] = 0 // 重置秒索引
    }
    
    // 确保索引不超出范围
    for (let i = 0; i < pickerValue.length; i++) {
      if (pickerValue[i] >= pickerRange[i].length) {
        pickerValue[i] = pickerRange[i].length - 1
      }
    }
    
    this.setData({
      pickerValue: pickerValue,
      pickerRange: pickerRange
    })
  },

  // 选择器确认
  onPickerConfirm() {
    const pickerValue = this.data.pickerValue
    const pickerRange = this.data.pickerRange
    
    const year = parseInt(pickerRange[0][pickerValue[0]])
    const month = parseInt(pickerRange[1][pickerValue[1]]) - 1 // 月份从0开始
    const day = parseInt(pickerRange[2][pickerValue[2]])
    const hour = parseInt(pickerRange[3][pickerValue[3]])
    const minute = parseInt(pickerRange[4][pickerValue[4]])
    const second = parseInt(pickerRange[5][pickerValue[5]])
    
    const date = new Date(year, month, day, hour, minute, second)
    const timestamp = date.getTime()
    const now = Date.now()
    
    // 检查时间是否有效
    if (isNaN(date.getTime())) {
      console.error('日期时间无效:', timestamp)
      return
    }
    
    // 检查时间不能早于当前时间
    if (timestamp < now) {
      wx.showToast({
        title: '不能选择过去的时间',
        icon: 'none',
        duration: 2000
      })
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

  // 隐藏日期时间选择器
  hideDateTimePicker() {
    this.setData({
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

    // 授权逻辑：
    // 1. 新建模式：开启订阅时立即请求授权
    // 2. 编辑模式：只有从"未开启"变为"开启"时才请求授权
    //    如果原本就开启了订阅，用户切换开关时不需要重新授权
    if (enable) {
      if (!this.data.isEditMode) {
        // 新建模式：开启订阅时立即授权
        this.requestSubscribe()
      } else {
        // 编辑模式：只有从未开启变为开启时才授权
        if (!this.data.originalEnableSubscribe) {
          this.requestSubscribe()
        }
        // 如果原本就开启了订阅，用户切换开关时不需要授权
        // 授权会在保存时统一处理
      }
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
    // 如果是编辑模式，再次检查权限
    if (this.data.isEditMode && this.data.reminderId) {
      try {
        const reminder = await api.getReminder(this.data.reminderId)
        const currentOpenid = await api.getUserOpenid()
        const ownerOpenid = reminder.ownerOpenid || reminder.owner_openid
        const reminderOpenid = reminder.openid
        
        // 如果当前用户不是创建者，说明这是被分享的提醒，禁止保存
        if (reminderOpenid !== ownerOpenid || currentOpenid !== ownerOpenid) {
          wx.showToast({
            title: '不能编辑他人分享的提醒',
            icon: 'none',
            duration: 2000
          })
          return
        }
      } catch (err) {
        console.error('权限检查失败', err)
        wx.showToast({
          title: '权限验证失败',
          icon: 'none',
          duration: 2000
        })
        return
      }
    }
    
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

    // 处理订阅授权逻辑
    // 1. 新建模式：如果开启订阅，需要授权
    // 2. 编辑模式：只有从"未开启"变为"开启"时才需要授权
    //    如果原本就开启了订阅，编辑时保持开启，不需要重新授权
    const needAuth = this.data.isEditMode 
      ? (!this.data.originalEnableSubscribe && this.data.enableSubscribe) // 编辑模式：从未开启变为开启
      : this.data.enableSubscribe // 新建模式：开启订阅就需要授权
    
    if (needAuth) {
      await this.requestSubscribe()
    }

    const reminderData = {
      title: thing1, // 保留 title 字段用于兼容
      thing1: thing1, // 事项主题
      thing4: thing4, // 事项描述
      time: this.data.formattedTime, // 事项时间
      reminderTime: this.data.reminderTime,
      enableSubscribe: this.data.enableSubscribe
    }
    
    try {
      if (this.data.isEditMode && this.data.reminderId) {
        // 编辑模式：更新提醒
        await api.updateReminder(this.data.reminderId, reminderData)
        
        wx.showToast({
          title: '更新成功',
          icon: 'success',
          duration: 1500
        })
      } else {
        // 新建模式：创建提醒
        await api.createReminder(reminderData)
        
        wx.showToast({
          title: '添加成功',
          icon: 'success',
          duration: 1500
        })
      }

      // 延迟返回上一页，让用户看到成功提示
      setTimeout(() => {
        wx.navigateBack({
          delta: 1
        })
      }, 1500)
    } catch (err) {
      console.error('保存提醒失败', err)
      wx.showToast({
        title: err.message || '保存失败，请重试',
        icon: 'none',
        duration: 2000
      })
    }
  }
})

