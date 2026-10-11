"""把看板案例整理成「自包含分享包」：每个包一个文件夹 + 说明 + zip，明天可直接发出去。"""
import pathlib
import shutil
import zipfile

ROOT = pathlib.Path(r"D:\Claude cade\data\_datasets")
DASH = ROOT / "09_dashboards"
PKG = ROOT / "11_share_ready"
PKG.mkdir(exist_ok=True)

REPO = "https://github.com/gy-999/data-viz"
REPO_ZIP = "https://codeload.github.com/gy-999/data-viz/zip/refs/heads/main"

PACKAGES = {
    "1_订单数据分析": {
        "src": DASH / "chinese_orders",
        "keep": ["dashboard.html", "数据总结报告.docx", "dashboard.config.yaml",
                 "plan.json", "report_spec.json", "warehouse.db"],
        "keep_dirs": ["artifacts"],
        "title": "订单数据分析（本次实测样例）",
        "data": "03_text_dirty/chinese_orders_gbk.csv",
        "data_desc": "中文 GBK 订单表：4,000 行 × 12 列（订单号/日期/客户/客户类型/城市/省份/产品类别/销售额/数量/折扣/利润）",
        "points": [
            "看板 21 个组件、0 警告，含 6 种新增统计图（箱线图 / 正态Q-Q / 帕累托×2 / 相关矩阵 / 回归）",
            "探源命中：UTF-8 解码失败需回退 GBK；空串 291 行；字面 None 1,047 行；订单号重复 2,075 行；1,243 行日期被压平",
            "真实结论：销售额 923,303 元 / 1,925 笔订单 / 860 客户；四川等前 4 省占 80%；折扣与利润 ρ=-0.53；利润~销售额 R²=0.0196",
        ],
    },
    "2_WELL看板演示": {
        "src": DASH / "well",
        "keep": ["WELL测试看板.html", "dashboard.config.yaml", "warehouse.db"],
        "keep_dirs": ["artifacts"],
        "title": "WELL 资源分析看板（官方案例模板演示）",
        "data": "（合成数据，用于验证渲染链路）",
        "data_desc": "按 WELL 案例脚本结构生成的 1.2 万行合成数据（生命周期状态/地市/区县/入网年份/坐标）",
        "points": [
            "16 个组件，闸门 A/B/C 全绿",
            "4 个 KPI（含口径悬停）+ 生命周期构成 + 地市/区县分布 + 码值字典表",
            "L2 四维下钻 + L3 逐条明细",
            "⚠ 由官方案例模板 + 合成数据生成，用于展示产出形态，非真实业务结论",
        ],
    },
    "3_ODF看板演示": {
        "src": DASH / "odf",
        "keep": ["ODF测试看板.html", "dashboard.config.yaml", "warehouse.db"],
        "keep_dirs": ["artifacts"],
        "title": "ODF 光配线架资源看板（官方案例模板演示）",
        "data": "（合成数据，用于验证渲染链路）",
        "data_desc": "按 ODF 案例脚本结构生成的 8,000 行合成数据（生命周期状态/设备类型/地市/区县/坐标/NFC）",
        "points": [
            "11 个组件，闸门通过（1 条布局警告，警告级放行）",
            "4 个 KPI + 构成 + 分布 + 码值字典表",
            "L2 三维下钻 + L3 逐条明细",
            "⚠ 由官方案例模板 + 合成数据生成，用于展示产出形态，非真实业务结论",
        ],
    },
}

README_TMPL = """# {title}

这是一个**自包含分享包**：直接把这个文件夹（或同名 zip）发出去，对方双击 HTML 就能看，不需要联网、不需要装软件。

## 一、先看这个

| 文件 | 说明 |
|---|---|
| `{main_html}` | **可视化看板**（单文件离线网页，双击用浏览器打开）|
{extra_rows}

## 二、这个包演示了什么

{points}

## 三、数据来源

- 数据文件：`{data}`
- 说明：{data_desc}
- 实训数据集完整清单见本仓库的 `_datasets` 目录说明

## 四、怎么打开

1. **看板**：双击 `{main_html}` 即可。图表库已内嵌在文件里，离线可用。
   - 交互：KPI 卡鼠标悬停看口径（分子/分母）→ 点图表下钻 → 再点到逐条明细
2. **总结报告**：双击 `.docx` 用 Word 打开。
3. **数仓复核**：`warehouse.db` 是 SQLite 数据库，所有看板数字都能在其中查到；口径定义见 `artifacts/口径卡.md`。

## 五、工具与出处

- 分析工具：**data-viz** Skill（AI 直读式数据分析工作流，v3.0）
- 仓库：{repo}
- 直接下载：{repo_zip}
- 版本：v3.0（AI 直读 + 用户选单 + 23 种图表；新增箱线图/正态Q-Q/帕累托/缺失值画像/相关矩阵/回归）

## 六、说明

本包内容由 data-viz 生成，用于演示「探源 → 口径拍板 → 输出选单 → 看板 → 总结报告」的完整链路。
{disclaimer}
"""

manifest = []
for name, spec in PACKAGES.items():
    dst = PKG / name
    if dst.exists():
        shutil.rmtree(dst)
    dst.mkdir(parents=True)
    copied = []
    for f in spec["keep"]:
        s = spec["src"] / f
        if s.exists():
            shutil.copy2(s, dst / f)
            copied.append(f)
    for d in spec["keep_dirs"]:
        s = spec["src"] / d
        if s.exists():
            shutil.copytree(s, dst / d)
    # 报告配图（若有）
    imgs = dst / "artifacts" / "report_img"
    # 写说明
    main_html = next((c for c in copied if c.endswith(".html")), "(未找到看板)")
    extra = [c for c in copied if not c.endswith(".html")]
    extra_rows = "\n".join(
        f"| `{c}` | " + {
            "数据总结报告.docx": "**数据总结报告**（Word，含洞察与建议）",
            "dashboard.config.yaml": "看板声明式配置（改这个就能改图）",
            "plan.json": "输出选单记录（用户选了哪些图与交付物）",
            "report_spec.json": "报告内容 spec（AI 写的叙事与结论）",
            "warehouse.db": "SQLite 数仓（所有数字可复核）",
        }.get(c, "配套文件") + " |"
        for c in extra)
    readme = README_TMPL.format(
        title=spec["title"], main_html=main_html, extra_rows=extra_rows,
        points="\n".join(f"- {p}" for p in spec["points"]),
        data=spec["data"], data_desc=spec["data_desc"],
        repo=REPO, repo_zip=REPO_ZIP,
        disclaimer=("> ⚠ 本包为演示数据生成，非真实业务结论。\n"
                    if "演示" in spec["title"] else
                    "> 本包基于示例数据集（中文 GBK 订单表），用于演示分析链路。\n"))
    (dst / "README.md").write_text(readme, encoding="utf-8")
    # 打包
    z = PKG / f"{name}.zip"
    if z.exists():
        z.unlink()
    with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED) as zf:
        for p in sorted(dst.rglob("*")):
            if p.is_file():
                zf.write(p, pathlib.Path(name) / p.relative_to(dst))
    manifest.append((name, len(copied), z.stat().st_size / 1024 / 1024))

print("=== 分享包 ===")
for n, c, mb in manifest:
    d = PKG / n
    files = [p for p in d.rglob("*") if p.is_file()]
    print(f"  {n:<18} {len(files):>2} 文件（含 README）  zip {mb:>5.2f} MB")
print(f"\n位置: {PKG}")
