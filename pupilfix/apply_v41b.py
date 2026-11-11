# -*- coding: utf-8 -*-
"""v41b 眼形光斑最终版：eyeglow POT 重烘焙 + 材质级纹理绑定 + frag 垫底补偿 + pupils 移到 depth 前

每项目改动：
1. materials/eyeglow.png：若非 2 的幂，垫到 POT 画布（内容置左上，黑色/透明垫底，不拉伸）
   【根因：WE 对效果材质直引的散装 png 按 next-POT 垫画布加载，采样 UV 0-1 横跨垫大后的画布，
     内容整体左上缩移（3446x1901 -> 4096x2048，横向 x0.84）——光斑"偏离眼睛约 10%"的真因】
2. shaders/effects/eyeflash.frag：采样 UV 乘垫底比 (W0/POT_W, H0/POT_H)，形状/位置/颜色全来自纹理；
   眼坐标常量 g_A0/g_B0 = results/NN.json（bg2 色斑基准，三层通用）
3. materials/effects/eyeflash.json：材质级 "textures": [null, "eyeglow"]
   【铁律：效果实例级 passes[0].textures 会顶掉输入帧缓冲槽位 -> g_Texture0 采样到白纹理 -> 全屏洗白】
4. scene.json：三层效果链 pupils 移到 index 0（depth 之前）——光斑先画进内容再随视差位移，结构性重合
5. 重启后回收检查：materials/eyeglow.tex 若存在会遮蔽 png（本脚本不删，需 recycle_delete.py）

用法：python apply_v41b.py --proj 65   /   python apply_v41b.py --all
"""
import json, os, sys, shutil

TEMP = r"C:\Users\25485\.zcode\workspace\default\temp"
BASE = r"E:\Program Files (x86)\Steam\steamapps\common\wallpaper_engine\projects\myprojects"
RESULTS = os.path.join(TEMP, "pupilfix", "results")
BACKUP = os.path.join(TEMP, "we_v41_backup")

FRAG_HEAD = r"""varying vec4 v_TexCoord;
varying float v_Pulse;

uniform sampler2D g_Texture0; // {"hidden":true}
uniform sampler2D g_Texture1; // {"material":"eyeglow","mode":"rgbmask","default":"util/black"}

uniform float g_GAx; // {"material":"眼A水平(%)"}
uniform float g_GAy; // {"material":"眼A垂直(%)"}
uniform float g_GBx; // {"material":"眼B水平(%)"}
uniform float g_GBy; // {"material":"眼B垂直(%)"}
uniform float g_Gr; // {"material":"瞳孔半径(层高%)"}
"""
FRAG_MID = r"""
const vec2 g_A0 = vec2(@AX, @AY);
const vec2 g_B0 = vec2(@BX, @BY);
// 引擎把非POT散装png垫到POT画布(内容置左上)，采样UV乘回内容占比
const vec2 g_PadInv = vec2(@PX, @PY);

void main() {
	vec4 base = texSample2D(g_Texture0, v_TexCoord.xy);

	vec2 pc = v_TexCoord.xy * 100.0;
	float dA = length(vec2((pc.x - g_A0.x) * 1.8194, pc.y - g_A0.y));
	float dB = length(vec2((pc.x - g_B0.x) * 1.8194, pc.y - g_B0.y));
	vec2 offA = vec2(g_GAx - g_A0.x, g_GAy - g_A0.y) * 0.01;
	vec2 offB = vec2(g_GBx - g_B0.x, g_GBy - g_B0.y) * 0.01;
	vec2 uvg = (v_TexCoord.xy - mix(offB, offA, step(dA, dB))) * g_PadInv;

	vec4 glow = texSample2D(g_Texture1, uvg);
	vec3 outc = base.rgb + glow.rgb * (v_Pulse * 1.35 + 0.08);
	gl_FragColor = vec4(min(outc, vec3(1.0, 1.0, 1.0)), base.a);
}
"""

def pot(n):
    return 1 << (n - 1).bit_length()

def bake_eyeglow(P, res):
    """从 bg2.png 现场烘焙眼形光斑（v39 方法）：彩色像素(sat>0.28&val>0.13)∩眼坐标1.6r圆门限
    → closing(5) → 高斯羽化σ1.6 为 Alpha；RGB=bg2×1.35 预乘；空蒙版放宽到 3.2r 重试。
    写入 materials/eyeglow.png（原生画布，POT 垫底由调用方处理）。"""
    import numpy as np
    from PIL import Image
    from scipy import ndimage
    bg2 = np.asarray(Image.open(os.path.join(P, "materials", "bg2.png")).convert("RGB")).astype(float) / 255.0
    H, W = bg2.shape[:2]
    mx = bg2.max(axis=2); mn = bg2.min(axis=2)
    sat = (mx - mn) / np.maximum(mx, 1e-6)
    colored = (sat > 0.28) & (mx > 0.13)
    eyes = [(res["ax"], res["ay"]), (res["bx"], res["by"])]
    for rmul in (1.6, 3.2):
        yy, xx = np.mgrid[0:H, 0:W]
        gate = np.zeros((H, W), bool)
        for ex, ey in eyes:
            r = res["r_pct"] / 100.0 * H * rmul
            gate |= ((xx - ex / 100.0 * W) ** 2 + (yy - ey / 100.0 * H) ** 2) < r * r
        m = colored & gate
        m = ndimage.binary_closing(m, structure=np.ones((5, 5)))
        if m.sum() > 30:
            break
    alpha = ndimage.gaussian_filter(m.astype(float), 1.6)
    alpha = np.clip(alpha * 1.4, 0, 1)  # ×1.4 补羽化损失
    rgb = np.clip(bg2 * 1.35, 0, 1) * alpha[..., None]  # 预乘
    out = np.dstack([rgb, alpha[..., None]])
    Image.fromarray((out * 255).astype(np.uint8)).save(os.path.join(P, "materials", "eyeglow.png"))
    return "baked(%dpx,rmul%.1f)" % (int(m.sum()), rmul)

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
    mat_path = os.path.join(P, "materials", "effects", "eyeflash.json")
    glow_path = os.path.join(P, "materials", "eyeglow.png")
    tex_path = os.path.join(P, "materials", "eyeglow.tex")

    import numpy as np
    from PIL import Image

    bg2 = Image.open(os.path.join(P, "materials", "bg2.png"))
    if not os.path.exists(glow_path):
        baked = bake_eyeglow(P, res)  # 新角色：无 v39 烘焙时现场生成
        print("  baked eyeglow:", baked)
    glow = Image.open(glow_path)
    # eyeglow 烘焙基准画布 = bg2 画布；垫底比由此算出（幂等：png 已 POT 也一样）
    W0, H0 = bg2.size
    assert glow.size in ((W0, H0), (pot(W0), pot(H0))), \
        "%s eyeglow%s 与 bg2%s 尺寸不符" % (dirname, glow.size, bg2.size)
    POT_W, POT_H = pot(W0), pot(H0)

    assert not os.path.exists(tex_path), dirname + " 存在 eyeglow.tex 会遮蔽 png（先回收）"

    bdir = os.path.join(BACKUP, "%02d" % nn)
    os.makedirs(bdir, exist_ok=True)
    for src, tag in ((frag_path, "eyeflash_frag.frag"), (scene_path, "scene.json"),
                     (mat_path, "eyeflash_mat.json"), (glow_path, "eyeglow_orig.png")):
        dst = os.path.join(bdir, tag)
        if not os.path.exists(dst):
            shutil.copy2(src, dst)

    # 1) POT 垫底重烘焙（幂等）
    if glow.size != (POT_W, POT_H):
        canvas = Image.new("RGBA", (POT_W, POT_H), (0, 0, 0, 0))
        canvas.paste(glow, (0, 0))
        canvas.save(glow_path)
        baked = "padded %s -> %s" % ((W0, H0), (POT_W, POT_H))
    else:
        baked = "already POT"

    # 2) frag（replace 拼装，避开 format 与注释花括号冲突）
    frag = (FRAG_HEAD + FRAG_MID
            .replace("@AX", "%.2f" % res["ax"]).replace("@AY", "%.2f" % res["ay"])
            .replace("@BX", "%.2f" % res["bx"]).replace("@BY", "%.2f" % res["by"])
            .replace("@PX", "%.5f" % (W0 / POT_W)).replace("@PY", "%.5f" % (H0 / POT_H)))
    atomic_write(frag_path, frag)

    # 3) 材质级纹理绑定
    mat = json.load(open(mat_path, encoding="utf-8"))
    mat["passes"][0]["textures"] = [None, "eyeglow"]
    atomic_write(mat_path, json.dumps(mat, ensure_ascii=False, indent="\t"))

    # 4) pupils 移到 depth 之前 + 清实例级 textures
    scene = json.load(open(scene_path, encoding="utf-8"))
    touched = 0
    for o in scene["objects"]:
        if o.get("name") not in ("bg1", "bg2", "bg3"):
            continue
        effs = o.get("effects", [])
        pupils = [e for e in effs if e.get("name") == "pupils"]
        assert len(pupils) == 1, dirname + " " + o["name"] + " pupils!=1"
        p = pupils[0]
        p["passes"][0].pop("textures", None)
        o["effects"] = [p] + [e for e in effs if e is not p]
        touched += 1
    assert touched == 3, dirname + " bg 层数 " + str(touched)
    atomic_write(scene_path, json.dumps(scene, ensure_ascii=False, indent="\t"))

    # 5) 回读校验
    chk = json.load(open(scene_path, encoding="utf-8"))
    for o in chk["objects"]:
        if o.get("name") in ("bg1", "bg2", "bg3"):
            names = [e.get("name") for e in o["effects"]]
            assert names[0] == "pupils" and names[1] == "depth", (dirname, names[:3])
            assert "textures" not in o["effects"][0]["passes"][0], dirname + " 实例级 textures 残留"
    mat2 = json.load(open(mat_path, encoding="utf-8"))
    assert mat2["passes"][0].get("textures") == [None, "eyeglow"], dirname + " 材质绑定缺失"
    f2 = open(frag_path, encoding="utf-8").read()
    assert "g_PadInv" in f2 and "base.a" in f2 and "%.5f" % (W0 / POT_W) in f2
    g2 = Image.open(glow_path)
    assert g2.size == (POT_W, POT_H), dirname + " png 未垫底"
    return "%s %s ratios(%.4f,%.4f)" % (dirname, baked, W0 / POT_W, H0 / POT_H)

def main():
    dirs = sorted(d for d in os.listdir(BASE) if d.startswith("zzz_mindscape_"))
    if "--all" in sys.argv:
        targets = dirs
    else:
        idx = [i for i, a in enumerate(sys.argv) if a == "--proj"]
        nn = sys.argv[idx[0] + 1] if idx else "65"
        targets = [d for d in dirs if d.split("_")[2] == nn]
    assert targets, "no target"
    for d in targets:
        print("OK", apply_project(d))
    print("v41b applied:", len(targets))

if __name__ == "__main__":
    main()
