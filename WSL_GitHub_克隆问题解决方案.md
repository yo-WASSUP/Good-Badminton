# WSL 中通过 Clash 代理克隆 GitHub 仓库 - 完整指南

## 问题现象

在 WSL (Windows Subsystem for Linux) 中克隆 GitHub 仓库时，速度极慢或超时失败。

```bash
git clone git@github.com:AlonZhao/Good-Badminton.git
# 结果：超时或速度极慢（几 KB/s）
```

---

## 问题原因分析

### 1. 网络连接问题
- GitHub 服务器在国内访问不稳定
- 延迟高（120+ ms）且丢包率高（30%+）
- 直连速度无法满足正常克隆需求

### 2. WSL 网络架构特殊性
- WSL 是独立的网络命名空间
- WSL 访问 Windows 主机需要使用**特定的 IP 地址**
- 常见错误：使用 `127.0.0.1` 或错误的 IP 地址

### 3. 正确的 Windows 主机 IP 地址
- ❌ 错误：`127.0.0.1`（WSL 的本地回环）
- ❌ 错误：`10.255.255.254`（DNS 服务器地址，不是主机地址）
- ✅ 正确：**WSL 的默认网关地址**（例如 `172.29.64.1`）

---

## 完整解决步骤

### 步骤 1: 在 Windows 中配置 Clash

#### 1.1 启用 Allow LAN（允许局域网连接）
1. 打开 **Clash for Windows**
2. 点击左侧 **General（常规）**
3. 找到 **Allow LAN** 选项并**开启**
4. 记录端口号（通常是 **7890**）

> ⚠️ **重要**：不开启此选项，WSL 无法连接到 Clash

#### 1.2 配置 Windows 防火墙
在 **PowerShell（管理员）** 中运行：

```powershell
New-NetFirewallRule -DisplayName "Clash for WSL" -Direction Inbound -Action Allow -Protocol TCP -LocalPort 7890
```

> 💡 这条命令允许 WSL 通过防火墙访问 Clash 的 7890 端口

### 步骤 2: 在 WSL 中获取 Windows 主机 IP

在 WSL 终端中运行：

```bash
ip route show | grep -i default | awk '{print $3}'
```

**输出示例**：
```
172.29.64.1
```

> 📌 这个 IP 地址就是 WSL 访问 Windows 主机的正确地址

### 步骤 3: 测试 Clash 代理连接

使用正确的 IP 地址测试：

```bash
curl -I --proxy http://172.29.64.1:7890 https://www.google.com --connect-timeout 5
```

**成功标志**：
```
HTTP/1.1 200 Connection established
HTTP/2 200
```

如果显示 `Connection refused`，请检查：
- Clash 是否正在运行
- Allow LAN 是否已开启
- 防火墙规则是否已添加

### 步骤 4: 配置 Git 使用代理

```bash
# 配置全局代理（使用你自己的 Windows IP）
git config --global http.proxy http://172.29.64.1:7890
git config --global https.proxy http://172.29.64.1:7890
```

**验证配置**：
```bash
git config --global --get-regexp proxy
```

**输出应显示**：
```
http.proxy http://172.29.64.1:7890
https.proxy http://172.29.64.1:7890
```

### 步骤 5: 克隆仓库

现在可以正常克隆了：

```bash
# 推荐：使用浅克隆（只克隆最新历史）
git clone --depth 1 https://github.com/用户名/仓库名.git

# 或完整克隆
git clone https://github.com/用户名/仓库名.git
```

---

## 后续使用指南

### ✅ 每次使用前的准备

**1. 启动 Clash**
- 在 Windows 中启动 **Clash for Windows**
- 确保 **Allow LAN** 保持开启状态
- 确认系统托盘中 Clash 图标显示已连接

**2. 直接使用 Git**
- Git 已经配置好代理，无需每次重新配置
- 所有 Git 操作（clone、pull、push、fetch）都会自动通过代理

### 📝 常见使用场景

#### 克隆新仓库
```bash
git clone https://github.com/用户名/仓库名.git
```

#### 拉取更新
```bash
cd 仓库目录
git pull
```

#### 推送代码
```bash
git push origin main
```

> 💡 所有这些操作都会自动使用 Clash 代理，无需额外操作

---

## 代理管理

### 查看当前代理配置
```bash
git config --global --get-regexp proxy
```

### 临时禁用代理（某次操作不用代理）
```bash
git clone https://github.com/xxx/xxx.git --config http.proxy="" --config https.proxy=""
```

### 永久取消代理
```bash
git config --global --unset http.proxy
git config --global --unset https.proxy
```

### 重新启用代理
```bash
# 记得替换为你的 Windows IP
git config --global http.proxy http://172.29.64.1:7890
git config --global https.proxy http://172.29.64.1:7890
```

---

## 故障排查

### 问题 1: 克隆时提示 "Connection refused"

**可能原因**：
- Clash 未启动
- Allow LAN 未开启
- 防火墙阻止连接

**解决方法**：
```bash
# 1. 检查 Clash 是否运行（在 Windows 上）
# 2. 测试代理连接
curl -I --proxy http://172.29.64.1:7890 https://www.google.com

# 3. 如果失败，重新获取 Windows IP
ip route show | grep -i default | awk '{print $3}'

# 4. 更新 Git 代理配置
git config --global http.proxy http://新的IP:7890
git config --global https.proxy http://新的IP:7890
```

### 问题 2: 克隆仍然很慢

**可能原因**：
- 代理未生效
- Clash 节点速度慢

**解决方法**：
```bash
# 1. 验证代理配置
git config --global --get-regexp proxy

# 2. 在 Clash 中切换到速度更快的节点

# 3. 使用浅克隆减少下载量
git clone --depth 1 https://github.com/xxx/xxx.git
```

### 问题 3: WSL 重启后 IP 地址变化

**现象**：之前配置的代理突然不工作了

**解决方法**：
```bash
# 重新获取 Windows IP
NEW_IP=$(ip route show | grep -i default | awk '{print $3}')
echo "新的 Windows IP: $NEW_IP"

# 更新 Git 配置
git config --global http.proxy http://$NEW_IP:7890
git config --global https.proxy http://$NEW_IP:7890
```

> 💡 **自动化脚本**：可以将以下内容添加到 `~/.bashrc`：
```bash
# 自动更新 Git 代理到当前 Windows IP
update_git_proxy() {
    local WIN_IP=$(ip route show | grep -i default | awk '{print $3}')
    git config --global http.proxy http://$WIN_IP:7890
    git config --global https.proxy http://$WIN_IP:7890
    echo "Git 代理已更新到: $WIN_IP:7890"
}
```

> 使用方法：在终端输入 `update_git_proxy` 即可自动更新代理配置

---

## 核心要点总结

| 项目 | 说明 |
|------|------|
| **Clash 必须运行** | ✅ 每次使用 Git 前确保 Clash 已启动 |
| **Allow LAN 必须开启** | ✅ 只需开启一次，会保存配置 |
| **防火墙规则** | ✅ 已添加后永久有效 |
| **Git 代理配置** | ✅ 配置一次后永久生效（除非 IP 变化） |
| **IP 地址** | ⚠️ WSL 重启后可能变化，需重新获取 |

### 最简使用流程

1. **启动 Clash**（在 Windows 中）
2. **直接使用 Git**（无需其他操作）

就是这么简单！🎉

---

## 其他 Git 操作加速技巧

### 1. 使用浅克隆
```bash
# 只克隆最近 1 次提交
git clone --depth 1 <仓库地址>

# 如果后续需要完整历史
git fetch --unshallow
```

### 2. 克隆时只拉取单个分支
```bash
git clone --single-branch --branch main <仓库地址>
```

### 3. 增加 Git 缓冲区大小
```bash
git config --global http.postBuffer 524288000  # 500MB
```

### 4. 关闭 SSL 验证（不推荐，仅在特殊情况）
```bash
git config --global http.sslVerify false
```

---

## 快速参考命令

```bash
# 获取 Windows IP
ip route show | grep -i default | awk '{print $3}'

# 配置 Git 代理
git config --global http.proxy http://172.29.64.1:7890
git config --global https.proxy http://172.29.64.1:7890

# 查看代理配置
git config --global --get-regexp proxy

# 测试代理
curl -I --proxy http://172.29.64.1:7890 https://www.google.com

# 取消代理
git config --global --unset http.proxy
git config --global --unset https.proxy
```

---

## 文档创建日期

2026年6月23日

---

**祝你使用愉快！如有问题，请按照故障排查章节逐步检查。** 🚀
