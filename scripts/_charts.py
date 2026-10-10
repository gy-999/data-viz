import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
plt.rcParams["font.sans-serif"] = ["Microsoft YaHei"]
plt.rcParams["axes.unicode_minus"] = False

def save_pie(labels, values, title, out, total_label=None):
    fig, ax = plt.subplots(figsize=(7, 4.2), dpi=150)
    cs = ["#5B8FF9","#61DDAA","#65789B","#F6BD16","#7262fd","#F08BB4","#86909c","#f6bd16"]
    ax.pie(values, labels=labels, autopct="%1.1f%%", startangle=90, colors=cs[:len(labels)],
           pctdistance=0.78, wedgeprops=dict(width=0.42, edgecolor="white", linewidth=2),
           textprops=dict(fontsize=10))
    if total_label: ax.text(0, 0, total_label, ha="center", va="center", fontsize=14, fontweight="bold")
    ax.set_title(title, fontsize=12, fontweight="bold")
    fig.tight_layout(); fig.savefig(out, bbox_inches="tight"); plt.close(fig)

def save_barh(labels, values, title, out, color="#5B8FF9"):
    fig, ax = plt.subplots(figsize=(7, 4.2), dpi=150)
    l2 = labels[::-1]; v2 = values[::-1]
    bars = ax.barh(l2, v2, color=color, height=0.6)
    mx = max(v2) if v2 else 1
    for b, v in zip(bars, v2): ax.text(v + mx*0.01, b.get_y()+b.get_height()/2, format(int(v), ","), va="center", fontsize=9)
    ax.set_title(title, fontsize=12, fontweight="bold")
    ax.spines[["top","right"]].set_visible(False)
    fig.tight_layout(); fig.savefig(out, bbox_inches="tight"); plt.close(fig)

def save_line(labels, values, title, out):
    fig, ax = plt.subplots(figsize=(7, 3.8), dpi=150)
    ax.plot(labels, values, marker="o", markersize=4, linewidth=2.2, color="#1456f0")
    ax.fill_between(labels, values, color="#1456f0", alpha=0.08)
    ax.set_title(title, fontsize=12, fontweight="bold")
    ax.spines[["top","right"]].set_visible(False)
    ax.tick_params(labelsize=9)
    fig.tight_layout(); fig.savefig(out, bbox_inches="tight"); plt.close(fig)