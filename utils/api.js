// utils/api.js
// API 请求工具类

// 配置服务端地址（开发环境）
// 注意：微信开发者工具不支持 localhost，需要使用本地 IP
// 获取本地 IP: ifconfig | grep "inet " | grep -v 127.0.0.1
// const API_BASE_URL = 'http://192.168.31.100:5000/api'
// 如果本地 IP 不行，可以尝试 127.0.0.1（但通常不行）
// const API_BASE_URL = 'http://127.0.0.1:5000/api'

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
          title: reminderData.title,
          time: reminderData.time,
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
      
      wx.request({
        url: `${API_BASE_URL}/reminders`,
        method: 'GET',
        data: {
          openid: openid
        },
        success: (res) => {
          if (res.data.errcode === 0) {
            resolve(res.data.data || [])
          } else {
            reject(new Error(res.data.errmsg || '获取提醒列表失败'))
          }
        },
        fail: reject
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

module.exports = {
  API_BASE_URL,
  getUserOpenid,
  createReminder,
  getReminders,
  deleteReminder
}

