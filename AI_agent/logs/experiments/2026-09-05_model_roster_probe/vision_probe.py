#!/usr/bin/env python3
"""2026-09-05 席位识图探针 —— 复现 README §二的两张图与两个读数。

用法（凭据从仓库根 .env 读，⛔ 脚本里不写明文）：
    python3 AI_agent/logs/experiments/2026-09-05_model_roster_probe/vision_probe.py glm-5.3-flash glm-5.3

判据：两张图各问【数量 + 指定序位的颜色】两个量，两个都对才算「看见了」——
单问数量会被瞎猜命中，这就是探针要两个量的原因。
"""
import base64, io, json, os, sys, urllib.request
from PIL import Image, ImageDraw

PROBES = [  # (n, 高亮序位 0-based, 高亮色, 底色)
    (7, 4, "red", "blue"),
    (4, 1, "green", "orange"),
]


def make_png(n, hi, hi_color, base_color):
    img = Image.new("RGB", (320, 160), "white")
    d = ImageDraw.Draw(img)
    step = 300 // n
    for i in range(n):
        x = 10 + i * step
        d.rectangle([x, 40, x + step - 10, 110], fill=hi_color if i == hi else base_color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


def load_env(path):
    env = {}
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    return env


def ask(base_url, api_key, model, b64, question):
    body = json.dumps({
        "model": model,
        "max_tokens": 900,
        "messages": [{"role": "user", "content": [
            {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": b64}},
            {"type": "text", "text": question},
        ]}],
    }).encode()
    req = urllib.request.Request(
        base_url.rstrip("/") + "/v1/messages", data=body,
        headers={"x-api-key": api_key, "anthropic-version": "2023-06-01",
                 "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=180) as resp:
        payload = json.load(resp)
    return " ".join(c.get("text", "") for c in payload.get("content", []) if c["type"] == "text")


def main(models):
    root = os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")
    env = load_env(os.path.join(root, ".env"))
    base_url, api_key = env["GLM_ANTHROPIC_BASE_URL"], env["GLM_API_KEY"]
    for n, hi, hi_color, base_color in PROBES:
        b64 = make_png(n, hi, hi_color, base_color)
        q = (f"How many rectangles are in this image, and what color is the "
             f"{hi + 1}th one from the left? Answer in one short line.")
        print(f"\n=== probe: {n} rects, #{hi + 1} is {hi_color} ===")
        for m in models:
            print(f"  [{m}] {ask(base_url, api_key, m, b64, q)!r}")


if __name__ == "__main__":
    main(sys.argv[1:] or ["glm-5.3-flash", "glm-5.3"])
