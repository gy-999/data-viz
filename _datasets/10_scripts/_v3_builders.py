        # ---------- 统计分析扩展（v4）：箱线图 / 正态QQ / 帕累托 / 缺失值 / 相关矩阵 / 回归 ----------
        if t == "box":
            import statistics as _st
            dim, vcol, filt = d["dimension"], d["column"], (f' WHERE {d["filter"]}' if d.get("filter") else "")
            rows = q(conn, f'SELECT "{dim}" AS dm, "{vcol}" AS v FROM "{d["table"]}" '
                           f'WHERE "{dim}" IS NOT NULL AND "{vcol}" IS NOT NULL{filt}')
            buckets = {}
            for r in rows:
                try: buckets.setdefault(str(r["dm"]), []).append(float(r["v"]))
                except (TypeError, ValueError): pass
            groups, outliers_out = [], []
            for name, vals in buckets.items():
                if len(vals) < 2: continue
                vals.sort(); n = len(vals)
                def _q(p):
                    pos = (n - 1) * p; lo = int(pos); hi = min(lo + 1, n - 1); frac = pos - lo
                    return vals[lo] * (1 - frac) + vals[hi] * frac
                q1, med, q3 = _q(.25), _q(.5), _q(.75); iqr = q3 - q1
                lo_f, hi_f = q1 - 1.5 * iqr, q3 + 1.5 * iqr
                inside = [v for v in vals if lo_f <= v <= hi_f]
                outs = [v for v in vals if v < lo_f or v > hi_f]
                mean = sum(vals) / n
                groups.append({"name": name, "min": round(min(inside), 6), "q1": round(q1, 6),
                               "median": round(med, 6), "q3": round(q3, 6), "max": round(max(inside), 6),
                               "n": n, "outliers": len(outs),
                               "mean": round(mean, 6), "std": round(_st.pstdev(vals), 6),
                               "cv": round(_st.pstdev(vals) / mean, 4) if mean else None})
                outliers_out += [{"g": name, "v": round(v, 6)} for v in outs[:40]]
            groups.sort(key=lambda g: -g["median"])
            groups = groups[:d.get("top", 10)]
            keep = {g["name"] for g in groups}
            return {"groups": groups, "outliers_pts": [o for o in outliers_out if o["g"] in keep][:300],
                    "y_label": col_cn(vcol), "x_label": col_cn(dim),
                    "outlier_total": sum(g["outliers"] for g in groups)}
        if t == "qq":
            import statistics as _st
            vcol = d["column"]; filt = f' WHERE {d["filter"]}' if d.get("filter") else ""
            vals = []
            for r in q(conn, f'SELECT "{vcol}" AS v FROM "{d["table"]}" WHERE "{vcol}" IS NOT NULL{filt}'):
                try: vals.append(float(r["v"]))
                except (TypeError, ValueError): pass
            if len(vals) < 8:
                return {"points": [], "ref": [], "n": len(vals), "note": "样本量不足以做正态Q-Q（需 >= 8）"}
            vals.sort(); n = len(vals); mu = sum(vals) / n; sd = _st.pstdev(vals)
            pts = []
            for i, v in enumerate(vals, start=1):
                p = (i - 0.375) / (n + 0.25)
                pts.append([round(_norm_ppf(p), 5), round(v, 6)])
            zs = [p[0] for p in pts]
            zmin, zmax = min(zs), max(zs)
            slope = sd if sd else 1
            ref = [[round(zmin, 5), round(mu + slope * zmin, 6)], [round(zmax, 5), round(mu + slope * zmax, 6)]]
            skew = round(sum(((v - mu) / sd) ** 3 for v in vals) / n, 4) if sd else None
            kurt = round(sum(((v - mu) / sd) ** 4 for v in vals) / n - 3, 4) if sd else None
            return {"points": pts[:d.get("top", 2000)], "ref": ref, "n": n,
                    "mean": round(mu, 6), "std": round(sd, 6), "skew": skew, "kurtosis": kurt,
                    "x_label": "理论分位数", "y_label": col_cn(vcol),
                    "note": "样本量 > 5000，参考偏度/峰度判断" if n > 5000 else ""}
        if t == "pareto":
            m = metrics.get(d.get("metric"))
            vcol, _filt, order = _agg_table(d, m)
            rows = q(conn, f'SELECT "{d["dimension"]}" AS dm, "{vcol}" AS v FROM "{d["table"]}" '
                          f'WHERE "{d["dimension"]}" IS NOT NULL{order} LIMIT {d.get("top", 12)}')
            labels = [str(r["dm"]) for r in rows]
            values = [r["v"] or 0 for r in rows]
            total = sum(v for v in values if isinstance(v, (int, float)))
            cum, run = [], 0.0
            for v in values:
                run += v if isinstance(v, (int, float)) else 0
                cum.append(round(run / total * 100, 2) if total else 0)
            vital_idx = next((i for i, cv in enumerate(cum) if cv >= 80), None)
            return {"title": d.get("label") or f'{(m or {}).get("name", "")} 帕累托分析',
                    "unit": (m or {}).get("unit", ""), "labels": labels,
                    "values": values, "cum": cum, "total": total,
                    "vital_label": (labels[vital_idx] if vital_idx is not None else None),
                    "vital_count": (vital_idx + 1 if vital_idx is not None else None)}
        if t == "missing":
            rows = q(conn, f'SELECT * FROM "{d["table"]}"')
            if not rows:
                return {"labels": [], "overall": [], "counts": [], "group_col": None}
            gcol = d.get("dimension")
            groups = {}
            for r in rows:
                key = str(r.get(gcol)) if gcol else "全部"
                groups.setdefault(key, []).append(r)
            labels, rate, cnt = [], [], []
            for key, rs in groups.items():
                nn = len(rs); cells = nn * len(rs[0]); miss = 0
                for r in rs:
                    for v in r.values():
                        if v is None or (isinstance(v, str) and v.strip() == ""): miss += 1
                labels.append(key); cnt.append(nn)
                rate.append(round(miss / cells * 100, 2) if cells else 0.0)
            order = sorted(range(len(labels)), key=lambda i: -rate[i])[:d.get("top", 12)]
            overall = []
            for col in rows[0].keys():
                nm = sum(1 for r in rows
                         if r.get(col) is None or (isinstance(r.get(col), str) and str(r.get(col)).strip() == ""))
                overall.append({"col": col_cn(col), "key": col, "rate": round(nm / len(rows) * 100, 2), "n": nm})
            overall.sort(key=lambda x: -x["rate"])
            return {"labels": [labels[i] for i in order], "rates": [rate[i] for i in order],
                    "counts": [cnt[i] for i in order],
                    "overall": overall[:d.get("col_top", 15)],
                    "group_col": col_cn(gcol) if gcol else None}
        if t == "corr":
            cols = d.get("columns") or []
            rows = q(conn, f'SELECT {", ".join(chr(34)+x+chr(34) for x in cols)} FROM "{d["table"]}"')
            pairs = []
            for r in rows:
                vals, ok = [], True
                for x in cols:
                    try: vals.append(float(r[x]))
                    except (TypeError, ValueError): ok = False; break
                if ok: pairs.append(vals)
            method = (d.get("method") or "pearson").lower()
            def _rank(seq):
                idx = sorted(range(len(seq)), key=lambda i: seq[i]); rk = [0.0] * len(seq); i = 0
                while i < len(idx):
                    j = i
                    while j + 1 < len(idx) and seq[idx[j + 1]] == seq[idx[i]]: j += 1
                    avg = (i + j) / 2 + 1
                    for k in range(i, j + 1): rk[idx[k]] = avg
                    i = j + 1
                return rk
            def _pearson(a, b):
                n = len(a)
                if n < 3: return None
                ma_, mb_ = sum(a) / n, sum(b) / n
                num = sum((a[i] - ma_) * (b[i] - mb_) for i in range(n))
                da = sum((x - ma_) ** 2 for x in a) ** 0.5
                db = sum((x - mb_) ** 2 for x in b) ** 0.5
                return round(num / (da * db), 4) if da and db else None
            series = list(zip(*pairs)) if pairs else [[] for _ in cols]
            if method == "spearman":
                series = [_rank(list(x)) for x in series]
            matrix, labels = [], [col_cn(c) for c in cols]
            for i in range(len(cols)):
                matrix.append([1.0 if i == j else _pearson(list(series[i]), list(series[j])) for j in range(len(cols))])
            flat = [abs(v) for row in matrix for v in row if isinstance(v, (int, float)) and v != 1.0]
            return {"labels": labels, "keys": cols, "matrix": matrix, "method": method,
                    "n": len(pairs), "max_abs": round(max(flat), 4) if flat else None,
                    "title": d.get("label") or f"{'斯皮尔曼' if method == 'spearman' else '皮尔逊'}相关矩阵"}
        if t == "regress":
            xcol, ycol = d["x"], d["y"]
            filt = f' WHERE {d["filter"]}' if d.get("filter") else ""
            rows = q(conn, f'SELECT "{xcol}" AS x, "{ycol}" AS y FROM "{d["table"]}" '
                          f'WHERE "{xcol}" IS NOT NULL AND "{ycol}" IS NOT NULL{filt} LIMIT {d.get("top", 2000)}')
            pts = []
            for r in rows:
                try: pts.append([float(r["x"]), float(r["y"])])
                except (TypeError, ValueError): pass
            if len(pts) < 3:
                return {"points": pts, "n": len(pts), "note": "样本量不足以拟合（需 >= 3）"}
            n = len(pts); sx = sum(p[0] for p in pts); sy = sum(p[1] for p in pts)
            sxx = sum(p[0] ** 2 for p in pts); sxy = sum(p[0] * p[1] for p in pts)
            den = n * sxx - sx * sx
            slope = (n * sxy - sx * sy) / den if den else 0.0
            intercept = (sy - slope * sx) / n
            my = sy / n
            ss_tot = sum((p[1] - my) ** 2 for p in pts)
            ss_res = sum((p[1] - (intercept + slope * p[0])) ** 2 for p in pts)
            r2 = round(1 - ss_res / ss_tot, 4) if ss_tot else None
            r = round((1 - ss_res / ss_tot) ** 0.5, 4) if ss_tot and ss_res <= ss_tot else None
            xmin = min(p[0] for p in pts); xmax = max(p[0] for p in pts)
            return {"points": pts, "n": n, "r2": r2, "r": r,
                    "slope": round(slope, 6), "intercept": round(intercept, 6),
                    "fit": [[round(xmin, 6), round(intercept + slope * xmin, 6)],
                            [round(xmax, 6), round(intercept + slope * xmax, 6)]],
                    "x_label": col_cn(xcol), "y_label": col_cn(ycol),
                    "title": d.get("label") or f"{col_cn(ycol)} 与 {col_cn(xcol)} 回归"}
