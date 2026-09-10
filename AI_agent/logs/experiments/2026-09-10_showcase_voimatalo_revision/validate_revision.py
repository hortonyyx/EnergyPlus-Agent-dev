"""Check saved revision geometry, physical cuts, provenance and preserved files."""
import hashlib,json,re,subprocess,sys
from pathlib import Path
from urllib.parse import urlsplit,unquote
ROOT=Path(__file__).resolve().parents[4];sys.path.insert(0,str(ROOT))
from src.agent.geometry.source_model import _digest
LOG=Path(__file__).resolve().parent
ASSET=ROOT/'showcase/2026-09-11-research-report/demos/textured-mass'

def area(r):
    n=[0.,0.,0.]
    for a,b in zip(r,r[1:]+r[:1]):
        n[0]+=(a[1]-b[1])*(a[2]+b[2]);n[1]+=(a[2]-b[2])*(a[0]+b[0]);n[2]+=(a[0]-b[0])*(a[1]+b[1])
    return sum(x*x for x in n)**.5/2

def main():
    report={'variants':{},'preserved_files':{},'markdown_links':0}
    for variant in ['exterior','inferred']:
        s=json.loads((ASSET/'revision_02'/variant/'source_model.json').read_text())
        d=json.loads((ASSET/'revision_02'/variant/'display_geometry.json').read_text())
        old=json.loads((ASSET/variant/'source_model.json').read_text())
        assert s['source_model_sha256']==_digest({k:v for k,v in s.items() if k!='source_model_sha256'})
        assert s['validation']['status']=='pass'
        old_windows={w['id']:w for w in old['openings'] if w['kind']=='window'}
        windows={w['id']:w for w in s['openings'] if w['kind']=='window'}
        assert len(old_windows)==316 and len(windows)==322
        assert all(windows[k]['vertices']==v['vertices'] for k,v in old_windows.items())
        tower=next(x for x in s['spaces'] if x['id']=='TRAFFIC_merged')
        bounds={b['id']:b for b in s['boundaries']}
        tb=[b for b in s['boundaries'] if b['space_id']==tower['id']]
        assert tower['height']==27.6 and len([b for b in tb if b['geometry_type']!='wall'])==2
        assert all(b['enclosure']=='physical' and b['kind']!='virtual' for b in tb)
        doors=[o for o in s['openings'] if o['kind']=='door' and tower['id'] in o['space_ids']]
        assert len(doors)==8 and all(len(s['opening_hosts'][o['id']])==2 for o in doors)
        hosts={h for o in s['openings'] if tower['id'] in o['space_ids'] for h in s['opening_hosts'][o['id']]}
        cuts=[]
        for h in sorted(hosts):
            gross=area(bounds[h]['vertices'])
            shown=sum(area(p['verts'])-sum(area(r) for r in p.get('holes',[])) for p in d['display_surface_parts'][h])
            expected=sum(area(o['vertices']) for o in s['openings'] if h in s['opening_hosts'][o['id']])
            assert abs(gross-shown-expected)<1e-6,(h,gross,shown,expected)
            cuts.append({'host':h,'actual_cut_m2':gross-shown,'expected_opening_area_m2':expected})
        ends=[b for b in s['boundaries'] if b.get('completion_evidence')]
        assert ends and all(b['enclosure']=='physical' and b['assumptions'] for b in ends)
        report['variants'][variant]={'source_sha256':s['source_model_sha256'],'preserved_windows':316,'added_windows':6,'tower_doors':len(doors),'tower_intermediate_horizontal_faces':0,'inferred_end_faces':len(ends),'opening_cut_checks':cuts}
    preserved=['case_tests/textured_mass/single_buildings/voimatalo/input.glb',
        'showcase/2026-09-11-research-report/demos/sm25/sm25_showcase.html',
        'showcase/2026-09-11-research-report/demos/textured-mass/exterior/source_model.json',
        'showcase/2026-09-11-research-report/demos/textured-mass/inferred/source_model.json']
    for f in preserved:
        before=subprocess.check_output(['git','show','b6125c29:'+f],cwd=ROOT);after=(ROOT/f).read_bytes()
        assert before==after,f
        report['preserved_files'][f]=hashlib.sha256(after).hexdigest()
    product_changes=subprocess.check_output(['git','diff','--name-only','b6125c29','--','src','scripts','case_tests'],cwd=ROOT,text=True)
    assert not product_changes
    report['product_code_or_input_changes']=False
    selection=json.loads((ROOT/'case_tests/textured_mass/single_buildings/voimatalo/selection.json').read_text())
    parent=selection['source_tile']
    parent_sha=hashlib.sha256((ROOT/parent['sanitised_input_path']).read_bytes()).hexdigest()
    assert parent_sha==parent['sanitised_input_sha256']
    report['supplementary_parent_tile_sha256']=parent_sha
    for path in [LOG/'README.md',ASSET/'README.md',ROOT/'AI_agent/logs/worklog/2026-09-10_voimatalo_missing_faces.md']:
        for href in re.findall(r'\[[^\]]*\]\(([^)]+)\)',path.read_text()):
            url=urlsplit(href)
            if url.scheme or not url.path:continue
            assert (path.parent/unquote(url.path)).resolve().exists(),(path,href)
            report['markdown_links']+=1
    (LOG/'geometry_and_preservation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:{x:v for x,v in row.items() if x!='opening_cut_checks'} for k,row in report['variants'].items()},ensure_ascii=False))

if __name__=='__main__':main()
