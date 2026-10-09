# 安装、验证与回退

本补丁只适用于 README 中完整 SHA256 匹配的 Linux x86-64 文件。公共工具只生成副本，不操作后台或安装路径。以下安装步骤涉及特权客户端，适合能管理本机的用户；机构管理的设备应遵守其管理要求。

## 安装前

1. 完成正在进行的传输，正常退出 UniVPN，确认 `UniVPN`、`UniVPNCS` 和 `UniVPNPromoteService` 都停止。若有容器或监控自动拉起进程，也先停止该机制。
2. 记录安装路径、所有者和权限。下列例子针对实际已验证的 `/usr/local/UniVPN/serviceclient/UniVPNCS`，root:root、4755；若你机器不同，先核对，不能盲目改变权限。
3. 按 README 生成当前目录下的 `UniVPNCS.clock-fixed`，并再次核对 SHA256。

## 安装副本

在仓库目录执行。脚本先核对来源与副本，保留原文件，再同目录原子替换。不会启动客户端；任何检查失败都会停止。不要在传输中执行。

```bash
(
  set -eu
  target=/usr/local/UniVPN/serviceclient/UniVPNCS
  backup="${target}.before-clock-fix-$(date +%Y%m%d-%H%M%S)"
  staged="${target}.clock-fix.new"

  if sudo pgrep -x 'UniVPN|UniVPNCS|UniVPNPromoteSe' >/dev/null; then
    echo '客户端或后台尚未退出，停止安装。'
    exit 1
  fi
  test "$(stat -c '%u:%g:%a' "$target")" = '0:0:4755'
  test ! -e "$backup"
  test ! -e "$staged"
  test ! -L "$staged"
  printf '%s  %s\n' \
    bb8dc08cd5065195ebb7ab1c84f8b0ac541ad02c82e2c88b03a35f8e7cddb122 \
    "$target" | sha256sum -c -
  printf '%s  %s\n' \
    01bac6fd4f0f65b0ee0aadbe239c1dbd6eead3f148bd90b29e848b460620be64 \
    ./UniVPNCS.clock-fixed | sha256sum -c -

  sudo cp --preserve=all -- "$target" "$backup"
  sudo chmod 0600 "$backup"
  sudo cp --preserve=all -- "$target" "$staged"
  sudo chmod 0600 "$staged"
  sudo tee "$staged" < ./UniVPNCS.clock-fixed >/dev/null
  sudo chown --reference="$target" "$staged"
  sudo chmod --reference="$target" "$staged"
  printf '%s  %s\n' \
    01bac6fd4f0f65b0ee0aadbe239c1dbd6eead3f148bd90b29e848b460620be64 \
    "$staged" | sudo sha256sum -c -
  sudo mv -- "$staged" "$target"
  echo "安装完成，原文件保留位置：$backup"
)
```

记录输出的备份位置，不删除它。以原来的桌面用户正常打开 UniVPN，不需要重启操作系统，也不要直接以 root 运行完整 GUI。

## 验证

确认安装后文件 SHA256 等于修复值，建立连接并观察至少两个 SA 生命周期。对于本报告的 3600 秒寿命，应在约第 54 分钟看到 `[IKE Phase2 renegotiate][finished]`，然后再次成功续期，期间没有重新登录或 L2TP 重试耗尽。

也应验证实际使用中的内网目标及文件传输。仅界面显示连接、能 ping 通，或进程存在，都不能代替跨续期验证；如测试文件完整性，应比较传输前后的文件校验值。

## 回退

完成传输，退出所有客户端和后台，停止自动拉起机制。将你保存的原文件复制到同目录暂存路径，核对其 SHA256 为 README 的原值，恢复原 root:root、4755 权限后原子替换安装路径，再以原用户重新连接。

备份被刻意设为 0600，因此恢复时必须恢复原执行和 setuid 权限。若已更新或重新安装其他版本，不要拿旧文件直接覆盖新安装；先核对当前状态，或使用厂商对应版本重新安装。

没有备份时，`patch_clock.py --restore --output ...` 只能从完整 SHA256 匹配的修复文件生成原始内容副本；它不能恢复权限或未知版本。
