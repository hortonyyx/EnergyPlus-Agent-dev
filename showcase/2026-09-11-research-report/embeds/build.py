#!/usr/bin/env python3
"""Create self-contained presentation embeds from the checked-in viewers.

The large HTML payloads intentionally remain copies of the original offline
viewers: their Three.js code, geometry and embedded UV JPEGs are not rebuilt.
This script adds only presentation chrome and display-only filtering.
"""
from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCES = {
    "sm25.html": ROOT / "demos/sm25/sm25_showcase.html",
    "voimatalo.html": ROOT / "demos/textured-mass/index.html",
    "voimatalo-input.html": ROOT / "demos/textured-mass/input_viewer.html",
}
OUT = Path(__file__).resolve().parent

STYLE = """
<style id="embed-style">
  html,body { background:#f8f9f7 !important; }
  #panel,#rinfo,#state,aside { display:none !important; }
  canvas { display:block; width:100% !important; height:100% !important; }
  #embed-controls { position:fixed; z-index:20; left:12px; bottom:12px; display:flex;
    align-items:center; gap:5px; max-width:calc(100% - 24px); padding:6px 7px;
    color:#303b42; background:rgba(248,249,247,.92); border:1px solid #d3dad7;
    border-radius:7px; box-shadow:0 2px 8px rgba(31,42,45,.10); font:11px/1.2 system-ui,sans-serif; }
  #embed-controls .embed-label { margin:0 2px 0 1px; color:#59666a; white-space:nowrap; }
  #embed-controls button { appearance:none; border:1px solid #c8d1ce; border-radius:5px; background:#fff;
    color:#344148; padding:4px 6px; font:inherit; cursor:pointer; white-space:nowrap; }
  #embed-controls button:hover { background:#eef2f0; }
  body.embed-bare #embed-controls { display:none; }
</style>
"""

KEY_FORWARDING = """
<script id="embed-key-forwarding">
(() => {
  const allowed = new Set(['ArrowLeft','ArrowRight','PageUp','PageDown','Home','End','F','O','f','o']);
  document.addEventListener('keydown', event => {
    const active = document.activeElement;
    const editing = active && (active.matches('input,select,textarea') || active.isContentEditable);
    if (!editing && allowed.has(event.key)) {
      event.preventDefault();
      parent.postMessage({type:'bim-slide-key', key:event.key}, '*');
    }
  });
})();
</script>
"""


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if text.count(old) != 1:
        raise RuntimeError(f"{label}: expected one match for {old!r}, found {text.count(old)}")
    return text.replace(old, new, 1)


def common(text: str, controls: str) -> str:
    text = replace_once(text, "</style>", "</style>" + STYLE, "style insertion")
    footer = "</body>" if text.count("</body>") == 1 else "</html>"
    text = replace_once(text, footer, controls + KEY_FORWARDING + footer, "footer insertion")
    # The texture-only input viewer uses this exact clear colour.  Other pages
    # inherit the browser background through the transparent renderer.
    return text.replace("new THREE.Color(0xedf2f7)", "new THREE.Color(0xf8f9f7)")


def bim_controls(label: str, default: str) -> str:
    return f"""
<div id="embed-controls" aria-label="{label} presentation controls">
  <span class="embed-label">拖动旋转 · drag</span>
  <button type="button" id="embed-whole">整体 / whole</button>
  <button type="button" id="embed-layers">分层 / layers</button>
  <button type="button" id="embed-reset">复位 / reset</button>
</div>
<script id="embed-bim-controls">
(() => {{
  const input = (id, value, event='input') => {{ const el=document.getElementById(id); if (!el) return;
    el.value=value; el.dispatchEvent(new Event(event, {{bubbles:true}})); }};
  const whole = () => {{ input('floorSel','-1','change'); input('explodeMode','floor','change'); input('explode','0'); input('opacity','1'); }};
  const layers = () => {{ input('floorSel','-1','change'); input('explodeMode','floor','change'); input('explode','0.26'); input('opacity','1'); }};
  document.getElementById('embed-whole').onclick=whole;
  document.getElementById('embed-layers').onclick=layers;
  document.getElementById('embed-reset').onclick=() => document.getElementById('reset')?.click();
  const bare = new URLSearchParams(location.search).get('bare') === '1';
  if (bare) document.body.classList.add('embed-bare');
  {default}();
}})();
</script>
"""


def texture_controls() -> str:
    return """
<div id="embed-controls" aria-label="textured mass presentation controls">
  <span class="embed-label">拖动旋转 · drag to rotate</span>
  <button type="button" id="embed-reset">复位 / reset</button>
</div>
<script id="embed-texture-controls">
(() => {
  const bare = new URLSearchParams(location.search).get('bare') === '1';
  if (bare) document.body.classList.add('embed-bare');
  document.getElementById('embed-reset').onclick=() => {
    // Kept in the original viewer's lexical scope; a double click is not used.
    const canvas=document.querySelector('canvas');
    canvas?.dispatchEvent(new Event('pointerup', {bubbles:true}));
    location.reload();
  };
})();
</script>
"""


def build_bim(source: Path, title: str, default: str) -> str:
    text = source.read_text(encoding="utf-8")
    # Purely display-level: retain GEO unchanged, but omit ceiling polygons from
    # the mesh loop so the default layer view exposes actual interior spaces.
    text = replace_once(
        text,
        "  SURF.forEach(s=>{\n    const zone=s.zone||'?', fi=zoneFloor[zone] ?? nearestBase(zmin(s),BASES);",
        "  SURF.filter(s=>s.type !== 'Ceiling').forEach(s=>{\n    const zone=s.zone||'?', fi=zoneFloor[zone] ?? nearestBase(zmin(s),BASES);",
        "ceiling display filter",
    )
    # Scene decorations are presentation-only and are filtered before they are
    # inserted; geometry, material and renderer paths remain the source ones.
    hook = "<script>window.GEO ="
    patch = """<script id=\"embed-scene-filter\">\n(() => { const add=THREE.Scene.prototype.add; THREE.Scene.prototype.add=function(...objects) { const kept=objects.filter(object => !(['GridHelper','AxesHelper'].includes(object.type) || object.isGridHelper || object.isAxesHelper || object.isSprite)); return kept.length ? add.apply(this, kept) : this; }; })();\n</script>\n<script>window.GEO ="""
    text = replace_once(text, hook, patch, "scene filter insertion")
    text = replace_once(text, "renderer.setClearColor(0xf2f4f7);", "renderer.setClearColor(0xf8f9f7);", "BIM clear colour")
    if title == "sm25 BIM":
        text = replace_once(text, "ring.position.copy(cC); scene.add(ring);", "ring.position.copy(cC);", "north compass ring")
        text = replace_once(text, "  scene.add(ntick);", "", "north compass tick")
        text = replace_once(text, "camera.position.set(center.x+radius*1.6, center.y-radius*1.8, center.z+radius*1.3);", "camera.position.set(center.x+radius*1.0, center.y-radius*1.1, center.z+radius*0.85);", "sm25 camera")
    else:
        text = replace_once(text, "camera.position.set(center.x+radius*1.25, center.y-radius*1.45, center.z+radius*1.05);", "camera.position.set(center.x+radius*0.78, center.y-radius*0.90, center.z+radius*0.68);", "Voimatalo camera")
    return common(text, bim_controls(title, default))


def build_texture(source: Path) -> str:
    text = source.read_text(encoding="utf-8")
    text = replace_once(text, "new THREE.WebGLRenderer({antialias:true})", "new THREE.WebGLRenderer({antialias:true,preserveDrawingBuffer:true})", "texture screenshot buffer")
    text = replace_once(text, "camera.position.set(95,80,115);controls.target.set(0,15,0);", "camera.position.set(48,40,62);controls.target.set(0,15,0);", "texture camera")
    return common(text, texture_controls())


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "sm25.html").write_text(build_bim(SOURCES["sm25.html"], "sm25 BIM", "layers"), encoding="utf-8")
    (OUT / "voimatalo.html").write_text(build_bim(SOURCES["voimatalo.html"], "Voimatalo BIM", "whole"), encoding="utf-8")
    (OUT / "voimatalo-input.html").write_text(build_texture(SOURCES["voimatalo-input.html"]), encoding="utf-8")
    print("built sm25.html, voimatalo.html, voimatalo-input.html")


if __name__ == "__main__":
    main()
