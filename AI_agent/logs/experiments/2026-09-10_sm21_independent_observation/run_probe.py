"""Bounded image-only observation, then an explicitly assisted BIM recovery.

Uses the existing subscription/MCP adapter. The observer receives a separate
directory containing only selected original images and a seed-free manifest.
No reference, previous proposal, or previous evaluation reaches that call.
The recovery consumes its unedited answer as an uncertain visual hypothesis.
"""
import argparse
import json
from pathlib import Path
import shutil
import sys
import time
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from PIL import Image
from scripts.tool_scripts.run_bim_agent import digest, dump, run_experiment, subscription

QUESTION = """只分析所给立面图的下层全部可见开口，不规划整栋建筑。
先查看原图，再自行选合适局部。逐个列出开口的门/窗/不确定类型、
原始像素包围框、支持身份判断的可见形状，以及可读到的宽度、窗台/门槛和顶高。
尺寸链与开口的对应关系要由图确认，未标注的尺寸只能估计并明确标注。
请把落地与否、框线和尺寸引线分开；不提供预定开口数。
可以用现有计算工具。最后只给简短观察清单和不确定项，不超过500汉字。
你看不到旧模型，没有模型答案需要迎合。"""


def observe(args):
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    (out / "images").mkdir()
    source = args.images / "South_view.png"
    target = out / "images" / source.name
    shutil.copy2(source, target)
    with Image.open(target) as picture:
        size = list(picture.size)
    manifest = {
        "images": {target.name: {"size": size, "sha256": digest(target)}},
        "scope": QUESTION,
        "input_mode": "independent_local_image_observation",
        "deadline_epoch": time.time() + args.timeout,
        "only_input": "one original elevation and a local question; no seed, plan, GT, or previous observations",
        "implementation_sha256": {
            "scripts/tool_scripts/run_bim_agent.py": digest(ROOT / "scripts/tool_scripts/run_bim_agent.py"),
            str(Path(__file__).relative_to(ROOT)): digest(Path(__file__)),
        },
    }
    dump(out / "inputs.json", manifest)
    receipt = subscription(out, QUESTION, model="haiku", name="observer",
                           readonly=True, timeout=args.timeout)
    answer = receipt.get("result", {}).get("result")
    completed = bool(answer) and not receipt.get("result", {}).get("is_error", False)
    dump(out / "observation.json", {
        "completed": completed, "answer": answer,
        "actual_model": receipt.get("actual_model"),
        "receipt": "observer_receipt.json",
        "image_sha256": manifest["images"][target.name]["sha256"],
        "status": "unverified_model_observation_not_ground_truth",
    })
    print(json.dumps({"completed": completed, "elapsed_seconds": receipt["elapsed_seconds"],
                      "actual_model": receipt.get("actual_model"), "answer": answer}, ensure_ascii=False, indent=2))


def recover(args):
    observation_path = args.observation.resolve() / "observation.json"
    observation = json.loads(observation_path.read_text())
    if not observation["completed"]:
        raise ValueError("independent observation did not finish; no automatic retry or fallback")
    if digest(args.images / "South_view.png") != observation["image_sha256"]:
        raise ValueError("observation image differs from the recovery original")
    scope = """这是还原建模的局部观察辅助恢复实验，不是独立冷启动。
你仍有原六张图和保存方案。另一模型只看了南立面下层，没有看旧候选、平面、GT或历史观察。
下面原样提供它的观察，它可能错误，不是真值。请自行查原图，将可证实的开口身份/位置与
实际源对象逐一核对，处理相互矛盾、重复或遗漏；需要时结合原平面判断宿主。
不要仅改说明，若实际几何不符就保存修订；若观察不可信则说明依据。
保持本轮只处理已观察的南侧下层开口，其他房间分区等既存问题诚实保留，不伪称全图通过。
保留可靠几何和来源，未知不填作已核。最终选定真实可查看候选，并说明变化与尚未验证范围。
没有给GT、正确数量或开发助手手填的坐标。以下是未改写的模型观察：
<independent_visual_observation>
""" + observation["answer"] + "\n</independent_visual_observation>"
    run_experiment(SimpleNamespace(out=args.out, images=args.images, scope=scope,
                                   timeout=args.timeout, resume_candidate=args.seed))
    dump(args.out / "independent_observation_provenance.json", {
        "observation_file": str(observation_path.relative_to(ROOT)),
        "observation_sha256": digest(observation_path),
        "answer_passed_verbatim": True,
        "observer_had_seed_or_reference": False,
        "developer_selected_local_task": "South elevation lower-storey openings",
        "mode": "independent_image_observation_assisted_recovery",
        "observer_cost_is_separate": True,
    })


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["observe", "recover"])
    parser.add_argument("--images", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--timeout", type=int, required=True)
    parser.add_argument("--observation", type=Path)
    parser.add_argument("--seed", type=Path)
    args = parser.parse_args()
    if args.mode == "observe":
        observe(args)
    else:
        if args.observation is None or args.seed is None:
            parser.error("recover requires --observation and --seed")
        recover(args)


if __name__ == "__main__":
    main()
