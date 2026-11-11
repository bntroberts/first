#!/usr/bin/env python3
"""The Insurance Pro Blog talking-head editor.

Renders punch-in zooms, the opening lower third, and statistic "data sequences"
(talking-head frame shrinks to the top left while stat cards animate in) from a
JSON edit plan, then muxes the original audio untouched.

Usage:
  python3 ipb_edit.py plan.json                 # full render
  python3 ipb_edit.py plan.json --from 13 --to 33 --out test.mp4   # preview a range
  python3 ipb_edit.py plan.json --stills 2,6,20  # write PNG stills only (fast check)

See references/edit-plan.md for the plan schema.
"""
import argparse, json, os, subprocess, sys
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
FONTS = os.path.join(HERE, "..", "assets", "fonts")
W, H = 1920, 1080
NAVY = (27, 58, 92); TEAL = (26, 122, 109); SLATE = (44, 62, 80); GOLD = (197, 146, 46)
WARM = (245, 243, 239); STONE = (232, 228, 221); MUTED = (136, 136, 136); WHITE = (255, 255, 255)

_FILES = {("sans",400):"Lato-Regular.ttf",("sans",700):"Lato-Bold.ttf",("sans",900):"Lato-Black.ttf",
          ("serif",400):"PT_Serif-Web-Regular.ttf",("serif",700):"PT_Serif-Web-Bold.ttf"}
def font(fam, size, wght):
    return ImageFont.truetype(os.path.join(FONTS, _FILES[(fam, wght)]), size)
SANS = "sans"; SERIF = "serif"

def ease(x):
    x = min(max(x, 0.0), 1.0)
    return 4*x*x*x if x < .5 else 1 - (-2*x+2)**3/2
def eout(x):
    x = min(max(x, 0.0), 1.0); return 1-(1-x)**3

def soft_shadow(layer, box, radius, blur=16, alpha=60, off=(0, 8)):
    g = Image.new("RGBA", layer.size, (0,0,0,0))
    x0,y0,x1,y1 = box
    ImageDraw.Draw(g).rounded_rectangle([x0+off[0],y0+off[1],x1+off[0],y1+off[1]], radius, fill=(20,30,45,alpha))
    layer.alpha_composite(g.filter(ImageFilter.GaussianBlur(blur)))

def wrap(txt, f, w):
    out, line = [], ""
    for wd in txt.split():
        t = (line+" "+wd).strip()
        if f.getlength(t) <= w or not line: line = t
        else: out.append(line); line = wd
    out.append(line); return out

def fade(arr, a):
    arr = arr.copy(); arr[...,3] = (arr[...,3]*a).astype(np.uint8); return arr

def over(base, rgba):
    a = rgba[...,3:4].astype(np.float32)/255
    base[:] = (base*(1-a) + rgba[...,:3][...,::-1]*a).astype(np.uint8)

class Editor:
    def __init__(self, plan):
        self.p = plan
        self.face = plan.get("face_center", [960, 380])
        self.zooms = sorted(plan.get("zooms", []), key=lambda z: z[0])
        self.seqs = plan.get("data_sequences", [])
        self.lt = plan.get("lower_third")
        self.tags = plan.get("source_tags", [])
        self.TAGL = font(SANS, 20, 700); self.TAGF = font(SERIF, 30, 400)
        self.NUMF = font(SANS, 150, 900); self.PREF = font(SANS, 28, 700)
        self.LABF = font(SERIF, 38, 400); self.LTF = font(SANS, 58, 700)
        self.LTSUB = font(SANS, 26, 700); self.SRCF = font(SERIF, 24, 400)
        self.bgs = {}

    # ---------- zoom ----------
    def zoom_at(self, t):
        z = 1.0
        for a, b, z0, z1 in self.zooms:
            if t >= b: z = z1
            elif t >= a: return z0 + (z1-z0)*ease((t-a)/(b-a))
        return z
    def crop_for(self, z):
        cw, ch = W/z, H/z; fx, fy = self.face
        k = min((z-1)/0.16, 1.0)
        cx = min(max(960 + (fx-960)*k, cw/2), W-cw/2)
        cy = min(max(540 + (fy-540)*k, ch/2), H-ch/2)
        return np.array([cx-cw/2, cy-ch/2, cw, ch])

    # ---------- data sequence ----------
    def make_bg(self, s):
        img = Image.new("RGBA", (W, H), WARM+(255,)); d = ImageDraw.Draw(img)
        d.rectangle([0, H-14, W, H], fill=NAVY+(255,))
        d.rectangle([0, H-20, W, H-14], fill=TEAL+(255,))
        label = s.get("label", "").upper()
        y = 580
        if label:
            d.text((60, y), "  ".join(label), font=font(SANS, 24, 700), fill=TEAL); y += 48
        title = s.get("title", "")
        if title:
            size = 66
            while font(SANS, size, 700).getlength(title) > 800 and size > 36: size -= 2
            lines = wrap(title, font(SANS, size, 700), 800) if size == 36 else [title]
            for ln in lines:
                d.text((60, y), ln, font=font(SANS, size, 700), fill=NAVY); y += int(size*1.2)
            d.rectangle([60, y+14, 120, y+17], fill=TEAL); y += 44
        sub = s.get("subtitle", "")
        if sub:
            for ln in wrap(sub, font(SERIF, 32, 400), 800):
                d.text((60, y), ln, font=font(SERIF, 32, 400), fill=SLATE); y += 44
        src = s.get("source_note", "")
        if src:
            sl = wrap(src, self.SRCF, 800); yy = 1030 - 30*len(sl)
            for ln in sl:
                d.text((60, yy), ln, font=self.SRCF, fill=MUTED); yy += 30
        return np.array(img)

    def list_layer(self, s, t):
        # numbered agenda cards (style "list"): same card look as stats, one per item
        L = Image.new("RGBA", (W, H), (0,0,0,0))
        items = s["stats"]; n = len(items)
        gap = 22; top, bot = 80, 1010
        ch = min(200, (bot-top-gap*(n-1))//n)
        y_start = top + ((bot-top) - (ch*n + gap*(n-1)))//2
        numf = font(SANS, min(110, int(ch*0.62)), 900)
        hf = font(SANS, 40, 700); sf = font(SERIF, 29, 400)
        for i, it in enumerate(items):
            a = eout((t-it["t"])/0.55)
            if a <= 0: continue
            x0 = 930 + int((1-a)*120); y0 = y_start + i*(ch+gap)
            row = Image.new("RGBA", (W, H), (0,0,0,0))
            soft_shadow(row, [x0, y0, x0+930, y0+ch], 10, blur=14, alpha=45)
            d = ImageDraw.Draw(row)
            d.rounded_rectangle([x0, y0, x0+930, y0+ch], 10, fill=WHITE+(255,), outline=STONE+(255,), width=2)
            d.rounded_rectangle([x0, y0, x0+10, y0+ch], 4, fill=TEAL+(255,))
            d.text((x0+60, y0+ch//2), str(it.get("num", i+1)), font=numf, fill=TEAL, anchor="mm")
            d.rectangle([x0+112, y0+28, x0+114, y0+ch-28], fill=STONE+(255,))
            sub = wrap(it.get("sub", ""), sf, 740) if it.get("sub") else []
            blk = 48 + 38*len(sub); ly = y0 + (ch-blk)//2
            d.text((x0+145, ly), it["label"], font=hf, fill=NAVY); ly += 52
            for ln in sub:
                d.text((x0+145, ly), ln, font=sf, fill=SLATE); ly += 38
            L.alpha_composite(Image.fromarray(fade(np.array(row), a)))
        return np.array(L)

    def stat_layer(self, s, t):
        if s.get("style") == "list": return self.list_layer(s, t)
        L = Image.new("RGBA", (W, H), (0,0,0,0))
        stats = s["stats"]; n = len(stats)
        gap = 40; top, bot = 95, 1000
        ch = min(275, (bot-top-gap*(n-1))//n)
        y_start = top + ((bot-top) - (ch*n + gap*(n-1)))//2 if n < 3 else top
        for i, st in enumerate(stats):
            ts = st["t"]; a = eout((t-ts)/0.55)
            if a <= 0: continue
            x0 = 930 + int((1-a)*120); y0 = y_start + i*(ch+gap)
            row = Image.new("RGBA", (W, H), (0,0,0,0))
            soft_shadow(row, [x0, y0, x0+930, y0+ch], 10, blur=14, alpha=45)
            d = ImageDraw.Draw(row)
            d.rounded_rectangle([x0, y0, x0+930, y0+ch], 10, fill=WHITE+(255,), outline=STONE+(255,), width=2)
            d.rounded_rectangle([x0, y0, x0+10, y0+ch], 4, fill=TEAL+(255,))
            cnt = eout((t-ts)/1.1)
            val = float(st["value"]); dec = int(st.get("decimals", 0))
            pre, suf = st.get("prefix",""), st.get("suffix","%")
            disp = st.get("display")
            num = disp if disp else f"{pre}{val*cnt:,.{dec}f}{suf}"
            full_num = disp if disp else f"{pre}{val:,.{dec}f}{suf}"
            numf = self.NUMF
            while numf.getlength(full_num) > 340 and numf.size > 72:
                numf = font(SANS, numf.size-8, 900)
            bar = st.get("bar", suf == "%")
            if st.get("qualifier"): d.text((x0+44, y0+26), st["qualifier"].upper(), font=self.PREF, fill=GOLD)
            base = y0+ch-66 if bar else y0+ch//2+numf.size*0.36
            d.text((x0+44, base), num, font=numf, fill=NAVY, anchor="ls")
            lines = wrap(st["label"], self.LABF, 490)
            ly = y0 + (ch-(40 if bar else 0))//2 - len(lines)*24 - 4
            for ln in lines:
                d.text((x0+405, ly), ln, font=self.LABF, fill=SLATE); ly += 48
            if bar:
                frac = float(st.get("bar_fraction", val/100))
                bx0, bx1, by = x0+44, x0+890, y0+ch-40
                d.rounded_rectangle([bx0, by, bx1, by+14], 7, fill=STONE+(255,))
                fw = int((bx1-bx0)*min(max(frac,0),1)*cnt)
                if fw > 10: d.rounded_rectangle([bx0, by, bx0+fw, by+14], 7, fill=TEAL+(255,))
            L.alpha_composite(Image.fromarray(fade(np.array(row), a)))
        return np.array(L)

    # ---------- lower third ----------
    def lower_third(self, t):
        lt = self.lt
        if not lt: return None
        tin, tout = lt["in"], lt["out"]
        if t < tin or t > tout+0.7: return None
        txt = lt.get("text", "Brandon Roberts")
        sub = lt.get("subtitle", "The Insurance Pro Blog").upper()
        po = 1-ease((t-tout)/0.6)
        x, y, h = 110, 830, 150
        w = int(max(self.LTF.getlength(txt), self.LTSUB.getlength("  ".join(sub)))) + 110
        L = Image.new("RGBA", (W, H), (0,0,0,0))
        bw = int(w*ease((t-tin-0.2)/0.55)) if t < tout else int(w*po)
        acc = eout((t-tin)/0.35)*po
        if bw > 20:
            soft_shadow(L, [x, y, x+bw, y+h], 8, blur=14, alpha=int(70*po))
            d = ImageDraw.Draw(L)
            d.rounded_rectangle([x, y, x+bw, y+h], 8, fill=WHITE+(int(245*po),))
            d.rectangle([x, y+h-6, x+bw, y+h], fill=NAVY+(int(255*po),))
        d = ImageDraw.Draw(L)
        if acc > 0: d.rectangle([x, y, x+12, y+int(h*acc)], fill=TEAL+(int(255*po),))
        ta = ease((t-tin-0.6)/0.4)*po
        if ta > 0:
            T = Image.new("RGBA", (W, H), (0,0,0,0)); dt = ImageDraw.Draw(T)
            off = int((1-ease((t-tin-0.6)/0.4))*20) if t < tout else 0
            dt.text((x+50+off, y+20), txt, font=self.LTF, fill=NAVY)
            dt.text((x+52+off, y+96), "  ".join(sub), font=self.LTSUB, fill=TEAL)
            L.alpha_composite(Image.fromarray(fade(np.array(T), ta)))
        return np.array(L)

    # ---------- source tag ----------
    def source_tag(self, t):
        for tg in self.tags:
            tin, tout = tg["in"], tg["out"]
            if not (tin <= t <= tout+0.6): continue
            po = 1-ease((t-tout)/0.6)
            a = eout((t-tin)/0.5)*po
            lab = tg.get("label", "Research").upper()
            lines = wrap(tg["text"], self.TAGF, 1150)
            x, h = 110, 62 + 40*len(lines)
            y = 1000 - h
            w = int(max(max(self.TAGF.getlength(l) for l in lines), self.TAGL.getlength("  ".join(lab)))) + 80
            L = Image.new("RGBA", (W, H), (0,0,0,0))
            off = int((1-eout((t-tin)/0.5))*-30)
            soft_shadow(L, [x+off, y, x+off+w, y+h], 8, blur=12, alpha=55)
            d = ImageDraw.Draw(L)
            d.rounded_rectangle([x+off, y, x+off+w, y+h], 8, fill=WHITE+(245,))
            d.rounded_rectangle([x+off, y, x+off+8, y+h], 3, fill=TEAL+(255,))
            d.text((x+off+36, y+18), "  ".join(lab), font=self.TAGL, fill=TEAL)
            yy = y+50
            for ln in lines:
                d.text((x+off+36, yy), ln, font=self.TAGF, fill=SLATE); yy += 40
            return fade(np.array(L), a)
        return None

    # ---------- frame ----------
    def compose(self, frame, t):
        z = self.zoom_at(t); full = self.crop_for(z)
        seq = None
        for i, s in enumerate(self.seqs):
            if s["in"] <= t < s["out"] + 1.0: seq = (i, s)
        if seq is None:
            if z > 1.0001:
                M = np.array([[W/full[2],0,-full[0]*W/full[2]],[0,H/full[3],-full[1]*H/full[3]]],np.float32)
                out = cv2.warpAffine(frame, M, (W,H), flags=cv2.INTER_LINEAR)
            else: out = frame.copy()
        else:
            i, s = seq
            if i not in self.bgs: self.bgs[i] = self.make_bg(s)
            tin, tout = s["in"], s["out"]
            chained = s.get("chained") and i > 0
            if chained: k = 1.0 if t < tout else 1-ease((t-tout)/1.0)
            elif t < tin+0.8: k = ease((t-tin)/0.8)
            elif t < tout: k = 1.0
            else: k = 1-ease((t-tout)/1.0)
            fx, fy = self.face
            pip_src = np.array(s.get("pip_crop", [fx-650, fy-365.6, 1300, 731.2]), float)
            src = full*(1-k) + pip_src*k
            dst = np.array([0,0,W,H])*(1-k) + np.array([60,60,800,450])*k
            out = self.bgs[i][...,:3][...,::-1].copy()
            if chained and t < tin+0.7:
                # dip: previous panel fades to a blank panel, then the new one fades in
                j = i-1
                if j not in self.bgs: self.bgs[j] = self.make_bg(self.seqs[j])
                if "blank" not in self.bgs: self.bgs["blank"] = self.make_bg({})
                blank = self.bgs["blank"][...,:3][...,::-1]
                a = (t-tin)/0.7
                if a < 0.5:
                    e = ease(a*2)
                    out = (self.bgs[j][...,:3][...,::-1]*(1-e) + blank*e).astype(np.uint8)
                    over(out, fade(self.stat_layer(self.seqs[j], t), 1-e))
                else:
                    e = ease((a-0.5)*2)
                    out = (blank*(1-e) + out*e).astype(np.uint8)
            sl = self.stat_layer(s, t)
            if t >= tout: sl = fade(sl, k)
            over(out, sl)
            sx, sy, sw, sh = src; dx, dy, dw, dh = dst
            dw, dh = max(int(round(dw)),2), max(int(round(dh)),2); dx, dy = int(round(dx)), int(round(dy))
            M = np.array([[dw/sw,0,-sx*dw/sw],[0,dh/sh,-sy*dh/sh]],np.float32)
            pip = cv2.warpAffine(frame, M, (dw,dh), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
            r = int(12*k); b = int(8*k)
            if k > 0.05:
                shd = np.zeros((H,W),np.float32)
                cv2.rectangle(shd,(dx+10,dy+14),(dx+dw+10,dy+dh+14),1.0,-1)
                shd = cv2.GaussianBlur(shd,(0,0),18)*0.30*k
                out = (out*(1-shd[...,None])).astype(np.uint8)
            mask = np.full((dh,dw),255,np.uint8)
            if r > 1:
                mask[:] = 0
                cv2.rectangle(mask,(r,0),(dw-r,dh),255,-1); cv2.rectangle(mask,(0,r),(dw,dh-r),255,-1)
                for cx,cy in [(r,r),(dw-r-1,r),(r,dh-r-1),(dw-r-1,dh-r-1)]: cv2.circle(mask,(cx,cy),r,255,-1,cv2.LINE_AA)
            x0,y0 = max(dx,0),max(dy,0); x1,y1 = min(dx+dw,W),min(dy+dh,H)
            m = mask[y0-dy:y1-dy, x0-dx:x1-dx,None].astype(np.float32)/255
            out[y0:y1,x0:x1] = (pip[y0-dy:y1-dy, x0-dx:x1-dx]*m + out[y0:y1,x0:x1]*(1-m)).astype(np.uint8)
            if b > 0:
                Ly = Image.new("RGBA",(W,H),(0,0,0,0)); d = ImageDraw.Draw(Ly)
                d.rounded_rectangle([dx-b,dy-b,dx+dw+b-1,dy+dh+b-1], r+b, outline=WHITE+(int(255*k),), width=b)
                d.rounded_rectangle([dx-b-3,dy-b-3,dx+dw+b+2,dy+dh+b+2], r+b+3, outline=TEAL+(int(255*k),), width=3)
                over(out, np.array(Ly))
        lt = self.lower_third(t)
        if lt is not None: over(out, lt)
        if seq is None:
            tg = self.source_tag(t)
            if tg is not None: over(out, tg)
        return out

def probe_fps(path):
    r = subprocess.run(["ffprobe","-v","error","-select_streams","v:0","-show_entries","stream=r_frame_rate",
                        "-of","csv=p=0",path], capture_output=True, text=True).stdout.strip()
    n, d = r.split("/"); return float(n)/float(d), r

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("plan"); ap.add_argument("--out"); ap.add_argument("--from", dest="t0", type=float, default=0.0)
    ap.add_argument("--to", dest="t1", type=float); ap.add_argument("--stills")
    a = ap.parse_args()
    plan = json.load(open(a.plan)); src = plan["source"]; ed = Editor(plan)
    fps, fps_str = probe_fps(src)
    vf = f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H}"
    if a.stills:
        for t in [float(x) for x in a.stills.split(",")]:
            raw = subprocess.run(["ffmpeg","-v","error","-ss",str(t),"-i",src,"-frames:v","1","-vf",vf,
                                  "-f","rawvideo","-pix_fmt","bgr24","-"], capture_output=True).stdout
            f = np.frombuffer(raw[:W*H*3], np.uint8).reshape(H,W,3)
            p = f"still_{t:.2f}.png"; cv2.imwrite(p, ed.compose(f, t)); print(p)
        return
    out = a.out or plan.get("output", "edited.mp4")
    tmp = out + ".video.mp4"
    dcmd = ["ffmpeg","-v","error","-ss",str(a.t0),"-i",src]
    if a.t1: dcmd += ["-t", str(a.t1-a.t0)]
    dec = subprocess.Popen(dcmd+["-vf",vf,"-f","rawvideo","-pix_fmt","bgr24","-"], stdout=subprocess.PIPE)
    enc = subprocess.Popen(["ffmpeg","-v","error","-y","-f","rawvideo","-pix_fmt","bgr24","-s",f"{W}x{H}",
                            "-r",fps_str,"-i","-","-c:v","libx264","-preset","medium","-crf","18",
                            "-pix_fmt","yuv420p",tmp], stdin=subprocess.PIPE)
    i, fs = 0, W*H*3
    while True:
        buf = dec.stdout.read(fs)
        if len(buf) < fs: break
        enc.stdin.write(ed.compose(np.frombuffer(buf,np.uint8).reshape(H,W,3), a.t0+i/fps).tobytes()); i += 1
        if i % 250 == 0: print(f"{i} frames", flush=True)
    enc.stdin.close(); enc.wait()
    acmd = ["ffmpeg","-v","error","-y","-i",tmp,"-ss",str(a.t0)]
    if a.t1: acmd += ["-t", str(a.t1-a.t0)]
    subprocess.run(acmd+["-i",src,"-map","0:v","-map","1:a?","-c:v","copy"]+(["-c:a","copy"] if not a.t1 and a.t0==0 else ["-c:a","aac","-b:a","256k"])+["-shortest",out], check=True)
    os.remove(tmp); print("wrote", out, i, "frames")

if __name__ == "__main__":
    main()
