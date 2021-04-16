import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
import asyncio
import secrets
import os
import io
import json
import pathlib

pool = ThreadPoolExecutor(max_workers=5, thread_name_prefix="MathGraphWaiter")
TMP_DIR = pathlib.Path(os.path.dirname(__file__), "tmp")
GRAPH_FILE = str(pathlib.Path(os.path.dirname(__file__), "_graph.py"))

if not TMP_DIR.exists():
    TMP_DIR.mkdir()

async def plot(points: dict, no: int):
    filename = os.path.join(TMP_DIR, secrets.token_urlsafe(5) + ".png")
    data = json.dumps({"keys": points, "no": no})
    sub = subprocess.Popen(args=(sys.executable, GRAPH_FILE, filename, data), executable=sys.executable)
    await asyncio.get_running_loop().run_in_executor(pool, sub.wait)

    with open(filename, "rb") as f:
        resp = io.BytesIO(f.read())

    os.remove(filename)
    return resp
