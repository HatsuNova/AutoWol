#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AutoWOL - Wake-on-LAN Web Interface (Security Enhanced)
Flask应用，用于检测服务器状态并发送WOL唤醒包
支持登录认证、Session管理、防暴力破解
"""

from flask import Flask, render_template, jsonify, request, session, redirect, url_for, flash
import socket
import subprocess
import platform
import time
from datetime import timedelta
from functools import wraps
from config import (
    TARGET_IP, TARGET_MAC, TARGET_PORT, FLASK_HOST, FLASK_PORT,
    SECRET_KEY, USERNAME, PASSWORD, SESSION_TIMEOUT,
    MAX_LOGIN_ATTEMPTS, LOGIN_BLOCK_TIME
)

app = Flask(__name__)
app.secret_key = SECRET_KEY
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(seconds=SESSION_TIMEOUT)

# 登录失败记录 {ip: {'count': 失败次数, 'blocked_until': 解锁时间}}
login_attempts = {}


def login_required(f):
    """登录验证装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


def get_client_ip():
    """获取客户端真实IP（支持反向代理/frp）"""
    # 优先从 X-Forwarded-For 获取（frp 会设置此头）
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0].strip()
    elif request.headers.get('X-Real-IP'):
        return request.headers.get('X-Real-IP')
    return request.remote_addr


def is_ip_blocked(ip):
    """检查IP是否被锁定"""
    if ip in login_attempts:
        blocked_until = login_attempts[ip].get('blocked_until', 0)
        if time.time() < blocked_until:
            return True, int(blocked_until - time.time())
        # 解锁后重置计数
        if time.time() >= blocked_until:
            login_attempts[ip] = {'count': 0, 'blocked_until': 0}
    return False, 0


def record_login_attempt(ip, success):
    """记录登录尝试"""
    if ip not in login_attempts:
        login_attempts[ip] = {'count': 0, 'blocked_until': 0}
    
    if success:
        # 登录成功，清零计数
        login_attempts[ip] = {'count': 0, 'blocked_until': 0}
    else:
        # 登录失败，增加计数
        login_attempts[ip]['count'] += 1
        if login_attempts[ip]['count'] >= MAX_LOGIN_ATTEMPTS:
            # 超过最大尝试次数，锁定IP
            login_attempts[ip]['blocked_until'] = time.time() + LOGIN_BLOCK_TIME
            print(f"⚠️  IP {ip} 已被锁定 {LOGIN_BLOCK_TIME} 秒（失败 {login_attempts[ip]['count']} 次）")


def check_host_status(ip, port=22, timeout=2):
    """
    检测目标主机是否在线
    先尝试 ping，失败则尝试 TCP 端口连接
    
    Args:
        ip: 目标IP地址
        port: 检测端口（默认SSH 22端口）
        timeout: 超时时间（秒）
    
    Returns:
        bool: True表示在线，False表示离线
    """
    try:
        # 先尝试ping
        param = '-c' if platform.system().lower() != 'windows' else '-n'
        command = ['ping', param, '1', '-W', '1', ip]
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=3)
        
        if result.returncode == 0:
            return True
        
        # 如果ping失败，尝试端口连接
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((ip, port))
        sock.close()
        return result == 0
    except Exception as e:
        print(f"检测主机状态时出错: {e}")
        return False


def send_wol_packet(mac_address, broadcast_ip='192.168.1.255', port=9):
    """
    发送Wake-on-LAN魔术包
    
    Args:
        mac_address: 目标MAC地址，格式如 'AA:BB:CC:DD:EE:FF' 或 'AA-BB-CC-DD-EE-FF'
        broadcast_ip: 广播地址（默认192.168.1.255）
        port: WOL端口，通常为7或9
    
    Returns:
        bool: 成功返回True，失败返回False
    """
    try:
        # 规范化MAC地址格式，移除分隔符
        mac_address = mac_address.replace(':', '').replace('-', '').upper()
        
        # 验证MAC地址
        if len(mac_address) != 12:
            raise ValueError("MAC地址格式错误")
        
        # 将MAC地址转换为字节
        mac_bytes = bytes.fromhex(mac_address)
        
        # 构造魔术包: 6字节的0xFF + 16次重复的MAC地址
        magic_packet = b'\xFF' * 6 + mac_bytes * 16
        
        # 创建UDP socket并发送
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        
        # 发送到指定广播地址（端口9和7都试一下，提高成功率）
        for target_port in [9, 7]:
            try:
                sock.sendto(magic_packet, (broadcast_ip, target_port))
                print(f"   📡 已发送到 {broadcast_ip}:{target_port}")
            except Exception as port_err:
                print(f"   ⚠️  端口 {target_port} 发送失败: {port_err}")
        
        # 同时发送到全局广播地址作为备用
        try:
            sock.sendto(magic_packet, ('255.255.255.255', 9))
            print(f"   📡 已发送到 255.255.255.255:9 (备用)")
        except:
            pass
        
        sock.close()
        
        print(f"✅ WOL魔术包已发送到 {mac_address} (广播地址: {broadcast_ip})")
        return True
    except Exception as e:
        print(f"❌ 发送WOL包时出错: {e}")
        return False


# ==================== 路由定义 ====================

@app.route('/login', methods=['GET', 'POST'])
def login():
    """登录页面"""
    if session.get('logged_in'):
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        client_ip = get_client_ip()
        
        # 检查IP是否被锁定
        blocked, remaining_time = is_ip_blocked(client_ip)
        if blocked:
            flash(f'⚠️ 登录失败次数过多，请在 {remaining_time} 秒后重试', 'error')
            time.sleep(2)  # 防止暴力破解
            return render_template('login.html')
        
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        # 添加延迟，防止暴力破解
        time.sleep(1)
        
        if username == USERNAME and password == PASSWORD:
            session.permanent = True
            session['logged_in'] = True
            session['username'] = username
            session['login_time'] = time.time()
            record_login_attempt(client_ip, success=True)
            print(f"✅ 用户 {username} 从 {client_ip} 登录成功")
            flash('登录成功！', 'success')
            return redirect(url_for('index'))
        else:
            record_login_attempt(client_ip, success=False)
            attempts_left = MAX_LOGIN_ATTEMPTS - login_attempts[client_ip]['count']
            print(f"❌ 登录失败：{client_ip} (剩余 {attempts_left} 次机会)")
            if attempts_left > 0:
                flash(f'❌ 用户名或密码错误，还剩 {attempts_left} 次尝试机会', 'error')
            else:
                flash(f'⚠️ 登录失败次数过多，已锁定 {LOGIN_BLOCK_TIME} 秒', 'error')
            return render_template('login.html')
    
    return render_template('login.html')


@app.route('/logout')
def logout():
    """退出登录"""
    username = session.get('username', 'Unknown')
    print(f"👋 用户 {username} 退出登录")
    session.clear()
    flash('已退出登录', 'success')
    return redirect(url_for('login'))


@app.route('/')
@login_required
def index():
    """主页"""
    return render_template('index.html', 
                         target_ip=TARGET_IP, 
                         target_mac=TARGET_MAC, 
                         username=session.get('username'))


@app.route('/api/status')
@login_required
def get_status():
    """
    API: 获取目标服务器状态
    
    Returns:
        JSON: {status: 'online'/'offline', ip: '192.168.1.105', mac: 'XX:XX:XX:XX:XX:XX'}
    """
    is_online = check_host_status(TARGET_IP, TARGET_PORT)
    return jsonify({
        'status': 'online' if is_online else 'offline',
        'ip': TARGET_IP,
        'mac': TARGET_MAC
    })


@app.route('/api/wake', methods=['POST'])
@login_required
def wake_server():
    """
    API: 发送WOL唤醒包
    
    Returns:
        JSON: {success: true/false, message: '...'}
    """
    try:
        client_ip = get_client_ip()
        username = session.get('username', 'Unknown')
        print(f"🚀 用户 {username} ({client_ip}) 请求唤醒服务器 {TARGET_MAC}")
        
        success = send_wol_packet(TARGET_MAC)
        if success:
            return jsonify({
                'success': True,
                'message': f'WOL唤醒包已发送到 {TARGET_MAC}'
            })
        else:
            return jsonify({
                'success': False,
                'message': '发送WOL包失败'
            }), 500
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'错误: {str(e)}'
        }), 500


if __name__ == '__main__':
    print("=" * 60)
    print("🚀 AutoWOL 服务启动中...")
    print(f"📡 目标服务器: {TARGET_IP} ({TARGET_MAC})")
    print(f"🔐 登录用户名: {USERNAME}")
    print(f"⏱️  Session 超时: {SESSION_TIMEOUT} 秒")
    print(f"🛡️  最大登录尝试: {MAX_LOGIN_ATTEMPTS} 次")
    print(f"🌐 访问地址: http://{FLASK_HOST}:{FLASK_PORT}")
    print("⚠️  注意：公网访问前请修改 config.py 中的密码和密钥！")
    print("=" * 60)
    
    # 生产环境建议使用 gunicorn 或 uwsgi，不要使用 debug=True
    app.run(host=FLASK_HOST, port=FLASK_PORT, debug=False)
