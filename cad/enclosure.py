"""AI Cube prototype CSG. Units mm. Run: python cad/enclosure.py.

X right, Y rear, Z up. STL print orientations differ from assembly coordinates.
Purchased component envelopes are clearance references, not printable parts.
"""
from pathlib import Path
import sys, json
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'vendor'))
import manifold3d as m
import numpy as np
import trimesh
from PIL import Image, ImageDraw, ImageFont

W,D,H = 82.,78.,82.
WALL, TOP, MEMBRANE = 2.,2.,1.
LCD_W,LCD_H = 45.,31.
LCD_X,LCD_Z = 0.,48. # Measure active-area offset from PCB centre before print.
LCD_WINDOW = 25.4
SPEAKER_FACE,SPEAKER_DEPTH = 40.,20.
FIT = .4
PI_HOLES = (58.,23.)
# Unknown supplier holes deliberately unused: edge cradles + nylon ties.
M3_CLEAR, M3_NUT_AF = 3.4,5.8
M25_PILOT = 2.2 # Ream/tap for nylon M2.5; do NOT force threads into printed holes.

def box(x,y,z,at=(0,0,0)):
    return m.Manifold.cube((x,y,z)).translate(at)
def cyl(r,h,at=(0,0,0),axis='z',segments=48):
    s=m.Manifold.cylinder(h,r,circular_segments=segments)
    if axis=='x': s=s.rotate((0,90,0))
    if axis=='y': s=s.rotate((-90,0,0))
    return s.translate(at)
def rounded(w,d,h,r,z):
    s=cyl(r,h,(-w/2+r,-d/2+r,z))
    for x,y in [(w/2-r,-d/2+r),(w/2-r,d/2-r),(-w/2+r,d/2-r)]:
        s=s+cyl(r,h,(x,y,z))
    return s.hull()
def mesh(s):
    a=s.to_mesh()
    return trimesh.Trimesh(vertices=np.asarray(a.vert_properties)[:,:3],faces=np.asarray(a.tri_verts),process=True)

def build():
    shell=rounded(W,D,H-3.2,6,3.2)-rounded(W-4,D-4,H-TOP+1,4,-1)
    # Entire exterior top stays solid and unmarked. Local 37x37 recess leaves 1mm.
    shell=shell-box(37,37,1.1,(-18.5,-21.5,H-2.1))
    shell=shell-box(LCD_WINDOW,8,LCD_WINDOW,(LCD_X-LCD_WINDOW/2,-42,LCD_Z-LCD_WINDOW/2))
    # Rear generic power/service opening: soft grommet and separate strain relief.
    shell=shell-box(20,8,9,(-10,35,6))
    # Microphone front grille, lower left, not beside loudspeaker.
    for x in [-23,-19,-15]:
        for z in [13,17,21]: shell=shell-cyl(.8,7,(x,-42,z),'y',24)
    # Speaker right grille within 34mm face; vertical slits bridge only 2.2mm.
    for y in range(-14,15,4): shell=shell-box(8,2.2,28,(36,y-1.1,31))
    # Rear convection slots, above Pi.
    for x in range(-24,25,8): shell=shell-box(3,8,13,(x-1.5,35,52))
    # Four captive-nut bosses fuse into front/rear walls.
    base=rounded(W,D,3,6,0)
    for x in [-33,33]:
        for y in [-32,32]:
            shell=shell+box(10,10,9,(x-5,y-5,3.2))
            shell=shell-cyl(M3_CLEAR/2,15,(x,y,0))
            shell=shell-cyl(M3_NUT_AF/1.732,4,(x,y,9.2),segments=6)
            base=base-cyl(M3_CLEAR/2,5,(x,y,-1))
    # LCD edge cradle, accessible from open bottom, no active-glass adhesive.
    for x in [-25.5,22.9]:
        shell=shell+box(2.6,8,35,(x,-37,30.5))
        for z in [34,60]: shell=shell-box(5,3,2,(x-1,-33.5,z))
    shell=shell+box(51,6,2,(-25.5,-37,30.5))
    # Speaker square U cradle, 40.8mm clear, 20.8mm depth.
    shell=shell+box(23,44.8,2,(16,-22.4,22.6))
    for y in [-22.4,20.4]:
        shell=shell+box(23,2,43,(16,y,22.6))
        # Two straps routed behind magnet, with padded edge contact only.
        for z in [28,59]: shell=shell-box(4,5,2,(18,y-1,z))
    # Sensor cradle on upper left wall. PCB vertical (Y28 x Z20), short lead to top.
    shell=shell+box(7,32,2,(-39,-16,53))
    for y in [-16,14]:
        shell=shell+box(7,2,24,(-39,y,53))
        shell=shell-box(3,4,2,(-36,y-1,70))
    # Pi rear vertical plate + four M2.5 standoffs, board X65 x Z30.
    base=base+box(68,2,47,(-34,28,2))
    # Broad wire window retains frame and hole bosses.
    base=base-box(46,5,14,(-23,27,17))
    for x in [-PI_HOLES[0]/2,PI_HOLES[0]/2]:
        for z in [19.5,19.5+PI_HOLES[1]]:
            base=base+cyl(3,4,(x,24,z),'y')
            base=base-cyl(M25_PILOT/2,7,(x,23,z),'y')
    for x in [-39,28]: base=base-box(11,6,13,(x,26,3))
    # Mic floor tray (22.2x18.3) with low lip and ties through floor.
    base=base+box(26,22,2,(-28,-34,2.8))
    for x in [-28,-3.8]: base=base+box(1.8,22,3,(x,-34,4))
    for x in [-26,-5]: base=base-box(2,4,8,(x,-25,-1))
    # Amp floor tray (19.4x17.8), 12mm terminal clearance above board.
    base=base+box(24,22,2,(-12,-4,2.8))
    for x in [-12,10.2]: base=base+box(1.8,22,3,(x,-4,4))
    for x in [-10,8]: base=base-box(2,4,8,(x,5,-1))
    # Cable strain-relief tie holes adjacent rear service opening.
    for x in [-7,5]: base=base-box(2,4,5,(x,31,-1))
    return shell,base

def render(items,path,title,az=-48,el=25):
    """Orthographic shaded raster of actual exported mesh triangles (no AI artwork)."""
    az,el=np.radians([az,el])
    cam=np.array([np.cos(el)*np.sin(az),-np.cos(el)*np.cos(az),np.sin(el)])
    right=np.cross([0,0,1],cam); right/=np.linalg.norm(right)
    up=np.cross(cam,right)
    R=np.array([right,up,cam]).T
    polygons=[]; allp=[]
    light=np.array([-.4,-.5,.8]); light/=np.linalg.norm(light)
    for tm,color,shift in items:
        v=(tm.vertices+shift)@R; allp.append(v)
        for f,n in zip(tm.faces,tm.face_normals):
            if n@cam<=0: continue
            shade=.48+.52*max(0,n@light)
            polygons.append((v[f,2].mean(),v[f,:],tuple(int(c*shade) for c in color)))
    pts=np.vstack(allp); lo=pts[:,:2].min(0); hi=pts[:,:2].max(0)
    scale=min(1060/(hi[0]-lo[0]),800/(hi[1]-lo[1]))
    center=(lo+hi)/2
    im=Image.new('RGB',(1280,1024),'#edf1f5'); dr=ImageDraw.Draw(im)
    pixels=np.array(im); depth=np.full((1024,1280),-np.inf)
    for _,v,c in polygons:
        p=(v[:,:2]-center)*[scale,-scale]+[640,540]
        xmin,ymin=np.maximum(np.floor(p.min(0)).astype(int),[0,0])
        xmax,ymax=np.minimum(np.ceil(p.max(0)).astype(int),[1279,1023])
        if xmax<xmin or ymax<ymin: continue
        yy,xx=np.mgrid[ymin:ymax+1,xmin:xmax+1]; xx=xx+.5; yy=yy+.5
        (ax,ay),(bx,by),(cx,cy)=p
        den=(by-cy)*(ax-cx)+(cx-bx)*(ay-cy)
        if abs(den)<1e-9: continue
        a=((by-cy)*(xx-cx)+(cx-bx)*(yy-cy))/den
        b=((cy-ay)*(xx-cx)+(ax-cx)*(yy-cy))/den; cc=1-a-b
        z=a*v[0,2]+b*v[1,2]+cc*v[2,2]
        region=depth[ymin:ymax+1,xmin:xmax+1]
        mask=(a>=-1e-7)&(b>=-1e-7)&(cc>=-1e-7)&(z>region)
        region[mask]=z[mask]; pixels[ymin:ymax+1,xmin:xmax+1][mask]=c
    im=Image.fromarray(pixels); dr=ImageDraw.Draw(im)
    try: font=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',28)
    except OSError: font=ImageFont.load_default()
    dr.text((45,25),title,fill='#172c45',font=font)
    dr.text((45,975),'AI CUBE / 82 x 78 x 82 mm / physical dry-fit required',fill='#40516b',font=font)
    im.save(path)

def main():
    out=ROOT/'stl'; out.mkdir(exist_ok=True)
    previews=ROOT/'renders'; previews.mkdir(exist_ok=True)
    shell,base=build(); sm,bm=mesh(shell),mesh(base)
    report={}
    # Invert shell for printing: unmarked top directly on bed, open end upward.
    sp=sm.copy(); sp.apply_transform(trimesh.transformations.rotation_matrix(np.pi,[1,0,0])); sp.apply_translation([0,0,H])
    for name,tm in [('shell',sp),('base',bm)]:
        dest=out/(name+'.stl'); tm.export(dest)
        actual=trimesh.load_mesh(dest)
        parents=list(range(len(actual.vertices)))
        def find(a):
            while parents[a]!=a:
                parents[a]=parents[parents[a]]; a=parents[a]
            return a
        for a,b,c in actual.faces:
            parents[find(b)]=find(a); parents[find(c)]=find(a)
        pieces=set(find(i) for i in range(len(parents)))
        assert actual.is_watertight and actual.is_winding_consistent and actual.volume>0 and len(pieces)==1, name
        report[name]={'watertight':bool(actual.is_watertight),'consistent_winding':bool(actual.is_winding_consistent),'connected_bodies':len(pieces),'volume_mm3':round(float(actual.volume),2),'triangles':len(actual.faces),'bounds_mm':actual.bounds.round(3).tolist()}
    # The two printed parts must not intersect in assembled coordinates.
    overlap=(shell^base).volume()
    assert overlap<.001, overlap
    report['assembly_overlap_mm3']=overlap
    # Clearance-only reference bodies; board details and connectors not modelled.
    references=[('LCD',box(45,3,31,(-22.5,-35,32.5)),(39,86,107)),
      ('Pi Zero 2 W',box(65,1.6,30,(-32.5,22.4,16)),(38,130,95)),
      ('speaker',box(20,40,40,(19,-20,24.6)),(54,63,74)),
      ('USB microphone',box(22.2,18.3,7,(-26,-32.5,5)),(128,69,158)),
      ('MAX98357A',box(19.4,17.8,12,(-9.7,-1.9,5)),(63,114,171)),
      ('QT1010',box(2,28,20,(-37,-14,55)),(145,104,163)),
      ('electrode',box(35,35,.08,(-17.5,-20.5,80.92)),(215,145,70))]
    # Reserved connector/turn corridors, measured against print geometry and parts.
    # Pi USB edge at top, USB sockets on LEFT; route cable forward then down.
    corridors=[('Pi USB connector and turn',box(38,20,24,(-30,3,46))),
               ('LCD PH2 side lead',box(8,12,16,(-33,-29,40)))]
    report['cable_corridor_material_overlap_mm3']={n:round(((s^shell)+(s^base)).volume(),5) for n,s in corridors}
    report['cable_corridor_component_overlap_mm3']={n:round(sum((s^r).volume() for _,r,_ in references),5) for n,s in corridors}
    assert all(v<.001 for v in report['cable_corridor_material_overlap_mm3'].values())
    assert all(v<.001 for v in report['cable_corridor_component_overlap_mm3'].values())
    # Reference envelopes may touch cradles but must not penetrate print material.
    report['component_material_overlap_mm3']={n:round(((s^shell)+(s^base)).volume(),5) for n,s,_ in references}
    assert all(v<.001 for v in report['component_material_overlap_mm3'].values()),report
    report['component_pair_overlap_mm3']={}
    for i,(n,s,c) in enumerate(references):
        for n2,s2,c2 in references[i+1:]:
            vol=(s^s2).volume()
            if vol>.001: report['component_pair_overlap_mm3'][n+' / '+n2]=vol
    assert not report['component_pair_overlap_mm3']
    (ROOT/'validation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    render([(sm,(195,209,224),(0,0,0)),(bm,(86,111,145),(0,0,0))],previews/'assembly.png','Assembled enclosure / actual CAD mesh',az=46)
    render([(sm,(195,209,224),(0,0,35)),(bm,(86,111,145),(0,0,-20))]+[(mesh(s),c,(0,0,0)) for n,s,c in references],previews/'exploded.png','Exploded assembly / component clearance envelopes',az=-130,el=23)
    # Cutaway is a true Boolean section of the source CAD, not a print part.
    cut=mesh(shell-box(90,47,100,(-45,-45,0)))
    render([(cut,(195,209,224),(0,0,0)),(bm,(86,111,145),(0,0,0))]+[(mesh(s),c,(0,0,0)) for n,s,c in references],previews/'cutaway.png','Front cutaway / component placement',az=-35,el=24)
    render([(sp,(195,209,224),(-48,0,0)),(bm,(86,111,145),(48,0,0))],previews/'print-layout.png','Print orientation / shell top-down + base flat',az=25,el=40)
    print(json.dumps(report,indent=2))

if __name__=='__main__': main()
