# UniVPN Linux 定时断线：TSC 校准诊断与本地修复

Linux UniVPN / IPsec rekey / hourly disconnect / CPU MHz / invariant TSC。

本项目记录一个已实测的 UniVPN Linux 客户端计时缺陷：启动时读取动态 `cpu MHz` 来换算 CPU 时间戳计数器（TSC），使定时器走慢，IPsec 密钥续期晚于服务器到期时间，表现为约一小时掉线、长时间文件传输被中断。

在一台 Intel Core i7-10700K、Ubuntu 24.04 的机器上，修正校准路径后，真实 10 秒从只计为 8.07 秒恢复为 10.00 秒。2026-10-09 00:42 至 09:34 的验证窗口内连续在线约 **8 小时 51 分钟，成功完成 9 次续期，没有重新连接记录**。

这是社区诊断项目，与 UniVPN 厂商没有隶属关系。提供的是诊断说明、我们编写的工具及只适用于已核对文件的本地补丁方法。仓库不分发 UniVPN 客户端、安装包或修复后的客户端二进制；原软件的权利和许可仍属于其权利人。

## 适用范围

| 条件 | 已验证范围 |
|---|---|
| 客户端 | Linux x86-64，10781.19.0.1214 |
| 后台文件 | `UniVPNCS`，6,771,528 字节 |
| 协议 | L2TP over IPsec，IPsec SA 生命周期 3600 秒 |
| 硬件和系统 | Intel Core i7-10700K，Ubuntu 24.04 |
| 原文件 SHA256 | `bb8dc08cd5065195ebb7ab1c84f8b0ac541ad02c82e2c88b03a35f8e7cddb122` |
| 修复文件 SHA256 | `01bac6fd4f0f65b0ee0aadbe239c1dbd6eead3f148bd90b29e848b460620be64` |

**完整文件 SHA256 必须匹配。**相同软件版本号仍可能存在不同构建。本补丁不能用于未知文件、ARM、macOS、Windows，或直接套用到 10781.21.0.0831。纯 SSL VPN、服务器强制会话期限、认证失败、路由冲突或网络故障也不能仅凭“掉线”归为此问题。

## 如何判断是否相关

典型线索是：连接开始正常，约一小时后断开；Windows 可持续连接；持续传输仍会断；不同启动时有时稳定、有时不稳定。日志在断线前没有正常的 IPsec 第二阶段续期完成记录。

在 `/usr/local/UniVPN/log/UniVPN_UniVPNCS_*.log` 中查找以下事件：

```text
[Handle expiration][start]
[IKE Phase2 renegotiate][start]
[IKE Phase2 renegotiate][finished]
```

`0x8001a` 或 PPP 回应超时只是后续断线线索，单独出现不能证明计时缺陷。IKE 的 Informational 交换也不是续期成功。

如需分享证据，请只整理事件名称、时间、客户端版本及文件 SHA256，不上传完整日志、配置、进程内存、账号、密钥、服务器地址或内网路由。

## 原因与修复

本机原后台保存的换算频率为 4698.230 MHz；独立测得实际 TSC 为约 3792.002 MHz。原本应等待 53.95 分钟的续期定时器因此真实等待约 66.84 分钟，晚于 60 分钟的 SA 生命周期。

客户端内部已有实际测量 TSC 的备用校准函数。本地修复只把校准初始化的第一次调用切换到该现成函数：

```text
文件偏移：0x3b1cf8
字节：    f6 → fe
调用指令：e8 80 f6 ff ff → e8 80 fe ff ff
目标地址：0x3b137b → 0x3b1b7b
```

不修改账号、认证、加密参数、路由或服务器会话期限。这里的二进制偏移只对上述完整 SHA256 对应的文件成立。

详细原理、历史正常期的解释边界及厂商源码修复建议见 [诊断证据](docs/diagnosis.md)。

## 使用工具

需要 Python ≥ 3.10，无第三方 Python 依赖，不必安装软件包。先从合法授权渠道自行取得原客户端。

```bash
git clone https://github.com/ZXCYFR/univpn-linux-clock-fix.git
cd univpn-linux-clock-fix

# 默认只读检查，不改动任何文件或当前连接。
python3 patch_clock.py /usr/local/UniVPN/serviceclient/UniVPNCS

# 仅生成当前目录中的补丁副本；输出必须不存在。
python3 patch_clock.py /usr/local/UniVPN/serviceclient/UniVPNCS \
  --output ./UniVPNCS.clock-fixed
```

生成的副本权限是 0644，不能直接执行，也不会自动安装。安装必须在传输结束、客户端及后台均退出后进行；见 [安装、验证与回退](docs/install.md)。重装或更新客户端会覆盖补丁，应重新核对完整文件，不要自动对新版本打补丁。

也可以从已核对的修复文件生成原始内容副本：

```bash
python3 patch_clock.py ./UniVPNCS.clock-fixed \
  --restore --output ./UniVPNCS.restored
```

如果输入不匹配已验证的完整文件，或输出路径已存在，工具会拒绝操作。不要通过修改校验常量强行适配新版本。

## 独立测量 TSC

附带的 C 程序在 Linux x86-64 上比较 `rdtsc` 与 `CLOCK_MONOTONIC_RAW`，不改变 CPU 频率，也不启动 VPN：

```bash
gcc -std=c11 -Wall -Wextra -Werror -O2 measure_tsc.c -o /tmp/univpn-measure-tsc
/tmp/univpn-measure-tsc
```

这是短采样的交叉核对工具，不是所有处理器上的通用校准实现，也不替代对客户端实际计时和续期行为的验证。

## 已完成验证

- 原客户端校准函数的隔离调用，确认原路径与实测路径差异；未运行客户端主入口或建立测试 VPN。
- 修复后真实后台计时：真实 10.000584 秒，内部 1000 步 × 10 毫秒 = 10.00 秒。
- 同一次连接连续跨越 9 次密钥续期，未发生重新登录；[脱敏验证时间线](docs/validation.md)。
- 公共工具在实际已验证文件上生成补丁、反向还原，逐字节及 SHA256 核对。
- 对未知版本、已有输出和符号链接的拒绝测试；副本不继承执行或 setuid 权限。

```bash
python3 -m unittest discover -s tests -v
```

自动测试不包含厂商二进制，也不声称替代真实 VPN 长连接验证。当前实证来自一台机器和一个构建；欢迎提供脱敏的独立复现。

## 缺陷报告与贡献

如遇相同情况，请在 [Issues](https://github.com/ZXCYFR/univpn-linux-clock-fix/issues) 提供系统、CPU 型号、客户端版本、`UniVPNCS` SHA256、协议及断开间隔、明确续期事件的时间线。请区分已实测结果与推测，避免上传凭据或完整配置。

厂商可以从源码层面采用单调时钟计算等待时间，或可靠校准 TSC，避免把动态 `cpu MHz` 当作稳定计时时钟频率。我们未取得厂商源码，不能提交经过编译验证的厂商源码补丁。

本项目代码和原创文档采用 MIT 许可；该许可不授予对 UniVPN 专有软件的再分发权利。
