# -*- coding: utf-8 -*-
"""Hook PostToolUse: kiem tra cu phap file .py vua sua.

Loi cu phap thi tra ma 2 de Claude thay loi va sua ngay.
"""

import json
import py_compile
import sys


def main():
    try:
        event = json.load(sys.stdin)
    except ValueError:
        return 0
    path = (event.get("tool_input") or {}).get("file_path", "")
    if not path.endswith(".py"):
        return 0
    try:
        py_compile.compile(path, doraise=True)
    except py_compile.PyCompileError as exc:
        print("Loi cu phap trong", path, file=sys.stderr)
        print(exc.msg, file=sys.stderr)
        return 2
    except OSError:
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
