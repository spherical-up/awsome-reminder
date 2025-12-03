// utils/subscribeMessage.js
// 订阅消息工具类

/**
 * 请求订阅消息
 * @param {Array} tmplIds 订阅消息模板ID数组
 * @returns {Promise} 返回订阅结果
 */
function requestSubscribeMessage(tmplIds) {
  return new Promise((resolve, reject) => {
    wx.requestSubscribeMessage({
      tmplIds: tmplIds,
      success(res) {
        console.log('订阅消息请求成功', res)
        // res 是一个对象，key 为模板ID，value 为 'accept' | 'reject' | 'ban'
        resolve(res)
      },
      fail(err) {
        console.error('订阅消息请求失败', err)
        reject(err)
      },
      complete() {
        // 无论成功失败都会执行
      }
    })
  })
}

/**
 * 检查订阅消息授权状态
 * @param {String} tmplId 模板ID
 * @returns {Promise} 返回授权状态
 */
function checkSubscribeMessageStatus(tmplId) {
  return new Promise((resolve, reject) => {
    wx.getSetting({
      withSubscriptions: true,
      success(res) {
        const subscriptionsSetting = res.subscriptionsSetting
        if (subscriptionsSetting) {
          const itemSettings = subscriptionsSetting.itemSettings || {}
          const status = itemSettings[tmplId]
          resolve(status) // 'accept' | 'reject' | 'ban'
        } else {
          resolve(null)
        }
      },
      fail(err) {
        reject(err)
      }
    })
  })
}

module.exports = {
  requestSubscribeMessage,
  checkSubscribeMessageStatus
}

