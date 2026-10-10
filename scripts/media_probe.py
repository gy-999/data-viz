
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""data-viz: media_probe.py - media & file-family asset profiler (v1.1)
Images (Pillow): dims/format/EXIF date/camera/aspect/duplicate-groups (perceptual hash)
Video/Audio: file-level profile (no ffprobe -> no duration)
Archives: zip inner listing
Any directory: file-family composition, size buckets, mtime range
"""
import os, sys, json, time, zipfile, hashlib
from pathlib import Path
from collections import Counter
from datetime import datetime

IMG_EXT = {'.png','.jpg','.jpeg','.gif','.bmp','.webp','.tif','.tiff','.heic'}
VID_EXT = {'.mp4','.avi','.mov','.mkv','.wmv','.flv','.m4v','.ts','.webm'}
AUD_EXT = {'.mp3','.wav','.flac','.aac','.m4a','.ogg','.wma'}
ARC_EXT = {'.zip','.7z','.rar','.tar','.gz'}
DOC_EXT = {'.docx','.pptx','.xlsx','.pdf','.doc','.xls'}

def _ahash(path):
    """perceptual hash: 8x8 mean-bits + mean-brightness bucket (kills flat-color collisions)"""
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        try:
            from PIL import Image
            im = Image.open(path).convert("L").resize((8, 8))
            px = list(im.getdata())
            mean = sum(px) / 64.0
            bits = "".join("1" if v >= mean else "0" for v in px)
            bucket = int(mean // 24)
            return "%s%02x" % (format(int(bits, 2), "016x"), bucket)
        except Exception:
            return None

def profile_images(paths):
    from PIL import Image
    out = {"count": len(paths), "formats": Counter(), "dims": Counter(),
           "aspect": Counter(), "cameras": Counter(), "with_date": 0,
           "date_min": None, "date_max": None, "total_mb": 0.0}
    hashes = {}
    for p in paths:
        try:
            st = os.stat(p)
            out["total_mb"] += st.st_size / 1048576
            im = Image.open(p)
            w, h = im.size
            fmt = (im.format or Path(p).suffix.lstrip(".")).upper()
            out["formats"][fmt] += 1
            out["dims"]["%dx%d" % (w, h)] += 1
            if w > h * 1.05: out["aspect"]["横图"] += 1
            elif h > w * 1.05: out["aspect"]["竖图"] += 1
            else: out["aspect"]["方图"] += 1
            exif = im.getexif()
            cam = exif.get(272)
            dt = exif.get(306)
            if cam: out["cameras"][str(cam)[:40]] += 1
            if dt:
                out["with_date"] += 1
                s = str(dt)[:19]
                out["date_min"] = s if out["date_min"] is None or s < out["date_min"] else out["date_min"]
                out["date_max"] = s if out["date_max"] is None or s > out["date_max"] else out["date_max"]
            im.close()
            hs = _ahash(p)
            if hs: hashes.setdefault(hs, []).append(str(Path(p).name))
        except Exception:
            out["formats"].setdefault("(打不开)", 0)
            out["formats"]["(打不开)"] += 1
    dup = [[names[0]] + (["+%d同图" % (len(names)-1)] if len(names) > 1 else [])
           for hs, names in hashes.items() if len(names) > 1]
    out["dup_groups"] = dup
    out["dup_suspect_files"] = sum(len(n) for n in hashes.values() if len(n) > 1)
    for k in ("formats", "dims", "aspect", "cameras"):
        out[k] = out[k].most_common(10)
    out["total_mb"] = round(out["total_mb"], 1)
    return out

def profile_files(paths):
    c = {"count": len(paths), "exts": Counter(), "total_mb": 0.0,
         "size_max_mb": 0.0, "mtime_min": None, "mtime_max": None}
    for p in paths:
        try:
            st = os.stat(p)
            mb = st.st_size / 1048576
            c["total_mb"] += mb
            c["size_max_mb"] = max(c["size_max_mb"], mb)
            c["exts"][Path(p).suffix.lower() or "(无)"] += 1
            mt = datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d")
            c["mtime_min"] = mt if c["mtime_min"] is None or mt < c["mtime_min"] else c["mtime_min"]
            c["mtime_max"] = mt if c["mtime_max"] is None or mt > c["mtime_max"] else c["mtime_max"]
        except Exception: pass
    c["exts"] = c["exts"].most_common(10)
    c["total_mb"] = round(c["total_mb"], 1)
    c["size_max_mb"] = round(c["size_max_mb"], 1)
    return c

def profile_zip(p):
    info = {"name": Path(p).name, "inner_count": 0, "inner_exts": [], "size_mb": 0.0}
    try:
        with zipfile.ZipFile(p) as z:
            names = [i.filename for i in z.infolist() if not i.is_dir()]
            info["inner_count"] = len(names)
            info["inner_exts"] = Counter(Path(n).suffix.lower() for n in names).most_common(8)
            info["size_mb"] = round(sum(i.file_size for i in z.infolist()) / 1048576, 1)
    except Exception as e:
        info["error"] = str(e)[:80]
    return info

def profile(source):
    t0 = time.time()
    p = Path(source)
    if p.is_file():
        paths = [p]
        root = p.parent
    else:
        paths = [f for f in sorted(p.rglob("*")) if f.is_file()]
        root = p
    fam = {"image": [], "video": [], "audio": [], "archive": [], "document": [], "other": []}
    for f in paths:
        e = f.suffix.lower()
        if e in IMG_EXT: fam["image"].append(f)
        elif e in VID_EXT: fam["video"].append(f)
        elif e in AUD_EXT: fam["audio"].append(f)
        elif e in ARC_EXT: fam["archive"].append(f)
        elif e in DOC_EXT: fam["document"].append(f)
        else: fam["other"].append(f)

    result = {
        "type": "media_profile",
        "source": str(source),
        "file_count": len(paths),
        "by_family": {k: len(v) for k, v in fam.items()},
        "scan_time": 0,
    }
    if fam["image"]: result["images"] = profile_images(fam["image"])
    for k in ("video", "audio", "other"):
        if fam[k]: result[k] = profile_files(fam[k])
    if fam["document"]:
        result["documents"] = profile_files(fam["document"])
        result["documents"]["note"] = "docx/pptx/xlsx 表格可用 doc_extract.py 抽取为 CSV 进入分析管线"
    if fam["archive"]:
        result["archives"] = [profile_zip(f) for f in fam["archive"][:20]]
    allf = profile_files(paths)
    result["overall"] = {"total_mb": allf["total_mb"], "size_max_mb": allf["size_max_mb"],
                          "mtime_range": [allf["mtime_min"], allf["mtime_max"]]}
    result["scan_time"] = round(time.time() - t0, 2)
    return result

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", required=True)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    r = profile(a.source)
    if a.json:
        print(json.dumps(r, ensure_ascii=False, default=str, indent=2))
    else:
        print("文件族:", r["by_family"])
        if "images" in r:
            im = r["images"]
            print("图片:", im["count"], "| 格式:", dict(im["formats"]), "| 横竖:", dict(im["aspect"]))
            print("  EXIF日期覆盖:", im["with_date"], "| 相机:", dict(im["cameras"]))
            print("  疑似重复组:", len(im["dup_groups"]), "组 /", im["dup_suspect_files"], "张")
            for g in im["dup_groups"][:5]: print("   -", g)
        if "video" in r: print("视频:", r["video"]["count"], "个,", r["video"]["total_mb"], "MB (无ffprobe,未抽时长)")
        if "audio" in r: print("音频:", r["audio"]["count"], "个")
        if "documents" in r: print("文档:", r["documents"]["count"], "个 ->", r["documents"]["note"])
        if "archives" in r:
            for a2 in r["archives"]: print("压缩包:", a2["name"], "内含", a2["inner_count"], "文件")
        print("总体:", r["overall"], "| 耗时:", r["scan_time"], "s")
