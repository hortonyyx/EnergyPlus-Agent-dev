"""Count actual model tool invocations, never nested implementation log actions."""
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path

from src.agent.runtime_tools import MESH_COORDINATOR_TOOL_NAMES

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]


def main():
    paths = sorted((HERE.parent / '2026-10-01_behaviour_records/records').glob('*/record.json.gz'))
    paths += sorted((ROOT / '.tmp_a5t/history').rglob('record.json.gz'))
    rows = []
    for path in paths:
        data = json.loads(gzip.decompress(path.read_bytes()))
        source = path
        if data.get('source_format') == 'event_envelope_reference':
            source = (path.parent / data['event_log']['uri']).resolve()
            assert hashlib.sha256(source.read_bytes()).hexdigest() == data['event_log']['sha256']
            events = [json.loads(line)['payload'] for line in source.read_bytes().splitlines()]
            counts = Counter(e['tool_name'] for e in events if e['event_type'] == 'tool_invocation')
        else:
            counts = Counter(s['tool'] for i in data['invocations'] for s in i['steps'])
        rows.append(dict(record=str(path.relative_to(ROOT)), counted_source=str(source.relative_to(ROOT)),
            counted_source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
            calls=dict(sorted(counts.items())), total_calls=counts.total()))
    totals = Counter()
    for row in rows:
        totals.update(row['calls'])
    removed = {
        'preview_space_trace': '旧轨迹轮廓入口；由保存平面草稿、inspect_plan_draft 和像素区域查看覆盖。',
        'view_space_trace': '旧轨迹回看；当前平面草稿与源平面覆盖。',
        'select_space_trace': '旧轨迹选择；产物无生产消费者，历史处理器保留。',
        'view_candidate': '0 次；源平面重开并入 inspect_candidate(include_plan=true)，保留原渲染器。',
        'view_claim_evidence': '0 次；依据重开并入 view_image(claim_id=...)，保留原哈希核验与裁图。',
        'pixel_profile': '有历史调用；按派工合入 view_pixel_profile(include_image=false)，旧数值接口仅历史重放。',
    }
    unique = {
        'build_bim': '通用世界坐标几何首稿入口；网格/推理输入未必有可用的平面像素草稿。',
        'claim_transaction': 'A2 后统一的尺寸依据事务入口；旧调用记录中的拆分写入不能证明新入口无用。',
        'review_detail': '明确配置才启用的局部视觉复核，默认已不暴露。',
        'record_work_review': '明确启用续轮时的复核记录，默认已不暴露。',
        'map_dimension_chain': '首稿前独立尺寸链累计换算的唯一入口；claim_transaction 需要已有候选。',
        'compare_facade_spans': '独立完整开口序列的正反方向比较，其他查看工具不计算该关系。',
        'view_plan_wall_support': '按用户指定颜色检查完整路径与门洞外缺墨区，包括失败草稿；drawing_differences 为有限启发式。',
        'check_wall_dimensions': '墙侧面/代表线转换及实际墙宿主清单，未知偏移不能猜。',
        'overlay_candidate': '通用/推理候选注册原平面标定的唯一入口；平面编译的自动叠图不覆盖此条件。',
        'record_inference': '推断记录入口；统计语料全为图纸，不代表网格/推理没有用途。',
        'inspect_inference': '查推断记录。', 'audit_inference_candidate': '核推断声明与保存对象覆盖。',
        'build_parametric_bim': '参数化声明展开。', 'inspect_parametric_plan': '取回保存的参数化原声明。',
        'inspect_mesh': '原网格入口。', 'inspect_mesh_directions': '原网格方向。',
        'view_mesh': '原网格渲染。', 'measure_mesh_pixels': '相机投影量测。',
        'view_mesh_observation': '网格量测回看。', 'set_candidate_mesh_frame': '网格/源坐标绑定。',
        'overlay_mesh_candidate': '源与网格叠图。',
    }
    tool_names = sorted(set(MESH_COORDINATOR_TOOL_NAMES) | set(totals))
    for row in rows:
        row['calls'] = {name: row['calls'].get(name, 0) for name in tool_names}
    result = dict(model_requests=0, baseline_commit='f4d48cf7',
        scope='24 runs: all 16 archived 10-01 behaviour records (six good runs 53–58, T1 two, eight additional historical controls), six 10-04 node-regression runs across C2/A1 and two 27B runs. Drawing-only corpus; interrupted attempts included; no nested toolkit actions counted.',
        runs=rows, run_count=len(rows), total_calls=totals.total(),
        tools={name: dict(total_calls=totals[name], runs_used=sum(bool(r['calls'].get(name)) for r in rows),
            decision='remove_from_default' if name in removed else 'already_capability_or_replay_only' if name in
                {'record_claim','decide_claim','confirm_claims','review_detail','record_work_review'} else 'retain',
            reason=removed.get(name, unique.get(name, '本统计范围有实际调用。')))
            for name in tool_names})
    assert len(rows) == 24
    assert all(totals[n] == 0 for n in removed if n != 'pixel_profile')
    (HERE / 'tool_usage.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps(dict(runs=len(rows), calls=totals.total(), removed={n: totals[n] for n in removed}), ensure_ascii=False))


if __name__ == '__main__': main()
