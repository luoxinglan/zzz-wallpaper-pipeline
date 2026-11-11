# -*- coding: utf-8 -*-
"""v41 眼形光斑 v3：eyeflash.frag 采样 eyeglow.png + pupils 移到 depth 之前（视差跟随）

改动（每项目）：
1. shaders/effects/eyeflash.frag 重写：
   - g_Texture1 = materials/eyeglow.png（v39 烘焙：bg2 眼睛彩色像素形状，RGB=预乘眼色）
   - 形状/位置/颜色全部来自纹理；坐标滑块变为相对烘焙位置的偏移（默认=0）
   - out = base.rgb + glow.rgb * (v_Pulse*1.35 + 0.08)，保留 base.a（angleband 蒙版在后面要乘）
2. scene.json：bg1/2/3 效果链 pupils 移到 index 0（depth 之前）——光斑先画进内容再随 depth 位移
3. materials/effects/eyeflash.json 材质级 "textures": [null, "eyeglow"]
   【铁律：实例级 passes[0].textures 会覆盖输入帧缓冲槽位 -> g_Texture0 变白 -> 全屏洗白！只能材质级】
用法：python apply_v41.py [--all] [--proj 65]
"""
import json, os, sys, shutil, glob

TEMP = r"C:\Users\25485\.zcode\workspace\default\temp"
BASE = r"E:\Program Files (x86)\Steam\steamapps\common\wallpaper_engine\projects\myprojects"
RESULTS = os.path.join(TEMP, "pupilfix", "results")
BACKUP = os.path.join(TEMP, "we_v41_backup")

FRAG = r"""varying vec4 v_TexCoord;
varying float v_Pulse;

uniform sampler2D g_Texture0; // {{"hidden":true}}
uniform sampler2D g_Texture1; // {{"material":"eyeglow","mode":"rgbmask","default":"util/black"}}

uniform float g_GAx; // {{"material":"眼A水平(%)"}}
uniform float g_GAy; // {{"material":"眼A垂直(%)"}}
uniform float g_GBx; // {{"material":"眼B水平(%)"}}
uniform float g_GBy; // {{"material":"眼B垂直(%)"}}
uniform float g_Gr; // {{"material":"瞳孔半径(层高%)"}}

const vec2 g_A0 = vec2({ax:.2f}, {ay:.2f});
const vec2 g_B0 = vec2({bx:.2f}, {by:.2f});

void main() {{
	vec4 base = texSample2D(g_Texture0, v_TexCoord.xy);

	vec2 pc = v_TexCoord.xy * 100.0;
	float dA = length(vec2((pc.x - g_A0.x) * 1.8194, pc.y - g_A0.y));
	float dB = length(vec2((pc.x - g_B0.x) * 1.8194, pc.y - g_B0.y));
	vec2 offA = vec2(g_GAx - g_A0.x, g_GAy - g_A0.y) * 0.01;
	vec2 offB = vec2(g_GBx - g_B0.x, g_GBy - g_B0.y) * 0.01;
	vec2 uvg = v_TexCoord.xy - mix(offB, offA, step(dA, dB));

	vec4 glow = texSample2D(g_Texture1, uvg);
	vec3 outc = base.rgb + glow.rgb * (v_Pulse * 1.35 + 0.08);
	gl_FragColor = vec4(min(outc, vec3(1.0, 1.0, 1.0)), base.a);
}}
"""

def atomic_write(path, text):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    os.replace(tmp, path)

def apply_project(dirname):
    nn = int(dirname.split("_")[2])
    res = json.load(open(os.path.join(RESULTS, "%d.json" % nn), encoding="utf-8"))
    P = os.path.join(BASE, dirname)
    frag_path = os.path.join(P, "shaders", "effects", "eyeflash.frag")
    scene_path = os.path.join(P, "scene.json")
    glow_path = os.path.join(P, "materials", "eyeglow.png")
    tex_path = os.path.join(P, "materials", "eyeglow.tex")

    assert os.path.exists(glow_path), dirname + " 缺 eyeglow.png"
    assert not os.path.exists(tex_path), dirname + " 存在 eyeglow.tex 会遮蔽 png（先回收）"

    # 备份
    bdir = os.path.join(BACKUP, "%02d" % nn)
    os.makedirs(bdir, exist_ok=True)
    mat_path0 = os.path.join(P, "materials", "effects", "eyeflash.json")
    for src in (frag_path, scene_path, mat_path0):
        dst = os.path.join(bdir, os.path.basename(src).replace("eyeflash", "eyeflash_mat"))
        if not os.path.exists(dst):
            shutil.copy2(src, dst)

    # 1) frag
    frag = FRAG.format(ax=res["ax"], ay=res["ay"], bx=res["bx"], by=res["by"])
    atomic_write(frag_path, frag)

    # 1b) 材质级纹理绑定（唯一正确写法；实例级会覆盖 g_Texture0 导致白洗）
    mat_path = os.path.join(P, "materials", "effects", "eyeflash.json")
    mat = json.load(open(mat_path, encoding="utf-8"))
    mat["passes"][0]["textures"] = [None, "eyeglow"]
    atomic_write(mat_path, json.dumps(mat, ensure_ascii=False, indent="	"))

    # 2) scene.json
    scene = json.load(open(scene_path, encoding="utf-8"))
    touched = 0
    for o in scene["objects"]:
        if o.get("name") not in ("bg1", "bg2", "bg3"):
            continue
        effs = o.get("effects", [])
        pupils = [e for e in effs if e.get("name") == "pupils"]
        assert len(pupils) == 1, dirname + " " + o["name"] + " pupils!=1"
        p = pupils[0]
        p["passes"][0].pop("textures", None)  # 实例级绑定会白洗，只允许材质级
        rest = [e for e in effs if e is not p]
        o["effects"] = [p] + rest
        touched += 1
    assert touched == 3, dirname + " bg 层数 " + str(touched)
    atomic_write(scene_path, json.dumps(scene, ensure_ascii=False, indent="\t"))

    # 3) 回读校验
    chk = json.load(open(scene_path, encoding="utf-8"))
    for o in chk["objects"]:
        if o.get("name") in ("bg1", "bg2", "bg3"):
            names = [e.get("name") for e in o["effects"]]
            assert names[0] == "pupils" and names[1] == "depth", (dirname, names[:3])
            ppass = o["effects"][0]["passes"][0]
            assert "textures" not in ppass, (dirname, "实例级 textures 残留（白洗风险）")
    mat2 = json.load(open(os.path.join(P, "materials", "effects", "eyeflash.json"), encoding="utf-8"))
    assert mat2["passes"][0].get("textures") == [None, "eyeglow"], "材质级 textures 缺失"
    f2 = open(frag_path, encoding="utf-8").read()
    assert "g_Texture1" in f2 and "eyeglow" in f2 and "base.a" in f2
    return dirname

def main():
    dirs = sorted(d for d in os.listdir(BASE) if d.startswith("zzz_mindscape_"))
    if "--all" in sys.argv:
        targets = dirs
    else:
        nn = "65"
        for a in sys.argv:
            if a.startswith("--proj"):
                pass
        idx = [i for i, a in enumerate(sys.argv) if a == "--proj"]
        if idx:
            nn = sys.argv[idx[0] + 1]
        targets = [d for d in dirs if d.split("_")[2] == nn]
    assert targets, "no target"
    ok = 0
    for d in targets:
        try:
            apply_project(d)
            ok += 1
        except Exception as ex:
            print("FAIL", d, ex)
            raise
    print("v41 applied:", ok, "/", len(targets))

if __name__ == "__main__":
    main()
