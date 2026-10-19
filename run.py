"""一键启动脚本：项目根目录下执行 python run.py 即可。

启动后浏览器访问 http://127.0.0.1:8000
首次运行会自动创建 data/learning.db（内置 8 个 Python 练手项目）。

用法：
    python run.py                     # 正常启动（默认不开启热重载）
    python run.py --reload            # 开发模式：改代码自动重启
    python run.py --host 0.0.0.0 --port 9000
"""
from __future__ import annotations

import argparse


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="启动 Python 学习路线助手")
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="监听地址，默认 127.0.0.1（仅本机访问；改成 0.0.0.0 才能被局域网访问）",
    )
    parser.add_argument("--port", type=int, default=8000, help="监听端口，默认 8000")
    parser.add_argument(
        "--reload",
        action="store_true",
        help="开启热重载（开发用，会额外起一个看门狗进程，生产/演示不要开）",
    )
    args = parser.parse_args(argv)

    # 延迟导入：--help 不需要装 uvicorn 也能用
    import uvicorn

    uvicorn.run("app.main:app", host=args.host, port=args.port, reload=args.reload)


if __name__ == "__main__":
    main()
