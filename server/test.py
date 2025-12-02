"""
服务端接口测试脚本
用于快速测试各个接口是否正常工作
"""
import requests
import json
from datetime import datetime, timedelta

BASE_URL = 'http://localhost:5000/api'

def test_health():
    """测试健康检查接口"""
    print("=" * 50)
    print("1. 测试健康检查接口")
    print("=" * 50)
    try:
        r = requests.get(f'{BASE_URL}/health', timeout=5)
        result = r.json()
        print(f"状态码: {r.status_code}")
        print(f"响应: {json.dumps(result, indent=2, ensure_ascii=False)}")
        if result.get('errcode') == 0:
            print("✅ 健康检查通过")
            return True
        else:
            print("❌ 健康检查失败")
            return False
    except Exception as e:
        print(f"❌ 请求失败: {str(e)}")
        return False


def test_login(code='test_code'):
    """测试用户登录接口"""
    print("\n" + "=" * 50)
    print("2. 测试用户登录接口（需要真实的 code）")
    print("=" * 50)
    try:
        data = {'code': code}
        r = requests.post(f'{BASE_URL}/auth/login', json=data, timeout=10)
        result = r.json()
        print(f"状态码: {r.status_code}")
        print(f"响应: {json.dumps(result, indent=2, ensure_ascii=False)}")
        if result.get('errcode') == 0:
            openid = result.get('data', {}).get('openid')
            print(f"✅ 登录成功，openid: {openid}")
            return openid
        else:
            print(f"❌ 登录失败: {result.get('errmsg')}")
            print("提示: 需要使用真实的 code，可以从小程序端获取")
            return None
    except Exception as e:
        print(f"❌ 请求失败: {str(e)}")
        return None


def test_create_reminder(openid='test_openid_123'):
    """测试创建提醒接口"""
    print("\n" + "=" * 50)
    print("3. 测试创建提醒接口")
    print("=" * 50)
    try:
        # 创建5分钟后的提醒
        reminder_time = int((datetime.now() + timedelta(minutes=5)).timestamp() * 1000)
        reminder_time_str = (datetime.now() + timedelta(minutes=5)).strftime('%Y-%m-%d %H:%M:%S')
        
        data = {
            'openid': openid,
            'title': '测试提醒 - 这是一个测试提醒内容',
            'time': f'5分钟后 ({reminder_time_str})',
            'reminderTime': reminder_time,
            'enableSubscribe': True
        }
        
        print(f"请求数据: {json.dumps(data, indent=2, ensure_ascii=False)}")
        
        r = requests.post(f'{BASE_URL}/reminder', json=data, timeout=10)
        result = r.json()
        print(f"状态码: {r.status_code}")
        print(f"响应: {json.dumps(result, indent=2, ensure_ascii=False)}")
        
        if result.get('errcode') == 0:
            reminder_id = result.get('data', {}).get('id')
            print(f"✅ 创建提醒成功，ID: {reminder_id}")
            return reminder_id
        else:
            print(f"❌ 创建提醒失败: {result.get('errmsg')}")
            return None
    except Exception as e:
        print(f"❌ 请求失败: {str(e)}")
        return None


def test_get_reminders(openid='test_openid_123'):
    """测试获取提醒列表接口"""
    print("\n" + "=" * 50)
    print("4. 测试获取提醒列表接口")
    print("=" * 50)
    try:
        params = {'openid': openid}
        r = requests.get(f'{BASE_URL}/reminders', params=params, timeout=10)
        result = r.json()
        print(f"状态码: {r.status_code}")
        print(f"响应: {json.dumps(result, indent=2, ensure_ascii=False)}")
        
        if result.get('errcode') == 0:
            reminders = result.get('data', [])
            print(f"✅ 获取成功，共 {len(reminders)} 条提醒")
            return reminders
        else:
            print(f"❌ 获取失败: {result.get('errmsg')}")
            return []
    except Exception as e:
        print(f"❌ 请求失败: {str(e)}")
        return []


def test_delete_reminder(reminder_id):
    """测试删除提醒接口"""
    print("\n" + "=" * 50)
    print("5. 测试删除提醒接口")
    print("=" * 50)
    try:
        r = requests.delete(f'{BASE_URL}/reminder/{reminder_id}', timeout=10)
        result = r.json()
        print(f"状态码: {r.status_code}")
        print(f"响应: {json.dumps(result, indent=2, ensure_ascii=False)}")
        
        if result.get('errcode') == 0:
            print(f"✅ 删除提醒成功")
            return True
        else:
            print(f"❌ 删除提醒失败: {result.get('errmsg')}")
            return False
    except Exception as e:
        print(f"❌ 请求失败: {str(e)}")
        return False


def main():
    """主测试函数"""
    print("\n" + "=" * 50)
    print("微信小程序订阅消息服务端 - 接口测试")
    print("=" * 50)
    print(f"服务端地址: {BASE_URL}")
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 1. 健康检查
    if not test_health():
        print("\n❌ 服务端未启动或无法访问，请先启动服务端：python app.py")
        return
    
    # 2. 用户登录（可选，需要真实 code）
    # openid = test_login()
    # if not openid:
    #     openid = 'test_openid_123'  # 使用测试 openid
    openid = 'test_openid_123'
    
    # 3. 创建提醒
    reminder_id = test_create_reminder(openid)
    
    # 4. 获取提醒列表
    reminders = test_get_reminders(openid)
    
    # 5. 删除提醒（可选）
    if reminder_id:
        # test_delete_reminder(reminder_id)
        pass
    
    print("\n" + "=" * 50)
    print("测试完成")
    print("=" * 50)
    print("\n提示:")
    print("1. 如果登录接口失败，这是正常的，需要使用真实的 code")
    print("2. 创建的提醒会在指定时间自动发送订阅消息")
    print("3. 查看服务端日志可以了解详细执行情况")


if __name__ == '__main__':
    main()

