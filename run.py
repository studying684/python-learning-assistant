"""一键启动脚本：项目根目录下执行 python run.py 即可。

启动后浏览器访问 http://127.0.0.1:8000
首次运行会自动创建 data/learning.db（内置 8 个 Python 练手项目）。
"""
import uvicorn

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
