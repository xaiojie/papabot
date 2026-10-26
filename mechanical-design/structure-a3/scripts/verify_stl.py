"""Independently reread the exported binary STL, in millimetres, without Blender."""
import json, struct, math, hashlib, sys
from pathlib import Path
from collections import defaultdict, deque
OUT=Path(__file__).resolve().parents[1]
def sub(a,b):return tuple(x-y for x,y in zip(a,b))
def cross(a,b):return (a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])
def dot(a,b):return sum(x*y for x,y in zip(a,b))
results=[]
manifest_file=sys.argv[1] if len(sys.argv)>1 else 'export-manifest.json'
report_file=sys.argv[2] if len(sys.argv)>2 else 'stl-verification.json'
for item in json.loads((OUT/'reports'/manifest_file).read_text()):
    path=OUT/item['file'];raw=path.read_bytes();count=struct.unpack_from('<I',raw,80)[0]
    assert len(raw)==84+50*count
    indices={};verts=[];faces=[];volume=0;areas=[];edge_faces=defaultdict(list);directions=defaultdict(int)
    for i in range(count):
        rec=struct.unpack_from('<12fH',raw,84+i*50)
        tri=[tuple(rec[3+j*3:6+j*3]) for j in range(3)]
        f=[]
        for v in tri:
            key=tuple(round(x,5) for x in v)
            if key not in indices:indices[key]=len(verts);verts.append(v)
            f.append(indices[key])
        faces.append(tuple(f))
        cr=cross(sub(tri[1],tri[0]),sub(tri[2],tri[0]));areas.append(math.sqrt(dot(cr,cr))/2)
        volume+=dot(tri[0],cross(tri[1],tri[2]))/6
        for a,b in zip(f,f[1:]+f[:1]):
            key=tuple(sorted((a,b)));edge_faces[key].append(i);directions[key]+=1 if a<b else -1
    degenerate=sum(1 for f,area in zip(faces,areas) if len(set(f))<3 or area<1e-8)
    boundary=sum(len(v)==1 for v in edge_faces.values());nonmanifold=sum(len(v)!=2 for v in edge_faces.values())
    wrong_orientation=sum(v!=0 for v in directions.values())
    duplicates=len(faces)-len(set(tuple(sorted(f)) for f in faces))
    adj=defaultdict(set)
    for inc in edge_faces.values():
        for i in inc:
            adj[i].update(j for j in inc if i!=j)
    unseen=set(range(count));components=[]
    while unseen:
        todo=[unseen.pop()];comp=0
        while todo:
            i=todo.pop();comp+=1
            for j in adj[i]:
                if j in unseen:unseen.remove(j);todo.append(j)
        components.append(comp)
    lo=[min(v[i] for v in verts) for i in range(3)];hi=[max(v[i] for v in verts) for i in range(3)]
    dims=[hi[i]-lo[i] for i in range(3)]
    err=max(abs(a-b) for a,b in zip(dims,item['dimensions_mm']))
    result={'id':item['id'],'file':item['file'],'sha256':hashlib.sha256(raw).hexdigest(),'triangles':count,'welded_vertices_1e_5_mm':len(verts),'boundary_edges':boundary,'nonmanifold_edges':nonmanifold,'inconsistently_oriented_edges':wrong_orientation,'degenerate_triangles':degenerate,'duplicate_triangles':duplicates,'connected_shell_count':len(components),'volume_mm3':round(volume,5),'minimum_triangle_area_mm2':min(areas),'dimensions_mm':[round(x,5) for x in dims],'dimension_error_mm':err,'bottom_z_mm':lo[2]}
    result['pass']=nonmanifold==0 and wrong_orientation==0 and degenerate==0 and duplicates==0 and len(components)==1 and volume>0 and err<.01 and abs(lo[2])<.01
    results.append(result)
report={'checked_units':'mm','weld_tolerance_mm':1e-5,'mesh_check_pass':all(x['pass'] for x in results),'items':results,'limits':['No slicer or physical fit test has been performed.','Topology and duplicate-face checks do not prove all possible self-intersections absent.','No load-bearing or servo spline/mounting compatibility claim.']}
(OUT/'reports'/report_file).write_text(json.dumps(report,ensure_ascii=False,indent=2))
print(json.dumps(report,ensure_ascii=False,indent=2))
assert report['mesh_check_pass'],'STL validation failed'
