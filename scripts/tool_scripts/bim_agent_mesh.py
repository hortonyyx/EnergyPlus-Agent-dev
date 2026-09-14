"""Native mesh asset admission and on-demand observations for the BIM agent."""
from __future__ import annotations

import hashlib
import io
import json
import math
from pathlib import Path
import shutil

from mcp.server.fastmcp import Image
from PIL import Image as PILImage


def freeze_mesh(source: Path, run: Path) -> dict:
    from src.agent.geometry.mesh_observation import MeshObservation

    if source.suffix.lower() != '.glb':
        raise ValueError('native mesh input currently requires a self-contained GLB')
    target = run / 'assets' / 'input.glb'
    target.parent.mkdir()
    shutil.copyfile(source, target)
    description = MeshObservation(target).describe()
    return {'source_path': str(source.resolve()), 'frozen_path': 'assets/input.glb',
            'sha256': hashlib.sha256(target.read_bytes()).hexdigest(),
            'bytes': target.stat().st_size, 'geometry': description,
            'note': 'Original mesh asset; no preselected cameras or BIM observations. '
                    'Mesh surfaces may be incomplete/noisy and are not room semantics.'}


def register_mesh_tools(server, toolkit):
    """Expose only the admitted mesh; image-only/detail runs gain no asset access."""
    if not toolkit.manifest.get('mesh_input'):
        return
    asset = None

    def mesh():
        nonlocal asset
        from src.agent.geometry.mesh_observation import MeshObservation
        record = toolkit.manifest['mesh_input']
        path = toolkit.run / 'assets' / 'input.glb'
        if hashlib.sha256(path.read_bytes()).hexdigest() != record['sha256']:
            raise ValueError('input mesh changed')
        if asset is None:
            asset = MeshObservation(path)
        return asset

    def observation_path(observation):
        folder = toolkit.run / 'mesh_observations'
        allowed = {p.stem for p in folder.glob('mesh_*.json')}
        if observation not in allowed:
            raise ValueError('unknown mesh observation; first call view_mesh')
        return folder / observation

    @server.tool()
    def inspect_mesh(yaw_degrees: float = 0, bounds: list[list[float]] | None = None) -> dict:
        """Query original mesh bounds/counts in Z-up metres, optionally in a selected box.
        Local coordinates = rotate_xy(yaw_degrees) of [GLB.x,-GLB.z,GLB.y].
        No inferred walls, floors or footprint. Bounds selection can hide surfaces.
        """
        result = mesh().describe(yaw_degrees=yaw_degrees, bounds=bounds)
        toolkit.log('inspect_mesh', {'yaw_degrees': yaw_degrees, 'bounds': bounds, 'result': result})
        return {**result, 'remaining_seconds': toolkit.remaining_seconds()}

    @server.tool()
    def view_mesh(azimuth_degrees: float = 45, elevation_degrees: float = 25,
                  yaw_degrees: float = 0, target: list[float] | None = None,
                  width_m: float | None = None, height_m: float | None = None,
                  bounds: list[list[float]] | None = None):
        """Render the admitted textured mesh from a camera YOU choose, with metric mapping.
        Z-up local frame as inspect_mesh; azimuth=0 looks FROM +x, 90 FROM +y,
        180 FROM -x, 270 FROM -y. elevation=90 is top. target is local [x,y,z].
        Omit target/spans for an automatic overview; give smaller metric spans
        and a local target for detail. Optional bounds selects triangles by their
        centres before rendering; excluded/occluded areas are not blank-wall proof.
        Returns a 1200x900 image and observation ID for pixel-to-surface measurement.
        """
        for value in (azimuth_degrees, elevation_degrees):
            if not math.isfinite(value):
                raise ValueError('camera angles must be finite')
        if not -90 <= elevation_degrees <= 90:
            raise ValueError('elevation must be between -90 and 90 degrees')
        info = mesh().describe(yaw_degrees=yaw_degrees, bounds=bounds)
        if info['bounds'] is None:
            raise ValueError('bounds selected no mesh faces; widen the selection or inspect the full asset')
        lo, hi = info['bounds']
        centre = [(a+b)/2 for a,b in zip(lo,hi)] if target is None else target
        if len(centre) != 3 or not all(math.isfinite(v) for v in centre):
            raise ValueError('target must be a finite 3D point')
        diameter = max(math.dist(lo, hi), 1)
        if width_m is None and height_m is None:
            height_m = diameter * 1.05
        if width_m is None:
            width_m = height_m * 4 / 3
        if height_m is None:
            height_m = width_m * 3 / 4
        a,e = math.radians(azimuth_degrees), math.radians(elevation_degrees)
        direction = [math.cos(a)*math.cos(e), math.sin(a)*math.cos(e), math.sin(e)]
        distance = max(100, diameter*3)
        eye = [c+distance*d for c,d in zip(centre,direction)]
        folder = toolkit.run / 'mesh_observations'; folder.mkdir(exist_ok=True)
        prefix = folder / f'mesh_{len(list(folder.glob("mesh_*.json")))+1:03d}'
        picture, metadata = mesh().render(prefix, eye=eye, target=centre,
            width_m=width_m, height_m=height_m, width_px=1200, height_px=900,
            yaw_degrees=yaw_degrees, bounds=bounds)
        request = dict(azimuth_degrees=azimuth_degrees, elevation_degrees=elevation_degrees,
            yaw_degrees=yaw_degrees, target=target, width_m=width_m, height_m=height_m, bounds=bounds)
        result = {**metadata, 'observation': prefix.name,
                  'camera_request': request, 'remaining_seconds': toolkit.remaining_seconds()}
        # The geometry module's frozen JSON/buffers remain the measurement source.
        toolkit.log('view_mesh', {'observation': prefix.name, 'request': request,
                                 'mesh_sha256': toolkit.manifest['mesh_input']['sha256']})
        data = io.BytesIO(); picture.save(data, 'PNG')
        return [Image(data=data.getvalue(), format='png'), json.dumps(result)]

    @server.tool()
    def measure_mesh_pixels(observation: str, pixels: list[list[int]]) -> dict:
        """Read visible original-mesh surface XYZ at pixels of a saved mesh view.
        Integer pixels refer to the returned 1200x900 image, origin upper left.
        Background has no geometry. Two surface points also return their distance;
        texture marks still require your interpretation, and noisy mesh is not BIM truth.
        """
        result = mesh().pixel_query(observation_path(observation), pixels)
        toolkit.log('measure_mesh_pixels', {'observation': observation, 'pixels': pixels, 'result': result})
        return result

    @server.tool()
    def view_mesh_observation(observation: str):
        """Reopen the exact saved original-mesh rendering and camera metadata."""
        mesh()  # Verify original-asset identity even when reopening a view.
        prefix = observation_path(observation)
        metadata = json.loads(prefix.with_suffix('.json').read_text())
        with PILImage.open(prefix.with_suffix('.png')) as picture:
            data = io.BytesIO(); picture.save(data, 'PNG')
        return [Image(data=data.getvalue(), format='png'), json.dumps(metadata)]
