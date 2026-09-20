"""按建筑 ID 从香港地政总署「可視化三維地圖（單體化模型）」按需取单栋。

不下载整幅 ZIP（一幅约 1–2.6 GB），而是读 ZIP 中央目录后用 HTTP Range
只取目标建筑的条目。全部条目逐个校验 CRC32。

索引来源：CSDI Portal 的 file-api（每个图幅带 glTF/FBX/MAX 直链，key 公开）。
许可：data.gov.hk / CSDI 通用条款，免费、可商用，须注明来源。
"""
import argparse, binascii, collections, json, os, struct, sys, urllib.request, zlib
from pathlib import Path

INDEX_API = ("https://portal.csdi.gov.hk/csdi-webpage/file-api"
             "?dataset_id=landsd_rcd_1671676915450_88604"
             "&format=geojson&layer_name=Individualised_models")
TIMEOUT = 300


RETRIES = 6


def _get(url, headers=None):
    """代理偶发 502，按指数退避重试。"""
    import time
    last = None
    for attempt in range(RETRIES):
        try:
            req = urllib.request.Request(url, headers=headers or {})
            with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
                return r.read(), r.headers
        except Exception as exc:  # noqa: BLE001 - 网络层各类异常都重试
            last = exc
            if attempt < RETRIES - 1:
                time.sleep(2 ** attempt)
    raise RuntimeError(f"取 {url} 失败（重试 {RETRIES} 次）: {last}")


def rng(url, a, b):
    data, _ = _get(url, {"Range": f"bytes={a}-{b}"})
    return data


def content_length(url):
    import time
    last = None
    for attempt in range(RETRIES):
        try:
            req = urllib.request.Request(url, method="HEAD")
            with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
                return int(r.headers["Content-Length"])
        except Exception as exc:  # noqa: BLE001
            last = exc
            if attempt < RETRIES - 1:
                time.sleep(2 ** attempt)
    raise RuntimeError(f"取长度失败: {last}")


def central_directory(url, total, tail=3_000_000):
    """读 ZIP 尾部，解析中央目录，返回条目清单。"""
    data = rng(url, max(0, total - tail), total - 1)
    base = total - len(data)
    i = data.rfind(b"PK\x05\x06")
    if i < 0:
        raise RuntimeError("未找到 EOCD")
    _, _, _, _, cnt, _, cd_off, _ = struct.unpack_from("<IHHHHIIH", data, i)
    if cd_off - base < 0:  # 中央目录不在已取范围内，按精确偏移重取
        data = rng(url, cd_off, total - 1)
        base = cd_off
        i = data.rfind(b"PK\x05\x06")
        _, _, _, _, cnt, _, cd_off, _ = struct.unpack_from("<IHHHHIIH", data, i)
    p, ents = cd_off - base, []
    for _ in range(cnt):
        if data[p:p + 4] != b"PK\x01\x02":
            break
        h = struct.unpack_from("<IHHHHHHIIIHHHHHII", data, p)
        nlen, elen, clen = h[10], h[11], h[12]
        ents.append(dict(name=data[p + 46:p + 46 + nlen].decode("utf-8", "replace"),
                         method=h[4], crc=h[7], csz=h[8], usz=h[9], off=h[16]))
        p += 46 + nlen + elen + clen
    return ents


def extract(url, entry):
    """按 Range 取出单个 ZIP 条目并校验 CRC32。"""
    head = rng(url, entry["off"], entry["off"] + 29)
    _, _, _, _, _, _, _, _, _, nlen, elen = struct.unpack("<IHHHHHIIIHH", head)
    start = entry["off"] + 30 + nlen + elen
    raw = rng(url, start, start + entry["csz"] - 1)
    data = zlib.decompress(raw, -15) if entry["method"] == 8 else raw
    if (binascii.crc32(data) & 0xFFFFFFFF) != entry["crc"]:
        raise RuntimeError(f"CRC 校验失败: {entry['name']}")
    return data, len(raw)


def sheet_index(cache: Path):
    if cache.exists():
        return json.loads(cache.read_text())
    data, _ = _get(INDEX_API)
    cache.write_text(data.decode("utf-8"))
    return json.loads(data)


def sheet_for(index, lon, lat):
    for f in index["features"]:
        ring = f["geometry"]["coordinates"][0]
        n, inside, j = len(ring), False, len(ring) - 1
        for i in range(n):
            xi, yi = ring[i][:2]
            xj, yj = ring[j][:2]
            if ((yi > lat) != (yj > lat)) and (lon < (xj - xi) * (lat - yi) / (yj - yi) + xi):
                inside = not inside
            j = i
        if inside:
            return f["properties"]
    return None


def fetch_building(url, ents_by_bid, bid, outdir: Path):
    """取出一栋建筑的全部文件，转成自包含 GLB，返回记录。"""
    import trimesh
    ents = ents_by_bid[bid]
    outdir.mkdir(parents=True, exist_ok=True)
    files, transferred = [], 0
    for e in sorted(ents, key=lambda x: x["off"]):
        data, raw_len = extract(url, e)
        transferred += raw_len
        name = os.path.basename(e["name"])
        (outdir / name).write_bytes(data)
        files.append(dict(name=name, bytes=len(data), crc32=f"{e['crc']:08x}",
                          zip_offset=e["off"], compressed=e["csz"]))
    gltf = next(f for f in files if f["name"].endswith(".gltf"))
    scene = trimesh.load(outdir / gltf["name"], process=False)
    mesh = list(scene.geometry.values())[0] if hasattr(scene, "geometry") else scene
    glb = outdir / "input.glb"
    mesh.export(glb)
    tex = getattr(mesh.visual.material, "baseColorTexture", None)
    ext = mesh.bounds[1] - mesh.bounds[0]
    return dict(building_id=bid, files=files, transferred_bytes=transferred,
                glb_bytes=glb.stat().st_size,
                faces=int(len(mesh.faces)), vertices=int(len(mesh.vertices)),
                extents_m=[round(float(v), 3) for v in ext],
                surface_area_m2=round(float(mesh.area), 1),
                texture_px=list(tex.size) if tex else None,
                texture_px_per_m=round((tex.size[0] * tex.size[1] / float(mesh.area)) ** 0.5, 1) if tex else None)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(Path(__file__).parent / "single_buildings"))
    ap.add_argument("--only", help="只取这一个建筑 ID")
    args = ap.parse_args()
    sys.path.insert(0, str(Path(__file__).parent))
    from selection import SELECTION
    here = Path(__file__).parent
    index = sheet_index(here / "sheet_index.geojson")
    districts = json.loads((here / "districts.json").read_text())
    out = Path(args.out)
    # 按图幅分组，同一幅只读一次中央目录
    by_sheet = collections.defaultdict(list)
    for d, bid, c1, c2, c3, why in SELECTION:
        if args.only and bid != args.only:
            continue
        by_sheet[d].append((bid, c1, c2, c3, why))
    records = []
    for dist, items in by_sheet.items():
        info = districts[dist]
        sheet = sheet_for(index, info["lon"], info["lat"])
        url = sheet["Format_glTF"]
        total = content_length(url)
        ents = central_directory(url, total)
        by_bid = collections.defaultdict(list)
        for e in ents:
            if e["name"].startswith("BUILDING/") and not e["name"].endswith("/"):
                by_bid[e["name"].split("/")[1]].append(e)
        print(f"[{dist}] 图幅 {sheet['SHEETNO']} rev={sheet['REVISIONDATE']} "
              f"zip={total/2**30:.2f}GB 建筑={len(by_bid)}")
        for bid, c1, c2, c3, why in items:
            done = out / bid / "record.json"
            if done.exists():          # 断点续跑
                rec = json.loads(done.read_text())
                records.append(rec)
                print(f"   {bid}  已存在，跳过")
                continue
            rec = fetch_building(url, by_bid, bid, out / bid)
            rec.update(district=dist, sheet_no=sheet["SHEETNO"],
                       sheet_revision=sheet["REVISIONDATE"], source_url=url,
                       zip_total_bytes=total, axis1_complexity=c1,
                       axis2_type=c2, axis3_quality=c3, selection_reason=why)
            (out / bid / "record.json").write_text(json.dumps(rec, ensure_ascii=False, indent=1))
            records.append(rec)
            print(f"   {bid}  {rec['faces']:>5d}面  "
                  f"{rec['extents_m']}  贴图{rec['texture_px']}  "
                  f"传输 {rec['transferred_bytes']/1024:.0f}KB")
    (out / "manifest.json").write_text(json.dumps(
        dict(source="Lands Department HKSAR · 3D Visualisation Map (Individualised models)",
             index_api=INDEX_API, licence="data.gov.hk / CSDI Terms of Use",
             attribution="© The Government of the Hong Kong SAR (Lands Department)",
             buildings=records), ensure_ascii=False, indent=1))
    print(f"\n完成 {len(records)} 栋，清单写入 {out/'manifest.json'}")


if __name__ == "__main__":
    main()
