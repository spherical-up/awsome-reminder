// utils/api.js
// API 请求工具类

// 配置服务端地址（开发环境）
// 注意：微信开发者工具不支持 localhost，需要使用本地 IP
// 获取本地 IP: ifconfig | grep "inet " | grep -v 127.0.0.1
// const API_BASE_URL = 'http://10.0.1.130:5001/api'

// 生产环境配置
const API_BASE_URL = 'https://www.6ht6.com/api'

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

