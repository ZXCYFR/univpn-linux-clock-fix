"""验证公开补丁工具的错误版本拒绝及文件保护行为，不携带客户端。"""

from pathlib import Path
import stat
import tempfile
import unittest

from patch_clock import transform_binary, write_copy


class PatchSafetyTests(unittest.TestCase):
    """覆盖可能损坏错误版本或覆盖用户文件的实际失败路径。"""

    def test_unknown_binary_rejected(self) -> None:
        """任意未知文件在正向及回退操作中都必须被拒绝。"""
        for restore in (False, True):
            with self.subTest(restore=restore), self.assertRaises(ValueError):
                transform_binary(b"unknown UniVPN build", restore=restore)

    def test_existing_file_preserved(self) -> None:
        """已有输出的内容不能被生成操作覆盖。"""
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "existing"
            target.write_bytes(b"user data")
            with self.assertRaises(FileExistsError):
                write_copy(target, b"replacement")
            self.assertEqual(target.read_bytes(), b"user data")

    def test_symlink_target_preserved(self) -> None:
        """输出符号链接不能成为覆盖其目标的途径。"""
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "source"
            target.write_bytes(b"user data")
            link = Path(directory) / "link"
            link.symlink_to(target)
            with self.assertRaises(FileExistsError):
                write_copy(link, b"replacement")
            self.assertEqual(target.read_bytes(), b"user data")

    def test_copy_has_no_execute_or_setuid_permission(self) -> None:
        """副本写入完整内容，且不携带执行或 setuid 权限。"""
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "copy"
            write_copy(target, b"copy content")
            self.assertEqual(target.read_bytes(), b"copy content")
            self.assertEqual(stat.S_IMODE(target.stat().st_mode), 0o644)


if __name__ == "__main__":
    unittest.main()
