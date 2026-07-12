# -*- coding: utf-8 -*-
# 世界樹 -YGGDRASIL- Blenderレンダリング v2（連続チューブ・樹皮バンプ・発光葉）
import bpy, json, math, os, sys
from mathutils import Vector
from collections import defaultdict

BASE = r"C:/Users/suzuk/AppData/Local/Temp/claude/C--Users-suzuk-OneDrive-00-Claude-Code/98289cd8-481c-406c-8216-3b2290036002/scratchpad"
GEO  = os.path.join(BASE, "sekaiju_geo.json")
ARGS = [a for a in sys.argv[sys.argv.index("--")+1:]] if "--" in sys.argv else []
FINAL = "final" in ARGS
VAR = "gold"
for a in ARGS:
    if a.startswith("var="): VAR = a.split("=",1)[1]
OUT  = os.path.join(BASE, f"sekaiju_{VAR}_" + ("final.png" if FINAL else "draft.png"))
S = 0.01

with open(GEO, encoding="utf-8") as f:
    geo = json.load(f)

def hex2rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i+2],16)/255.0 for i in (0,2,4))

def co(p):
    return (p[0]*S, p[2]*S, p[1]*S)

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()
for block in (bpy.data.meshes, bpy.data.curves, bpy.data.materials, bpy.data.lights, bpy.data.cameras):
    for x in list(block):
        try: block.remove(x)
        except Exception: pass

# --- マテリアル ---
def mat(name, color, metallic=0.0, rough=0.5, emit=None, emit_str=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*color, 1)
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Roughness"].default_value = rough
    if emit is not None:
        try:
            bsdf.inputs["Emission Color"].default_value = (*emit, 1)
            bsdf.inputs["Emission Strength"].default_value = emit_str
        except Exception: pass
    return m

def add_bark(mtl, scale=7.0, strength=0.4):
    nt=mtl.node_tree; bsdf=nt.nodes["Principled BSDF"]
    tex=nt.nodes.new("ShaderNodeTexNoise")
    tex.inputs["Scale"].default_value=scale
    try: tex.inputs["Detail"].default_value=9
    except Exception: pass
    bump=nt.nodes.new("ShaderNodeBump"); bump.inputs["Strength"].default_value=strength
    nt.links.new(tex.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])

GOLD   = hex2rgb("#c9a961"); GOLD_L = hex2rgb("#e8c977"); BARK = hex2rgb("#57431f")
m_trunk  = mat("trunk", GOLD, metallic=0.88, rough=0.33); add_bark(m_trunk, 6.5, 0.5)
m_bough  = mat("bough", hex2rgb("#b8933f"), metallic=0.82, rough=0.36); add_bark(m_bough, 10, 0.3)
m_root   = mat("root", BARK, metallic=0.3, rough=0.55); add_bark(m_root, 8, 0.55)
m_spiral = mat("spiral", GOLD_L, metallic=0.9, rough=0.22, emit=GOLD_L, emit_str=0.6)
m_fruitG = mat("fruitG", GOLD_L, metallic=0.9, rough=0.18, emit=GOLD_L, emit_str=1.2)
m_fruitB = mat("fruitB", hex2rgb("#3a2c16"), metallic=0.1, rough=0.7)
m_ground = mat("ground", (0.015,0.013,0.010), metallic=0.2, rough=0.55)
CLM=[]; CLM_LEAF=[]
for i,cx in enumerate(geo["clusterColors"]):
    c = hex2rgb(cx)
    CLM.append(mat(f"cl{i}", c, metallic=0.15, rough=0.45, emit=c, emit_str=0.6))
    CLM_LEAF.append(mat(f"leaf{i}", tuple(x*0.9 for x in c), metallic=0.1, rough=0.4, emit=c, emit_str=5.0))

# --- 連続チューブ結合（分割チューブの継ぎ目を消す） ---
def kfn(p): return (round(p[0],3), round(p[1],3), round(p[2],3))
def build_chains(elist):
    unused=set(range(len(elist)))
    start_map=defaultdict(list)
    bcount=defaultdict(int)
    for i,e in enumerate(elist):
        start_map[kfn(e["a"])].append(i)
        bcount[kfn(e["b"])]+=1
    chains=[]
    def walk(i0):
        chain=[i0]; unused.discard(i0); cur=elist[i0]
        while True:
            cands=[j for j in start_map[kfn(cur["b"])] if j in unused]
            if not cands: break
            cands.sort(key=lambda j: 0 if elist[j]["k"]==cur["k"] else 1)
            j=cands[0]; unused.discard(j); chain.append(j); cur=elist[j]
        return chain
    for i,e in enumerate(elist):
        if i in unused and bcount.get(kfn(e["a"]),0)==0:
            chains.append(walk(i))
    while unused:
        chains.append(walk(next(iter(unused))))
    return chains

def curve_obj(name, material, res=6):
    cu = bpy.data.curves.new(name, 'CURVE')
    cu.dimensions='3D'; cu.bevel_depth=1.0; cu.bevel_resolution=res
    cu.use_fill_caps=True
    ob = bpy.data.objects.new(name, cu)
    bpy.context.collection.objects.link(ob)
    if material: cu.materials.append(material)
    return cu

def add_chains(cu, elist):
    for chain in build_chains(elist):
        pts=[]; radii=[]
        e0=elist[chain[0]]
        pts.append(co(e0["a"])); radii.append(e0["wA"]*S)
        for idx in chain:
            e=elist[idx]
            pts.append(co(e["b"])); radii.append(e["wB"]*S)
        sp=cu.splines.new('POLY'); sp.points.add(len(pts)-1)
        for i,(p,r) in enumerate(zip(pts,radii)):
            sp.points[i].co=(*p,1); sp.points[i].radius=r

groups=defaultdict(list)
for e in geo["edges"]:
    k=e["k"]
    if k=="trunk": groups["trunk"].append(e)
    elif k=="bough": groups["bough"].append(e)
    elif k in ("root0","rootclaw","root1"): groups["rootmain"].append(e)
    elif k in ("root2","root3"): groups[f"rootf{e['ci']}"].append(e)
    elif k in ("twig","fstem"): groups["twig"].append(e)

add_chains(curve_obj("trunkC", m_trunk, 10), groups["trunk"])
add_chains(curve_obj("boughC", m_bough, 7), groups["bough"])
add_chains(curve_obj("rootC",  m_root, 6), groups["rootmain"])
add_chains(curve_obj("twigC",  m_bough, 4), groups["twig"])
for i in range(7):
    mm=mat(f"rootf{i}", tuple(0.55*a+0.45*b for a,b in zip(hex2rgb(geo["clusterColors"][i]), BARK)), rough=0.5)
    add_chains(curve_obj(f"rootFine{i}", mm, 4), groups[f"rootf{i}"])

# --- 渦巻き ---
cu_sp = curve_obj("spirals", m_spiral, 4)
for spd in geo["spirals"]:
    tip=Vector(co(spd["t"])); frm=Vector(co(spd["f"]))
    d=(tip-frm)
    if d.length<1e-6: continue
    d.normalize()
    up=Vector((0,0,1)); n=d.cross(up)
    if n.length<1e-4: n=Vector((1,0,0))
    n.normalize()
    e1=d; e2=n.cross(d).normalized()
    flip=1 if spd["ccw"] else -1
    R=spd["s"]*S*1.7
    spl=cu_sp.splines.new('POLY')
    pts=[]
    for i in range(49):
        th=i/48*4.2*math.pi
        r=math.exp(-0.20*th)
        w=tip + e1*(math.cos(th)*r*R) + e2*(math.sin(th)*r*flip*R)
        pts.append(w)
    spl.points.add(len(pts)-1)
    for i,w in enumerate(pts):
        spl.points[i].co=(w.x,w.y,w.z,1)
        spl.points[i].radius=0.6*S*(1.0-0.4*i/48)

# --- 葉 ---
import bmesh
def leaf_mesh(name):
    me=bpy.data.meshes.new(name)
    bm=bmesh.new()
    segs=10; L=1.0; Wd=0.36
    top=[]; bot=[]
    for i in range(segs+1):
        t=i/segs
        wdt=Wd*math.sin(math.pi*min(1,t*1.05))*(1-0.25*t)
        top.append(bm.verts.new((t*L,  wdt, 0.03*math.sin(math.pi*t))))
    for i in range(segs+1):
        t=i/segs
        wdt=Wd*math.sin(math.pi*min(1,t*1.05))*(1-0.25*t)
        bot.append(bm.verts.new((t*L, -wdt, 0.03*math.sin(math.pi*t))))
    for i in range(segs):
        try: bm.faces.new((top[i],top[i+1],bot[i+1],bot[i]))
        except Exception: pass
    bm.to_mesh(me); bm.free()
    return me

leaf_templates=[leaf_mesh(f"leafme{i}") for i in range(7)]
for i,me in enumerate(leaf_templates): me.materials.append(CLM_LEAF[i])

for lf in geo["leaves"]:
    ob=bpy.data.objects.new("leaf", leaf_templates[lf["ci"]])
    bpy.context.collection.objects.link(ob)
    p=Vector(co(lf["p"]))
    d=Vector((lf["d"][0]*S, lf["d"][2]*S, lf["d"][1]*S))
    if d.length<1e-6: d=Vector((1,0,0))
    d.normalize()
    ob.location=p
    ob.rotation_euler=d.to_track_quat('X','Z').to_euler()
    ln=0.27*lf["m"]
    ob.scale=(ln, ln, ln)

# --- 根の玉・果実 ---
def ball(p, r, material):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=r, location=co(p), segments=16, ring_count=8)
    ob=bpy.context.active_object
    ob.data.materials.append(material)
    return ob

for b in geo["balls"]:
    ci=b.get("ci",0) or 0
    ball(b["p"], max(0.8,b["r"])*S*1.15, CLM[ci])
for fr in geo["fruits"]:
    ball(fr["p"], fr["r"]*S*1.3, m_fruitG if fr["good"] else m_fruitB)

# --- 地面 ---
bpy.ops.mesh.primitive_circle_add(vertices=96, radius=9.5, fill_type='NGON', location=(0,0,0))
gnd=bpy.context.active_object; gnd.data.materials.append(m_ground)

# --- 星空ワールド ---
w=bpy.context.scene.world or bpy.data.worlds.new("W")
bpy.context.scene.world=w
w.use_nodes=True
nt=w.node_tree; nt.nodes.clear()
out=nt.nodes.new("ShaderNodeOutputWorld")
bg =nt.nodes.new("ShaderNodeBackground")
mixs=nt.nodes.new("ShaderNodeMixRGB"); mixs.blend_type='ADD'; mixs.inputs[0].default_value=1.0
noise=nt.nodes.new("ShaderNodeTexNoise"); noise.inputs["Scale"].default_value=900.0
ramp=nt.nodes.new("ShaderNodeValToRGB")
ramp.color_ramp.elements[0].position=0.74; ramp.color_ramp.elements[0].color=(0,0,0,1)
ramp.color_ramp.elements[1].position=0.80; ramp.color_ramp.elements[1].color=(1.0,0.95,0.8,1)
grad=nt.nodes.new("ShaderNodeRGB"); grad.outputs[0].default_value=(0.010,0.012,0.028,1)
nt.links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
nt.links.new(ramp.outputs["Color"], mixs.inputs[2])
nt.links.new(grad.outputs[0], mixs.inputs[1])
nt.links.new(mixs.outputs[0], bg.inputs["Color"])
bg.inputs["Strength"].default_value=1.0
nt.links.new(bg.outputs[0], out.inputs[0])

# --- ライティング ---
def light(name, type, loc, energy, color=(1,1,1), size=5):
    li=bpy.data.lights.new(name,type); li.energy=energy; li.color=color
    if type=='AREA': li.size=size
    ob=bpy.data.objects.new(name,li); ob.location=loc
    bpy.context.collection.objects.link(ob)
    return ob

def aim(ob, z=2.3):
    tgt=bpy.data.objects.new("t_"+ob.name,None); tgt.location=(0,0,z)
    bpy.context.collection.objects.link(tgt)
    c=ob.constraints.new('TRACK_TO'); c.target=tgt
    c.track_axis='TRACK_NEGATIVE_Z'; c.up_axis='UP_Y'

key = light("key",'AREA',(8,-7,8), 3200, (1.0,0.9,0.72), 7);  aim(key)
rim = light("rim",'AREA',(-8,8,5.5), 2200, (0.55,0.7,1.0), 9); aim(rim)
fil = light("fill",'AREA',(1,-10,1.6), 650, (0.9,0.9,1.0), 12); aim(fil)

# --- カメラ ---
cam=bpy.data.cameras.new("cam"); cam.lens=38
camo=bpy.data.objects.new("cam",cam); camo.location=(9.8,-8.6,3.4)
bpy.context.collection.objects.link(camo)
tgt=bpy.data.objects.new("target",None); tgt.location=(0,0,2.5)
bpy.context.collection.objects.link(tgt)
cc=camo.constraints.new('TRACK_TO'); cc.target=tgt
cc.track_axis='TRACK_NEGATIVE_Z'; cc.up_axis='UP_Y'
bpy.context.scene.camera=camo

# --- 質感バリアント ---
import random
random.seed(7)
def bsdf_of(m): return m.node_tree.nodes["Principled BSDF"]

if VAR=="mix":
    # A+B: クリムトの温かい黄金の樹 × 神秘の発光（クラスター色を保つ強さ）＋蛍
    nt=m_trunk.node_tree; b=bsdf_of(m_trunk)
    vor=nt.nodes.new("ShaderNodeTexVoronoi"); vor.inputs["Scale"].default_value=16.0
    mix=nt.nodes.new("ShaderNodeMixRGB"); mix.blend_type='MIX'
    mix.inputs[1].default_value=(*hex2rgb("#d9b76a"),1)
    mix.inputs[2].default_value=(*hex2rgb("#8a6f2a"),1)
    nt.links.new(vor.outputs["Color"], mix.inputs[0])
    nt.links.new(mix.outputs[0], b.inputs["Base Color"])
    b.inputs["Metallic"].default_value=0.80; b.inputs["Roughness"].default_value=0.30
    for i,m in enumerate(CLM_LEAF):
        bb=bsdf_of(m); c=hex2rgb(geo["clusterColors"][i])
        bb.inputs["Base Color"].default_value=(*[x*0.85 for x in c],1)
        bb.inputs["Metallic"].default_value=0.15; bb.inputs["Roughness"].default_value=0.3
        bb.inputs["Emission Color"].default_value=(*c,1)
        bb.inputs["Emission Strength"].default_value=2.2
    bsdf_of(m_spiral).inputs["Emission Strength"].default_value=1.2
    bsdf_of(m_fruitG).inputs["Emission Strength"].default_value=1.8
    key.data.energy=3400; key.data.color=(1.0,0.89,0.66)
    rim.data.energy=2300; rim.data.color=(0.58,0.7,1.0)
    fil.data.energy=300
    grad.outputs[0].default_value=(0.007,0.009,0.022,1)
    m_fly=mat("fly", GOLD_L, emit=GOLD_L, emit_str=16)
    for i in range(60):
        a=random.random()*6.28; r=1.2+random.random()*3.6; z=1.6+random.random()*2.8
        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.012+random.random()*0.014,
            location=(math.cos(a)*r, math.sin(a)*r, z), segments=8, ring_count=4)
        bpy.context.active_object.data.materials.append(m_fly)
elif VAR=="klimt":
    # クリムト装飾: モザイク金の幹・七宝(エナメル)の葉・温かい金光
    nt=m_trunk.node_tree; b=bsdf_of(m_trunk)
    vor=nt.nodes.new("ShaderNodeTexVoronoi"); vor.inputs["Scale"].default_value=16.0
    mix=nt.nodes.new("ShaderNodeMixRGB"); mix.blend_type='MIX'
    mix.inputs[1].default_value=(*hex2rgb("#d9b76a"),1)
    mix.inputs[2].default_value=(*hex2rgb("#8a6f2a"),1)
    nt.links.new(vor.outputs["Color"], mix.inputs[0])
    nt.links.new(mix.outputs[0], b.inputs["Base Color"])
    b.inputs["Metallic"].default_value=0.78; b.inputs["Roughness"].default_value=0.28
    for i,m in enumerate(CLM_LEAF):
        bb=bsdf_of(m); c=hex2rgb(geo["clusterColors"][i])
        bb.inputs["Base Color"].default_value=(*c,1)
        bb.inputs["Metallic"].default_value=0.45; bb.inputs["Roughness"].default_value=0.12
        bb.inputs["Emission Strength"].default_value=1.1
    key.data.energy=4200; key.data.color=(1.0,0.88,0.62)
    rim.data.energy=2400; rim.data.color=(1.0,0.8,0.55)
    fil.data.energy=350
    grad.outputs[0].default_value=(0.020,0.014,0.008,1)
elif VAR=="mystic":
    # 神秘発光: 闇に浮かぶ樹・強発光の葉と渦・蛍
    b=bsdf_of(m_trunk); b.inputs["Base Color"].default_value=(*hex2rgb("#8a6f2a"),1)
    b.inputs["Roughness"].default_value=0.42
    for m in CLM_LEAF:
        bb=bsdf_of(m); bb.inputs["Emission Strength"].default_value=9.0
    bsdf_of(m_spiral).inputs["Emission Strength"].default_value=2.2
    bsdf_of(m_fruitG).inputs["Emission Strength"].default_value=3.0
    key.data.energy=700;  key.data.color=(0.72,0.8,1.0)
    rim.data.energy=3200; rim.data.color=(0.5,0.65,1.0)
    fil.data.energy=120
    grad.outputs[0].default_value=(0.003,0.005,0.016,1)
    m_fly=mat("fly", GOLD_L, emit=GOLD_L, emit_str=30)
    for i in range(60):
        a=random.random()*6.28; r=1.2+random.random()*3.6; z=1.6+random.random()*2.8
        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.012+random.random()*0.014,
            location=(math.cos(a)*r, math.sin(a)*r, z), segments=8, ring_count=4)
        bpy.context.active_object.data.materials.append(m_fly)
elif VAR=="real":
    # 写実: 本物の樹皮(深いバンプ・非金属)＋金は渦と葉の差し色に
    for m,colr in ((m_trunk,"#5a4326"),(m_bough,"#6b5230"),(m_root,"#4a3820")):
        b=bsdf_of(m)
        b.inputs["Base Color"].default_value=(*hex2rgb(colr),1)
        b.inputs["Metallic"].default_value=0.04; b.inputs["Roughness"].default_value=0.78
        for n in m.node_tree.nodes:
            if n.type=='BUMP': n.inputs["Strength"].default_value=0.95
            if n.type=='TEX_NOISE': n.inputs["Scale"].default_value=15.0
    for m in CLM_LEAF:
        bb=bsdf_of(m); bb.inputs["Metallic"].default_value=0.0
        bb.inputs["Roughness"].default_value=0.5
        bb.inputs["Emission Strength"].default_value=1.0
    sun=bpy.data.lights.new("sun",'SUN'); sun.energy=4.0; sun.color=(1.0,0.85,0.65); sun.angle=math.radians(3)
    so=bpy.data.objects.new("sun",sun); so.rotation_euler=(math.radians(55),0,math.radians(140))
    bpy.context.collection.objects.link(so)
    key.data.energy=900; rim.data.energy=1400; rim.data.color=(0.6,0.7,1.0); fil.data.energy=250
    grad.outputs[0].default_value=(0.012,0.010,0.018,1)

# --- レンダ ---
sc=bpy.context.scene
sc.render.engine='CYCLES'
sc.cycles.samples = 192 if FINAL else 48
try: sc.cycles.use_denoising=True
except Exception: pass
sc.render.resolution_x = 1920 if FINAL else 1100
sc.render.resolution_y = 1080 if FINAL else 620
sc.render.filepath=OUT
bpy.ops.render.render(write_still=True)
print("RENDER_DONE:", OUT)
