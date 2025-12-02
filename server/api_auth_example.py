"""
服务端认证接口示例
用于通过 code 换取 openid
"""
from flask import Flask, request, jsonify
import requests
import os

app = Flask(__name__)

APPID = os.getenv('WX_APPID', 'your-appid')
APPSECRET = os.getenv('WX_APPSECRET', 'your-appsecret')


@app.route('/api/auth/login', methods=['POST'])
def login():
    """
    通过 code 换取 openid
    
    请求体:
    {
        "code": "微信登录code"
    }
    """
    try:
        data = request.json
        code = data.get('code')
        
        if not code:
            return jsonify({
                'errcode': 400,
                'errmsg': '缺少 code 参数'
            }), 400
        
        # 调用微信接口换取 openid
        url = f'https://api.weixin.qq.com/sns/jscode2session'
        params = {
            'appid': APPID,
            'secret': APPSECRET,
            'js_code': code,
            'grant_type': 'authorization_code'
        }
        
        response = requests.get(url, params=params, timeout=10)
        result = response.json()
        
        if 'openid' in result:
            return jsonify({
                'errcode': 0,
                'errmsg': 'success',
                'data': {
                    'openid': result['openid'],
                    'session_key': result.get('session_key')
                }
            })
        else:
            return jsonify({
                'errcode': result.get('errcode', -1),
                'errmsg': result.get('errmsg', '换取 openid 失败')
            }), 400
            
    except Exception as e:
        return jsonify({
            'errcode': 500,
            'errmsg': str(e)
        }), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

