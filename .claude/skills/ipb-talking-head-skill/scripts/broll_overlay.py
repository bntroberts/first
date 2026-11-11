#!/usr/bin/env python3
"""Overlay Storyblocks B-roll onto a rendered IPB video and write a Premiere XML.

Usage:
    python3 broll_overlay.py MAIN.mp4 plan.json -o "Name - Edited v1.mp4"
        [--no-xml] [--check-only] [--force]

MAIN.mp4 is the graphics render from ipb_edit.py (or the rough cut itself).
The plan's top-level "broll" array is described in references/broll.md.
The main audio is stream-copied untouched; B-roll audio is never used.
Writes <output>.xml (FCP7 XML, importable via File > Import in Premiere Pro):
V1 = main video, V2 = B-roll, A1/A2 = main audio.
"""
import argparse
import json
import os
import subprocess
import sys
from fractions import Fraction
from urllib.parse import quote
from xml.sax.saxutils import escape

HOOK_PROTECT = 15.0      # no B-roll in the opening hook
MIN_FACE_GAP = 10.0      # seconds of Brandon between inserts
GRAPHIC_MARGIN = 1.0     # clearance around graphics windows
MIN_LEN, MAX_LEN = 2.5, 8.0
PUSH = 0.06              # 100% -> 106%


def probe(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries",
         "stream=codec_type,width,height,r_frame_rate:format=duration",
         "-of", "json", path],
        check=True, capture_output=True, text=True).stdout
    info = json.loads(out)
    v = next((s for s in info["streams"] if s["codec_type"] == "video"), None)
    if v is None:
        sys.exit(f"No video stream in {path}")
    return {
        "w": int(v["width"]), "h": int(v["height"]),
        "fps": Fraction(v["r_frame_rate"]),
        "dur": float(info["format"]["duration"]),
        "audio": any(s["codec_type"] == "audio" for s in info["streams"]),
    }


def graphics_windows(plan):
    """Windows B-roll must stay clear of, using ipb_edit.py's plan schema
    (references/edit-plan.md). Tails include each element's exit animation."""
    wins = []
    for s in plan.get("data_sequences", []):
        wins.append(("data sequence", float(s["in"]), float(s["out"]) + 1.0))
    for tg in plan.get("source_tags", []):
        wins.append(("source tag", float(tg["in"]), float(tg["out"]) + 0.6))
    lt = plan.get("lower_third")
    if lt:
        wins.append(("lower third", float(lt["in"]), float(lt["out"]) + 0.7))
    for a, b, z0, z1 in plan.get("zooms", []):
        if b - a < 1.0 and z1 > z0:  # punch-in: the zoom is the emphasis
            wins.append(("punch-in zoom", float(a), float(b)))
    return wins


def validate(broll, plan, main, plan_dir):
    errors = []
    prev_end = None
    for i, b in enumerate(sorted(broll, key=lambda x: x["start"])):
        tag = f"broll[{i}] @ {b['start']:.1f}s"
        s, e = float(b["start"]), float(b["end"])
        length = e - s
        if length <= 0:
            errors.append(f"{tag}: end must be after start")
            continue
        if not MIN_LEN <= length <= MAX_LEN:
            errors.append(f"{tag}: length {length:.1f}s outside {MIN_LEN}-{MAX_LEN}s")
        if s < HOOK_PROTECT:
            errors.append(f"{tag}: inside the opening {HOOK_PROTECT:.0f}s hook")
        if e > main["dur"]:
            errors.append(f"{tag}: ends after the video ({main['dur']:.1f}s)")
        if prev_end is not None and s - prev_end < MIN_FACE_GAP:
            errors.append(f"{tag}: only {s - prev_end:.1f}s after the previous insert "
                          f"(min {MIN_FACE_GAP:.0f}s)")
        prev_end = e
        for key, gs, ge in graphics_windows(plan):
            if s < ge + GRAPHIC_MARGIN and e > gs - GRAPHIC_MARGIN:
                errors.append(f"{tag}: collides with {key} {gs:.1f}-{ge:.1f}s")
        path = os.path.join(plan_dir, b["file"])
        if not os.path.exists(path):
            errors.append(f"{tag}: missing file {b['file']}")
            continue
        clip = probe(path)
        need = float(b.get("source_in", 0)) + length
        if clip["dur"] < need:
            errors.append(f"{tag}: clip is {clip['dur']:.1f}s, needs {need:.1f}s")
    return errors


def build_filter(broll, main):
    W, H, fps = main["w"], main["h"], main["fps"]
    parts, last = [], "0:v"
    for i, b in enumerate(broll, start=1):
        s, e = float(b["start"]), float(b["end"])
        d = e - s
        fade = float(b.get("fade", 0.25))
        move = b.get("move", "push")
        chain = [f"fps={fps}",
                 f"scale={W}:{H}:force_original_aspect_ratio=increase",
                 f"crop={W}:{H}", "setsar=1"]
        if move in ("push", "pull"):
            z = f"(1+{PUSH}*t/{d:.3f})" if move == "push" else f"(1+{PUSH}*(1-t/{d:.3f}))"
            chain += [f"scale=w='trunc({W}*{z}/2)*2':h='trunc({H}*{z}/2)*2':eval=frame",
                      f"crop={W}:{H}"]
        chain.append("format=yuva420p")
        if fade > 0:
            chain += [f"fade=t=in:st=0:d={fade}:alpha=1",
                      f"fade=t=out:st={d - fade:.3f}:d={fade}:alpha=1"]
        chain.append(f"setpts=PTS-STARTPTS+{s:.3f}/TB")
        parts.append(f"[{i}:v]{','.join(chain)}[b{i}]")
        out = f"v{i}"
        parts.append(f"[{last}][b{i}]overlay=eof_action=pass:"
                     f"enable='between(t,{s:.3f},{e:.3f})'[{out}]")
        last = out
    parts.append(f"[{last}]format=yuv420p[vout]")
    return ";".join(parts)


def render(main_path, broll, main, plan_dir, out_path):
    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
           "-i", main_path]
    for b in broll:
        d = float(b["end"]) - float(b["start"])
        cmd += ["-ss", str(b.get("source_in", 0)), "-t", f"{d:.3f}",
                "-i", os.path.join(plan_dir, b["file"])]
    cmd += ["-filter_complex", build_filter(broll, main), "-map", "[vout]"]
    if main["audio"]:
        cmd += ["-map", "0:a", "-c:a", "copy"]
    cmd += ["-c:v", "libx264", "-preset", "medium", "-crf", "18",
            "-pix_fmt", "yuv420p", "-movflags", "+faststart", out_path]
    subprocess.run(cmd, check=True)


def file_url(path):
    return "file://" + quote(os.path.abspath(path))


def write_xml(xml_path, main_path, broll, main, plan_dir, name):
    fps = main["fps"]
    tb = round(float(fps))
    ntsc = "TRUE" if fps.denominator != 1 else "FALSE"
    rate = f"<rate><timebase>{tb}</timebase><ntsc>{ntsc}</ntsc></rate>"
    f = lambda sec: int(round(float(sec) * float(fps)))
    total = f(main["dur"])
    W, H = main["w"], main["h"]

    def file_el(fid, path, dur, audio):
        media = (f"<video><samplecharacteristics><width>{W}</width>"
                 f"<height>{H}</height></samplecharacteristics></video>")
        if audio:
            media += "<audio><channelcount>2</channelcount></audio>"
        return (f'<file id="{fid}"><name>{escape(os.path.basename(path))}</name>'
                f"<pathurl>{escape(file_url(path))}</pathurl>{rate}"
                f"<duration>{dur}</duration><media>{media}</media></file>")

    main_file = file_el("main-file", main_path, total, main["audio"])
    v1 = (f'<clipitem id="main-v"><name>{escape(os.path.basename(main_path))}</name>'
          f"{rate}<start>0</start><end>{total}</end><in>0</in><out>{total}</out>"
          f"{main_file}</clipitem>")
    v2 = []
    for i, b in enumerate(broll):
        path = os.path.join(plan_dir, b["file"])
        cdur = f(probe(path)["dur"])
        s, e, src = f(b["start"]), f(b["end"]), f(b.get("source_in", 0))
        label = b.get("title") or os.path.basename(path)
        v2.append(f'<clipitem id="broll-{i}"><name>{escape(str(label))}</name>{rate}'
                  f"<start>{s}</start><end>{e}</end><in>{src}</in>"
                  f"<out>{src + (e - s)}</out>"
                  f"{file_el(f'broll-file-{i}', path, cdur, False)}</clipitem>")
    audio = ""
    if main["audio"]:
        for ch in (1, 2):
            audio += (f'<track><clipitem id="main-a{ch}"><name>main</name>{rate}'
                      f"<start>0</start><end>{total}</end><in>0</in><out>{total}</out>"
                      f'<file id="main-file"/><sourcetrack><mediatype>audio</mediatype>'
                      f"<trackindex>{ch}</trackindex></sourcetrack></clipitem></track>")
    xml = ('<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE xmeml>\n'
           f'<xmeml version="4"><sequence id="seq"><name>{escape(name)}</name>'
           f"<duration>{total}</duration>{rate}<media>"
           f"<video><format><samplecharacteristics>{rate}<width>{W}</width>"
           f"<height>{H}</height></samplecharacteristics></format>"
           f"<track>{v1}</track><track>{''.join(v2)}</track></video>"
           f"<audio>{audio}</audio></media></sequence></xmeml>\n")
    with open(xml_path, "w", encoding="utf-8") as fh:
        fh.write(xml)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("main")
    ap.add_argument("plan")
    ap.add_argument("-o", "--output")
    ap.add_argument("--no-xml", action="store_true")
    ap.add_argument("--check-only", action="store_true")
    ap.add_argument("--force", action="store_true",
                    help="render even if style checks fail (Brandon asked for it)")
    args = ap.parse_args()

    with open(args.plan, encoding="utf-8") as fh:
        plan = json.load(fh)
    plan_dir = os.path.dirname(os.path.abspath(args.plan))
    broll = sorted(plan.get("broll", []), key=lambda b: float(b["start"]))
    main_info = probe(args.main)

    errors = validate(broll, plan, main_info, plan_dir)
    for err in errors:
        print("CHECK:", err, file=sys.stderr)
    missing = [e for e in errors if "missing file" in e or "clip is" in e]
    if missing or (errors and not args.force):
        sys.exit(f"{len(errors)} B-roll check(s) failed")
    if args.check_only:
        print(f"OK: {len(broll)} B-roll inserts pass checks")
        return
    if not args.output:
        sys.exit("--output is required unless --check-only")

    if broll:
        render(args.main, broll, main_info, plan_dir, args.output)
    else:
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", args.main,
                        "-c", "copy", args.output], check=True)
    out = probe(args.output)
    print(f"Rendered {args.output}: {out['dur']:.2f}s "
          f"(source {main_info['dur']:.2f}s), audio={'yes' if out['audio'] else 'NO'}")
    if not args.no_xml:
        xml_path = os.path.splitext(args.output)[0] + ".xml"
        write_xml(xml_path, args.main, broll, main_info, plan_dir,
                  os.path.splitext(os.path.basename(args.output))[0])
        print(f"Premiere timeline: {xml_path}")


if __name__ == "__main__":
    main()
