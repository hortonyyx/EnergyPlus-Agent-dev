"""Round-trip sm_15 IDF through idfpy: load -> validate -> resave -> diff.

Includes a workaround for idfpy IDF parser case-sensitivity bug:
the parser does NOT normalize uppercase object type names to canonical
case, so we pre-process the IDF text first.

Usage: uv run python Tool_scripts/idfpy_roundtrip_sm15.py
"""

import re
from pathlib import Path
from idfpy import IDF
from idfpy.models import OBJECT_TYPE_REGISTRY

SRC = Path('test_data/SmallOffice/smalloffice_15/output/smalloffice_15.idf')
OUT_DIR = Path('test_data/SmallOffice/smalloffice_15/output')
FIXED_IDF = OUT_DIR / 'smalloffice_15_caseFixed.idf'
OUT_IDF = OUT_DIR / 'smalloffice_15_idfpy.idf'
OUT_EPJSON = OUT_DIR / 'smalloffice_15_idfpy.epjson'


def normalize_idf_case(src: Path, dst: Path) -> int:
    """Replace each uppercase object-type header with its canonical case."""
    upper_to_canon = {k.upper(): k for k in OBJECT_TYPE_REGISTRY.keys()}
    text = src.read_text(encoding='utf-8', errors='replace')

    def repl(m):
        upper_name = m.group(1).upper()
        canon = upper_to_canon.get(upper_name)
        return f'{canon},' if canon else m.group(0)

    pattern = re.compile(r'^([A-Z][A-Z0-9_:]*),\s*$', re.MULTILINE)
    new_text, n = pattern.subn(repl, text)
    dst.write_text(new_text, encoding='utf-8')
    return n


def main():
    print(f'[0] Normalize IDF case -> {FIXED_IDF.name}')
    n = normalize_idf_case(SRC, FIXED_IDF)
    print(f'    {n} object headers rewritten')

    print(f'\n[1] Loading {FIXED_IDF}')
    idf = IDF.load(FIXED_IDF)

    print('\n[2] Object counts by type:')
    counts = {}
    for type_name in sorted(idf._objects.keys()):
        m = len(idf._objects[type_name])
        if m:
            counts[type_name] = m
            print(f'    {type_name:50s} {m}')
    print(f'    TOTAL: {sum(counts.values())} objects across {len(counts)} types')

    print('\n[3] idf.validate():')
    errors = idf.validate()
    print(f'    {len(errors)} reference errors')
    if errors:
        print('    First 8:')
        for e in errors[:8]:
            print(f'      - {e}')

    print('\n[4] Geometry (sample 3 surfaces via mixin):')
    surf_dict = idf.all_of_type('BuildingSurface:Detailed')
    for name, s in list(surf_dict.items())[:3]:
        try:
            print(f'    {name}: area={s.area:.2f} m^2  normal={s.normal}')
        except Exception as ex:
            print(f'    {name}: (geom err: {ex})')

    print('\n[5] Forward navigation sanity:')
    surf_dict = idf.all_of_type('BuildingSurface:Detailed')
    if surf_dict:
        first_name, first_surf = next(iter(surf_dict.items()))
        try:
            zone_obj = first_surf.zone_name_ref
            print(f'    {first_name}.zone_name_ref -> {type(zone_obj).__name__ if zone_obj else None}')
            con_obj = first_surf.construction_name_ref
            print(f'    {first_name}.construction_name_ref -> {type(con_obj).__name__ if con_obj else None}')
        except AttributeError as ex:
            print(f'    (attr error: {ex})')

    print(f'\n[6] Save IDF -> {OUT_IDF.name}')
    idf.save(OUT_IDF)

    print(f'\n[7] Save epJSON -> {OUT_EPJSON.name}')
    idf.save(OUT_EPJSON, output_type='epjson')

    print('\n[8] Reload roundtrip:')
    idf2 = IDF.load(OUT_IDF)
    counts2 = {t: len(o) for t, o in idf2._objects.items() if o}
    print(f'    same total: {sum(counts.values())} -> {sum(counts2.values())}')
    print(f'    same types: {set(counts.keys()) == set(counts2.keys())}')

    print('\n[9] File sizes:')
    print(f'    src    : {SRC.stat().st_size:>8} bytes')
    print(f'    fixed  : {FIXED_IDF.stat().st_size:>8} bytes')
    print(f'    out idf: {OUT_IDF.stat().st_size:>8} bytes')
    print(f'    out json: {OUT_EPJSON.stat().st_size:>8} bytes')


if __name__ == '__main__':
    main()
