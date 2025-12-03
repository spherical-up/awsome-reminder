# 订阅消息模板字段配置

## 错误说明

如果遇到错误：
```
errcode: 47003
errmsg: argument invalid! data.thing3.value is empty
```

说明模板需要 `thing3` 字段，但代码中没有提供。

## 当前模板字段

根据模板配置，当前模板需要以下字段：
- `thing1` - 事项主题
- `time2` - 事项时间
- `thing4` - 事项描述

## 查看模板字段

### 方法 1：在微信公众平台查看

1. 登录 [微信公众平台](https://mp.weixin.qq.com/)
2. 进入 **功能** -> **订阅消息**
3. 找到你的模板（模板ID: `is4mEq0nlt5fJRn-Pflnr-wJxoCKOz9qty857QmH7Bw`）
4. 查看模板详情，确认需要哪些字段

### 方法 2：查看模板示例

当前模板格式：
```
事项主题：{{thing1.DATA}}
事项时间：{{time2.DATA}}
事项描述：{{thing4.DATA}}
```

## 配置模板字段

### 当前代码配置

在 `server/app.py` 中，模板数据构建如下：

```python
template_data = {
    'thing1': {'value': reminder['title'][:20]},  # 事项主题
    'time2': {'value': reminder.get('time', '')},  # 事项时间
    'thing4': {'value': reminder['title'][:20]}  # 事项描述
}
```

### 根据模板调整

如果你的模板字段不同，需要修改 `template_data`：

**示例 1：如果 thing3 是备注**
```python
template_data = {
    'thing1': {'value': reminder['title'][:20]},
    'time2': {'value': reminder.get('time', '')},
    'thing3': {'value': '来自松鼠小记'}  # 备注信息
}
```

**示例 2：如果 thing3 是其他内容**
```python
template_data = {
    'thing1': {'value': reminder['title'][:20]},
    'time2': {'value': reminder.get('time', '')},
    'thing3': {'value': reminder.get('note', '')[:20]}  # 从提醒数据中获取
}
```

## 字段类型说明

微信订阅消息支持的字段类型：

| 字段类型 | 说明 | 长度限制 |
|---------|------|---------|
| `thing` | 事物 | 最多 20 字 |
| `time` | 时间 | 格式：YYYY年MM月DD日 HH:mm |
| `date` | 日期 | 格式：YYYY年MM月DD日 |
| `number` | 数字 | 最多 8 位 |
| `letter` | 字母 | 最多 8 位 |
| `name` | 姓名 | 最多 10 字 |
| `phrase` | 短语 | 最多 5 字 |

## 常见字段配置

### 提醒类模板

```python
template_data = {
    'thing1': {'value': '事项主题'[:20]},  # 事项主题
    'time2': {'value': '2024-12-03 10:00:00'},  # 事项时间
    'thing4': {'value': '事项描述'[:20]}  # 事项描述
}
```

### 通知类模板

```python
template_data = {
    'thing1': {'value': '通知标题'[:20]},
    'thing2': {'value': '通知内容'[:20]},
    'time3': {'value': '2024-12-03 10:00:00'}
}
```

## 修改配置

### 步骤 1：查看模板字段

在微信公众平台查看你的模板需要哪些字段。

### 步骤 2：修改代码

编辑 `server/app.py`，找到 `template_data` 的构建部分（两处）：
1. `schedule_reminder` 函数中的 `send_reminder` 函数内（约第 172 行）
2. `manual_send_reminder` 函数内（约第 492 行）

当前已配置为：
- `thing1`: 事项主题（提醒标题）
- `time2`: 事项时间（提醒时间）
- `thing4`: 事项描述（提醒标题）

### 步骤 3：重启服务

```bash
cd server
docker-compose restart reminder-server
```

### 步骤 4：测试

创建提醒并等待发送，或使用手动发送接口测试：

```bash
curl -X POST http://192.168.31.100:5000/api/debug/reminder/{reminder_id}/send
```

## 调试技巧

### 1. 查看模板数据

在日志中查看发送的模板数据：
```bash
docker logs reminder-server -f | grep "模板数据"
```

### 2. 查看错误信息

如果发送失败，查看详细错误：
```bash
docker logs reminder-server -f | grep "发送订阅消息失败"
```

### 3. 手动测试

使用调试接口手动发送，查看具体错误：
```bash
curl -X POST http://192.168.31.100:5000/api/debug/reminder/{reminder_id}/send
```

## 注意事项

1. **字段名称必须匹配**：模板中的字段名（如 `thing1`）必须与代码中的键名一致
2. **字段值不能为空**：所有必需字段都必须有值
3. **长度限制**：注意字段的长度限制（如 `thing` 类型最多 20 字）
4. **格式要求**：时间字段需要符合指定格式

## 如果还有问题

1. 确认模板ID是否正确
2. 查看模板详情，确认所有必需字段
3. 检查字段值是否符合格式要求
4. 查看服务日志获取详细错误信息

