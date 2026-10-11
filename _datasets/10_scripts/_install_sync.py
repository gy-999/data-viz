"""把主副本 data-viz 同步安装到多个平台，并校验哈希。

用法:
    python _install_sync.py            # 同步到默认目标
    python _install_sync.py --dry-run  # 只看会改什么
    python _install_sync.py --verify   # 只校验，不写入

设计要点:
  * 主副本 = D:\\Claude cade\\data\\data-viz（git 仓库，唯一事实来源）
  * 目标 = Claude Code (D:\\Claude cade\\skill\\skills) + DSH (C:\\Users\\guoyu\\.dsh\\skills)
  * 排除 .git / __pycache__ / *.pyc / output / .pytest_cache，避免把运行垃圾装进去
  * 目标里多出来的旧文件会被删除（保持目标与主副本一致），并逐文件 MD5 校验
"""
import argparse
import hashlib
import pathlib
import shutil
import sys

MASTER = pathlib.Path(r"D:\Claude cade\data\data-viz")
TARGETS = {
    "Claude Code": pathlib.Path(r"D:\Claude cade\skill\skills\data-viz"),
    "DSH": pathlib.Path(r"C:\Users\guoyu\.dsh\skills\data-viz"),
}
EXCLUDE_DIRS = {".git", "__pycache__", ".pytest_cache", "output", ".idea", ".vscode"}
EXCLUDE_SUFFIX = {".pyc", ".pyo", ".log"}


def rel_files(root: pathlib.Path):
    for p in sorted(root.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(root)
        if any(part in EXCLUDE_DIRS for part in rel.parts):
            continue
        if p.suffix.lower() in EXCLUDE_SUFFIX:
            continue
        yield rel


def md5(p: pathlib.Path) -> str:
    h = hashlib.md5()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sync(target: pathlib.Path, dry: bool):
    print(f"\n=== {target} ===")
    target.mkdir(parents=True, exist_ok=True)
    src_map = {rel: (MASTER / rel) for rel in rel_files(MASTER)}
    dst_map = {rel: (target / rel) for rel in rel_files(target)}

    added = [r for r in src_map if r not in dst_map]
    changed = [r for r in src_map if r in dst_map and md5(src_map[r]) != md5(dst_map[r])]
    removed = [r for r in dst_map if r not in src_map]

    print(f"  主副本 {len(src_map)} 个文件 | 目标 {len(dst_map)} 个文件")
    print(f"  新增 {len(added)} / 更新 {len(changed)} / 删除（主副本已无）{len(removed)}")
    for r in (added + changed)[:12]:
        print(f"    + {r}")
    for r in removed[:12]:
        print(f"    - {r}")

    if dry:
        return added, changed, removed

    for rel in added + changed:
        dst = target / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src_map[rel], dst)
    for rel in removed:
        (target / rel).unlink()
    # 清掉空的 __pycache__ 之类残留目录
    for p in sorted([x for x in target.rglob("*") if x.is_dir()], key=lambda x: -len(x.parts)):
        try:
            if not any(p.iterdir()):
                p.rmdir()
        except OSError:
            pass

    # 校验
    bad = []
    for rel, src in src_map.items():
        dst = target / rel
        if not dst.exists() or md5(src) != md5(dst):
            bad.append(str(rel))
    print(f"  校验: {'全部一致 (' + str(len(src_map)) + ' 个文件)' if not bad else '不一致 -> ' + ', '.join(bad[:6])}")
    return added, changed, removed


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--verify", action="store_true")
    a = ap.parse_args()
    if not MASTER.exists():
        print(f"主副本不存在: {MASTER}")
        sys.exit(1)
    if a.verify:
        for name, t in TARGETS.items():
            src = {r for r in rel_files(MASTER)}
            dst = {r for r in rel_files(t)} if t.exists() else set()
            diff = src ^ dst
            bad = [r for r in src & dst if md5(MASTER / r) != md5(t / r)]
            print(f"{name}: {'一致' if not diff and not bad else f'差异 {len(diff)} 个文件路径, {len(bad)} 个内容不同'}")
        return
    for name, t in TARGETS.items():
        sync(t, a.dry_run)
    print("\n完成。")


if __name__ == "__main__":
    main()
