// utils/api.js
// API 请求工具类

// 配置服务端地址
// 自动根据环境选择 API 地址

// 获取当前 IP（开发环境使用）
function getLocalIP() {
  // 优先从本地存储获取（如果之前设置过）
  const savedIP = wx.getStorageSync('dev_server_ip')
  if (savedIP) {
    console.log('使用已保存的开发服务器 IP:', savedIP)
    return savedIP
  }
  
  // 默认 IP（如果 IP 变化，可以通过以下方式更新：
  // 1. 在开发者工具控制台执行: 
  //    const api = require('./utils/api.js')
  //    api.setDevServerIP('新的IP地址')
  // 2. 或者修改下面的默认值
  const defaultIP = '10.0.1.130'
  
  // 常见的内网 IP 段（用于自动检测，可选）
  // 注意：小程序无法直接获取本机 IP，这里提供默认值和存储机制
  // 如果需要自动检测，可以在应用启动时调用 detectDevServerIP()
  
  return defaultIP
}

// 自动检测可用的开发服务器 IP（可选功能）
function detectDevServerIP() {
  return new Promise((resolve) => {
    const commonIPs = [
      '10.0.1.130',  // 当前默认 IP
      '192.168.31.100',  // 之前使用过的 IP
      '192.168.1.100',
      '192.168.0.100',
      '10.0.0.100'
    ]
    
    let checkedCount = 0
    let foundIP = null
    
    commonIPs.forEach(ip => {
      wx.request({
        url: `http://${ip}:5001/api/health`,
        method: 'GET',
        timeout: 2000,
        success: (res) => {
          if (res.statusCode === 200 && res.data.errcode === 0) {
            foundIP = ip
            console.log('检测到可用的开发服务器 IP:', ip)
            setDevServerIP(ip)
            resolve(ip)
          }
        },
        fail: () => {
          checkedCount++
          if (checkedCount === commonIPs.length && !foundIP) {
            // 所有 IP 都检测失败，使用默认值
            console.warn('未检测到可用的开发服务器，使用默认 IP')
            resolve(getLocalIP())
          }
        }
      })
    })
    
    // 如果很快找到，直接返回
    if (foundIP) {
      resolve(foundIP)
    }
  })
}

// 设置开发服务器 IP（用于 IP 变化时动态更新）
function setDevServerIP(ip) {
  if (ip && /^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$/.test(ip)) {
    wx.setStorageSync('dev_server_ip', ip)
    console.log('开发服务器 IP 已更新为:', ip)
    return true
  } else {
    console.error('无效的 IP 地址:', ip)
    return false
  }
}

// 清除开发服务器 IP 配置（恢复默认值）
function clearDevServerIP() {
  wx.removeStorageSync('dev_server_ip')
  console.log('已清除开发服务器 IP 配置，恢复默认值')
}

// 判断当前环境
function getAPIBaseURL() {
  try {
    // 获取小程序账号信息
    const accountInfo = wx.getAccountInfoSync()
    const envVersion = accountInfo.miniProgram.envVersion
    
    // envVersion 可能的值：
    // - 'develop': 开发版（开发者工具）
    // - 'trial': 体验版
    // - 'release': 正式版
    
    if (envVersion === 'release') {
      // 正式版：使用生产环境地址
      return 'https://www.6ht6.com/api'
    } else {
      // 开发版和体验版：使用开发环境地址
      const localIP = getLocalIP()
      return `http://${localIP}:5001/api`
    }
  } catch (e) {
    // 如果获取失败，默认使用开发环境
    console.warn('获取环境信息失败，使用开发环境:', e)
    const localIP = getLocalIP()
    return `http://${localIP}:5001/api`
  }
}

const API_BASE_URL = getAPIBaseURL()

// 输出当前使用的 API 地址（开发时可见）
console.log('当前 API 地址:', API_BASE_URL)

// ============================================
// 手动切换配置（如果自动检测不准确）
// ============================================
// 方式1: 强制使用开发环境
// const API_BASE_URL = `http://${getLocalIP()}:5001/api`

// 方式2: 强制使用生产环境
// const API_BASE_URL = 'https://www.6ht6.com/api'

// 方式3: 使用环境变量（如果配置了）
// const API_BASE_URL = process.env.API_BASE_URL || 'https://www.6ht6.com/api'

/**
 * 获取用户 openid
 * 需要通过 wx.login 获取 code，然后调用服务端接口换取 openid
 */
function getUserOpenid() {
  return new Promise((resolve, reject) => {
    // 先从缓存获取
    const cachedOpenid = wx.getStorageSync('user_openid')
    if (cachedOpenid) {
      resolve(cachedOpenid)
      return
    }

    // 获取 code
    wx.login({
      success: (res) => {
        if (res.code) {
          // 调用服务端接口换取 openid
          // 注意：这里需要你的服务端提供一个 /api/auth/login 接口
          // 或者直接使用微信云开发
          wx.request({
            url: `${API_BASE_URL}/auth/login`,
            method: 'POST',
            data: {
              code: res.code
            },
            success: (result) => {
              if (result.data.errcode === 0) {
                const openid = result.data.data.openid
                wx.setStorageSync('user_openid', openid)
                resolve(openid)
              } else {
                reject(new Error('获取 openid 失败'))
              }
            },
            fail: reject
          })
        } else {
          reject(new Error('获取 code 失败'))
        }
      },
      fail: reject
    })
  })
}

/**
 * 创建提醒
 */
function createReminder(reminderData) {
  return new Promise(async (resolve, reject) => {
    try {
      const openid = await getUserOpenid()
      
      wx.request({
        url: `${API_BASE_URL}/reminder`,
        method: 'POST',
        data: {
          openid: openid,
          title: reminderData.title, // 保留 title 字段用于兼容
          thing1: reminderData.thing1 || reminderData.title, // 事项主题
          thing4: reminderData.thing4 || '', // 事项描述
          time: reminderData.time, // 事项时间
          reminderTime: reminderData.reminderTime,
          enableSubscribe: reminderData.enableSubscribe
        },
        success: (res) => {
          if (res.data.errcode === 0) {
            resolve(res.data)
          } else {
            reject(new Error(res.data.errmsg || '创建提醒失败'))
          }
        },
        fail: (err) => {
          reject(err)
        }
      })
    } catch (error) {
      reject(error)
    }
  })
}

/**
 * 获取提醒列表
 */
function getReminders() {
  return new Promise(async (resolve, reject) => {
    try {
      const openid = await getUserOpenid()
      
      // GET 请求需要将参数放在 URL 中
      const url = `${API_BASE_URL}/reminders?openid=${encodeURIComponent(openid)}`
      
      wx.request({
        url: url,
        method: 'GET',
        header: {
          'Content-Type': 'application/json'
        },
        success: (res) => {
          if (res.statusCode === 200) {
            if (res.data.errcode === 0) {
              resolve(res.data.data || [])
            } else {
              reject(new Error(res.data.errmsg || '获取提醒列表失败'))
            }
          } else {
            reject(new Error(`请求失败: ${res.statusCode}`))
          }
        },
        fail: (err) => {
          console.error('请求失败:', err)
          reject(new Error(err.errMsg || '网络请求失败'))
        }
      })
    } catch (error) {
      reject(error)
    }
  })
}

/**
 * 删除提醒
 */
function deleteReminder(reminderId) {
  return new Promise((resolve, reject) => {
    wx.request({
      url: `${API_BASE_URL}/reminder/${reminderId}`,
      method: 'DELETE',
      success: (res) => {
        if (res.data.errcode === 0) {
          resolve(res.data)
        } else {
          reject(new Error(res.data.errmsg || '删除提醒失败'))
        }
      },
      fail: reject
    })
  })
}

/**
 * 获取提醒详情
 */
function getReminder(reminderId) {
  return new Promise((resolve, reject) => {
    wx.request({
      url: `${API_BASE_URL}/reminder/${reminderId}`,
      method: 'GET',
      success: (res) => {
        if (res.data.errcode === 0) {
          resolve(res.data.data)
        } else {
          reject(new Error(res.data.errmsg || '获取提醒详情失败'))
        }
      },
      fail: reject
    })
  })
}

/**
 * 更新提醒
 */
function updateReminder(reminderId, reminderData) {
  return new Promise((resolve, reject) => {
    wx.request({
      url: `${API_BASE_URL}/reminder/${reminderId}`,
      method: 'PUT',
      header: {
        'Content-Type': 'application/json'
      },
      data: {
        thing1: reminderData.thing1 || reminderData.title,
        thing4: reminderData.thing4 || '',
        time: reminderData.time || '',
        reminderTime: reminderData.reminderTime,
        enableSubscribe: reminderData.enableSubscribe || false
      },
      success: (res) => {
        if (res.data.errcode === 0) {
          resolve(res.data)
        } else {
          reject(new Error(res.data.errmsg || '更新提醒失败'))
        }
      },
      fail: reject
    })
  })
}

/**
 * 更新提醒完成状态
 */
function updateReminderComplete(reminderId, completed) {
  return new Promise((resolve, reject) => {
    wx.request({
      url: `${API_BASE_URL}/reminder/${reminderId}/complete`,
      method: 'PUT',
      data: {
        completed: completed
      },
      success: (res) => {
        if (res.data.errcode === 0) {
          resolve(res.data)
        } else {
          reject(new Error(res.data.errmsg || '更新提醒状态失败'))
        }
      },
      fail: reject
    })
  })
}

/**
 * 分享提醒
 */
function shareReminder(reminderId, ownerOpenid) {
  return new Promise((resolve, reject) => {
    wx.request({
      url: `${API_BASE_URL}/reminder/${reminderId}/share`,
      method: 'POST',
      data: {
        owner_openid: ownerOpenid
      },
      success: (res) => {
        if (res.data.errcode === 0) {
          resolve(res.data.data)
        } else {
          reject(new Error(res.data.errmsg || '分享失败'))
        }
      },
      fail: reject
    })
  })
}

/**
 * 接受分享的提醒
 */
function acceptReminder(reminderId, assignedOpenid) {
  return new Promise((resolve, reject) => {
    wx.request({
      url: `${API_BASE_URL}/reminder/${reminderId}/accept`,
      method: 'POST',
      data: {
        assigned_openid: assignedOpenid
      },
      success: (res) => {
        // 处理400错误（重复接受）
        if (res.statusCode === 400 && res.data.errcode === 400) {
          // 返回数据中包含alreadyAccepted标记
          resolve(res.data.data || { alreadyAccepted: true, message: res.data.errmsg })
          return
        }
        
        if (res.data.errcode === 0) {
          resolve(res.data.data)
        } else {
          reject(new Error(res.data.errmsg || '接受失败'))
        }
      },
      fail: (err) => {
        // 处理HTTP错误
        if (err.statusCode === 400) {
          // 尝试解析错误信息
          try {
            const errorData = JSON.parse(err.data || '{}')
            resolve({ alreadyAccepted: true, message: errorData.errmsg || '已经接受过此提醒' })
          } catch {
            reject(new Error('已经接受过此提醒'))
          }
        } else {
          reject(err)
        }
      }
    })
  })
}

/**
 * 获取分配给自己的提醒
 */
function getAssignedReminders(openid) {
  return new Promise((resolve, reject) => {
    wx.request({
      url: `${API_BASE_URL}/reminders/assigned`,
      method: 'GET',
      data: {
        openid: openid
      },
      success: (res) => {
        if (res.data.errcode === 0) {
          resolve(res.data.data || [])
        } else {
          reject(new Error(res.data.errmsg || '获取失败'))
        }
      },
      fail: reject
    })
  })
}

module.exports = {
  // IP 配置相关函数
  getLocalIP,
  setDevServerIP,
  clearDevServerIP,
  detectDevServerIP,  // 自动检测开发服务器 IP
  // API 基础地址（只读，用于调试）
  get API_BASE_URL() {
    return API_BASE_URL
  },
  API_BASE_URL,
  getUserOpenid,
  createReminder,
  getReminders,
  getReminder,
  updateReminder,
  deleteReminder,
  updateReminderComplete,
  shareReminder,
  acceptReminder,
  getAssignedReminders
}

