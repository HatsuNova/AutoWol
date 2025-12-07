# AutoWOL - 服务器远程唤醒系统

基于 Flask 的 Wake-on-LAN (WOL) Web 应用，专为软路由（OpenWrt/ImmortalWrt）设计，可通过 Web 界面检测服务器状态并远程唤醒。

## 功能特性

- ✅ **服务器状态检测** - 实时检测目标服务器是否在线（支持 ping + TCP 端口双重检测）
- ✅ **一键远程唤醒** - 通过 WOL 魔术包远程唤醒服务器
- ✅ **登录认证** - 用户名密码保护，支持 Session 管理
- ✅ **防暴力破解** - 登录失败次数限制和 IP 锁定机制
- ✅ **现代化界面** - 响应式设计，支持移动端访问
- ✅ **自动刷新** - 每 10 秒自动检测服务器状态

## 系统要求

- **系统**: OpenWrt / ImmortalWrt 或其他 Linux 系统
- **Python**: 3.6+
- **内存**: 最小 64MB 可用内存
- **网络**: 与目标服务器在同一局域网

## 快速开始

### 1. 安装依赖

```bash
# 进入项目目录
cd AutoWol

# 安装 Python 依赖
pip3 install -r requirements.txt
```

### 2. 配置

```bash
# 复制配置文件模板
cp config.py.example config.py

# 编辑配置文件
nano config.py
```

**必须修改的配置项：**

```python
# 目标服务器配置
TARGET_IP = '192.168.1.105'          # 目标服务器的 IP 地址
TARGET_MAC = 'AA:BB:CC:DD:EE:FF'     # 目标服务器的 MAC 地址
TARGET_PORT = 22                     # 检测端口（SSH: 22, RDP: 3389, SMB: 445）

# Web 服务配置
FLASK_PORT = 5001                    # Web 服务端口

# 安全配置
SECRET_KEY = 'your-random-key'       # ⚠️ 修改为随机字符串
USERNAME = 'admin'                   # 登录用户名
PASSWORD = 'strong-password'         # ⚠️ 修改为强密码
```

**如何获取 MAC 地址？**

在目标服务器上执行：
- Windows: `ipconfig /all` 查看"物理地址"
- Linux: `ip link` 或 `ifconfig` 查看 MAC 地址

### 3. 启动服务

```bash
# 方式 1: 直接运行
python3 app.py

# 方式 2: 使用启动脚本
./autowol.sh start
```

### 4. 访问

打开浏览器访问：`http://软路由IP:5001`

例如：`http://192.168.1.1:5001/login`

## 服务管理

### autowol.sh 脚本用法

```bash
# 启动服务
./autowol.sh start

# 停止服务
./autowol.sh stop

# 重启服务（修改代码后使用）
./autowol.sh restart

# 查看状态
./autowol.sh status
```

### 查看日志

```bash
# 实时查看日志
tail -f /var/log/autowol.log

# 查看最近 100 行
tail -100 /var/log/autowol.log
```

## 开机自启动

### 使用 rc.local（推荐）

```bash
# 编辑 rc.local
vi /etc/rc.local

# 在 exit 0 之前添加：
/root/code/AutoWol/autowol.sh start

# 保存后添加执行权限
chmod +x /etc/rc.local
```

### 测试自启动

```bash
# 手动执行 rc.local 测试
/etc/rc.local

# 检查服务是否启动
/root/code/AutoWol/autowol.sh status
```

## 目标服务器配置

### Windows 系统启用 WOL

**1. BIOS 设置**
- 进入 BIOS/UEFI 设置
- 启用 "Wake on LAN" 或 "Power On By PCI-E"

**2. 网卡设置**
- 打开"设备管理器" → 网络适配器
- 右键网卡 → 属性 → 电源管理
- ✅ 勾选"允许此设备唤醒计算机"
- ✅ 勾选"只允许幻数据包唤醒计算机"
- 高级选项卡 → "Wake on Magic Packet" 设为 Enabled

**3. 关闭快速启动**
- 控制面板 → 电源选项 → 选择电源按钮的功能
- ❌ 取消勾选"启用快速启动"

**4. 使用"关机"而非"睡眠"**
- WOL 仅在完全关机状态下有效

### Linux 系统启用 WOL

```bash
# 检查网卡是否支持 WOL
ethtool eth0 | grep Wake-on

# 启用 WOL
sudo ethtool -s eth0 wol g

# 持久化配置（添加到 /etc/rc.local）
echo "ethtool -s eth0 wol g" >> /etc/rc.local
```

## 状态检测端口说明

系统通过以下方式检测服务器状态：

1. **ICMP Ping** - 优先使用 ping 检测
2. **TCP 端口连接** - ping 失败时尝试连接指定端口

**常用检测端口：**
- `22` - SSH（Linux/开启 SSH 的 Windows）
- `3389` - RDP（Windows 远程桌面）
- `445` - SMB（Windows 文件共享）
- `80/443` - HTTP/HTTPS（Web 服务器）

**修改检测端口：**

在 `config.py` 中修改 `TARGET_PORT`：

```python
TARGET_PORT = 22    # 改为你服务器开启的端口
```

## 安全建议

### ⚠️ 重要安全配置

1. **修改默认密码** - 使用强密码（至少 12 位，包含大小写、数字、特殊字符）
2. **修改 SECRET_KEY** - 使用随机字符串
3. **限制访问** - 仅在内网使用，或配置防火墙规则
4. **定期更新** - 定期更换密码

### 生成随机密钥

```bash
# 生成 SECRET_KEY
python3 -c "import secrets; print(secrets.token_hex(32))"
```

## 故障排查

### 服务无法启动

```bash
# 检查端口是否被占用
netstat -tuln | grep 5001

# 检查 Python 版本
python3 --version

# 检查依赖是否安装
pip3 list | grep Flask
```

### 无法唤醒服务器

1. 确认目标服务器已启用 WOL（BIOS + 网卡设置）
2. 确认 MAC 地址正确（不要输入 IP 地址）
3. 确认服务器是"关机"状态（不是睡眠/休眠）
4. 确认网线已连接（WiFi 通常不支持 WOL）
5. 检查日志：`tail -f /var/log/autowol.log`

### 状态检测不准确

1. 确认 `TARGET_PORT` 配置正确
2. 确认目标端口已开放（防火墙）
3. 尝试修改为其他端口：

```python
# config.py
TARGET_PORT = 3389  # 尝试 RDP 端口
```

## 目录结构

```
AutoWol/
├── app.py                  # 主程序
├── config.py.example       # 配置文件模板
├── autowol.sh              # 服务管理脚本
├── requirements.txt        # Python 依赖
├── templates/
│   ├── index.html          # 主页面
│   └── login.html          # 登录页面
└── README.md               # 本文件
```

## 技术栈

- **后端**: Flask (Python)
- **前端**: HTML5 + CSS3 + JavaScript
- **协议**: Wake-on-LAN (Magic Packet)
- **认证**: Flask Session + 防暴力破解

## 贡献

欢迎提交 Issue 和 Pull Request！

---

**问题反馈**: 如有问题，请检查配置文件和服务器端 WOL 设置。
