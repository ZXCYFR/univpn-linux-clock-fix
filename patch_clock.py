"""检查或生成 UniVPN 时钟修复副本；不安装、不停止或启动 VPN。"""

import argparse
import hashlib
import os
from pathlib import Path
import sys


ORIGINAL_SHA256 = "bb8dc08cd5065195ebb7ab1c84f8b0ac541ad02c82e2c88b03a35f8e7cddb122"
PATCHED_SHA256 = "01bac6fd4f0f65b0ee0aadbe239c1dbd6eead3f148bd90b29e848b460620be64"
CALL_OFFSET = 0x3B1CF6
BYTE_OFFSET = 0x3B1CF8
ORIGINAL_CALL = bytes.fromhex("e8 80 f6 ff ff")
PATCHED_CALL = bytes.fromhex("e8 80 fe ff ff")


def transform_binary(data: bytes, restore: bool = False) -> bytes:
    """校验完整文件及调用指令，只改变一个字节。

    Args:
        data: 用户合法取得的 UniVPNCS 文件内容。
        restore: 是否将已核对的修复副本还原为原始文件内容。

    Returns:
        经目标 SHA256 校验的完整副本内容。

    Raises:
        ValueError: 来源版本、调用指令或输出校验不符合已验证条件。
    """
    source_hash = PATCHED_SHA256 if restore else ORIGINAL_SHA256
    target_hash = ORIGINAL_SHA256 if restore else PATCHED_SHA256
    source_call = PATCHED_CALL if restore else ORIGINAL_CALL
    if hashlib.sha256(data).hexdigest() != source_hash:
        raise ValueError("完整文件 SHA256 不匹配，拒绝修改；不能仅凭版本号套用补丁")
    if data[CALL_OFFSET:CALL_OFFSET + len(source_call)] != source_call:
        raise ValueError("校准函数调用指令不匹配，拒绝修改")
    result = bytearray(data)
    result[BYTE_OFFSET] = 0xF6 if restore else 0xFE
    if hashlib.sha256(result).hexdigest() != target_hash:
        raise ValueError("生成内容的 SHA256 不匹配，拒绝输出")
    return bytes(result)


def write_copy(destination: Path, data: bytes) -> None:
    """以独占创建方式保存不可执行的副本，不覆盖已有文件。

    Args:
        destination: 不存在的副本路径；不负责创建其父目录。
        data: 已完成校验的副本内容。

    Raises:
        FileExistsError: 输出路径已存在，包括符号链接。
        OSError: 文件创建、写入或权限设置失败。
    """
    # 创建时权限 0600，完整写入并落盘后改为 0644；不继承 setuid 权限。
    descriptor = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "wb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
        os.fchmod(handle.fileno(), 0o644)


def main() -> int:
    """处理命令行参数，默认只读检查；生成副本后返回退出状态。

    Returns:
        成功为 0；版本不匹配或文件操作失败为 1。
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="UniVPNCS 来源路径")
    parser.add_argument("--output", type=Path, help="生成副本的路径，必须不存在")
    parser.add_argument("--restore", action="store_true", help="从修复副本生成原始内容副本")
    args = parser.parse_args()
    if args.restore and args.output is None:
        parser.error("--restore 必须同时指定 --output")
    try:
        data = args.source.read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        print("来源 SHA256：", digest)
        if args.output is None:
            if digest == ORIGINAL_SHA256:
                print("匹配已验证的原始 Linux x86-64 文件；未改动任何文件。")
            elif digest == PATCHED_SHA256:
                print("匹配已验证的修复文件；未改动任何文件。")
            else:
                raise ValueError("不匹配已验证的文件；请提交版本信息，不要套用本补丁")
            return 0
        corrected = transform_binary(data, restore=args.restore)
        write_copy(args.output, corrected)
        print("副本已生成：", args.output)
        print("副本 SHA256：", hashlib.sha256(corrected).hexdigest())
        print("只生成了 0644 副本；未安装，也未断开或重启 VPN。")
        return 0
    except (OSError, ValueError) as error:
        print(f"操作失败：{error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
