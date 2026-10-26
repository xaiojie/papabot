"""Convert the installed Chinese typeface to fixed, font-independent silk polygons."""
import json
from pathlib import Path
from fontTools.ttLib import TTCollection
from fontTools.pens.basePen import BasePen
from shapely.geometry import Polygon, LineString
from shapely.ops import split, unary_union
from shapely import affinity

ROOT = Path(__file__).resolve().parent
FONT = '/System/Library/Fonts/STHeiti Medium.ttc'

class FlatPen(BasePen):
    def __init__(self, glyphs):
        super().__init__(glyphs)
        self.contours = []
    def _moveTo(self, p): self.points = [p]
    def _lineTo(self, p): self.points.append(p)
    def _curveToOne(self, a, b, c):
        p = self.points[-1]
        for i in range(1, 17):
            t = i / 16
            self.points.append(tuple((1-t)**3*p[j]+3*(1-t)**2*t*a[j]+3*(1-t)*t*t*b[j]+t**3*c[j] for j in range(2)))
    def _qCurveToOne(self, a, b):
        p = self.points[-1]
        for i in range(1, 17):
            t = i / 16
            self.points.append(tuple((1-t)**2*p[j]+2*(1-t)*t*a[j]+t*t*b[j] for j in range(2)))
    def _closePath(self): self.contours.append(Polygon(self.points))
    def _endPath(self): self._closePath()

font = next(f for f in TTCollection(FONT).fonts if ord('爬') in f.getBestCmap())
glyphs = font.getGlyphSet()
pen = FlatPen(glyphs)
glyphs[font.getBestCmap()[ord('爬')]].draw(pen)
# TrueType's nested contours are combined with the even-odd fill rule.
shape = Polygon()
for p in pen.contours:
    shape = shape.symmetric_difference(p)
x0,y0,x1,y1 = shape.bounds
shape = affinity.translate(shape, -x0, -y0)
shape = affinity.scale(shape, xfact=2.96/(y1-y0), yfact=2.96/(y1-y0), origin=(0,0))
# A small weight increase aids 3 mm silkscreen legibility; final height is 3 mm.
shape = shape.buffer(0.02, join_style=1).simplify(0.002, preserve_topology=True)
x0,y0,x1,y1 = shape.bounds
shape = affinity.translate(shape,-x0,-y0)
width=x1-x0
label=unary_union([shape, affinity.translate(shape, width+0.35, 0)])
label=affinity.translate(label,18.8-(2*width+0.35)/2,29.3-(y1-y0)/2)

def no_holes(p):
    if not p.interiors:
        return [p]
    h=Polygon(p.interiors[0]).representative_point()
    a,b,c,d=p.bounds
    parts=split(p,LineString([(a-1,h.y),(c+1,h.y)]))
    assert len(parts.geoms)>1
    return [q for sub in parts.geoms for q in no_holes(sub)]

parts=[q for p in (label.geoms if hasattr(label,'geoms') else [label]) for q in no_holes(p)]
assert unary_union(parts).symmetric_difference(label).area < 1e-7
paths=[]
for p in parts:
    pts=[(round(x/25.4*1000,4), round(y/25.4*1000,4)) for x,y in p.exterior.coords]
    paths.append([*pts[0],'L',*[v for xy in pts[1:] for v in xy]])
data={'text':'爬爬','font_file':FONT,'font_family':font['name'].getDebugName(1),
      'bbox_mm':list(label.bounds),'area_mm2':label.area,'polygon_count':len(paths),
      'curve_samples':16,'simplification_tolerance_mm':0.002,'paths_mil':paths}
(ROOT/'chinese-outline.json').write_text(json.dumps(data,ensure_ascii=False,indent=2))
print({k:v for k,v in data.items() if k!='paths_mil'})
