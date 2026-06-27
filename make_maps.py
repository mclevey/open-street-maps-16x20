"""
Minimalist roads-only city maps from OpenStreetMap (faithful vector data).
One shared style across all cities. Graphs are cached locally as .graphml so
re-running only re-downloads cities you've changed.

SETUP (once):
    pip install osmnx matplotlib
RUN:
    python make_maps.py
Outputs land in ./out/ as 300 dpi PNGs at full print size, plus a contact sheet.

FRAME: Umbra Gallery frame = 16x20" full-bleed, OR 11x14" with the mat.
Pick one below in PRINT_SIZE. Everything else (ratio, dpi, cropping) follows from it.
"""
import os, math, warnings
import osmnx as ox
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

warnings.filterwarnings("ignore")
ox.settings.use_cache = True
ox.settings.log_console = False

HERE  = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, "cache"); os.makedirs(CACHE, exist_ok=True)
OUT   = os.path.join(HERE, "out");   os.makedirs(OUT,   exist_ok=True)

# ---------------------------------------------------------------------------
# PRINT SIZE  — drives aspect ratio + resolution.
#   (16, 20) = full-bleed, no mat   |   (11, 14) = matted
# ---------------------------------------------------------------------------
PRINT_W, PRINT_H = 16, 20
DPI = 300
RATIO = PRINT_H / PRINT_W          # portrait height:width

# ---------------------------------------------------------------------------
# SHARED STYLE
# ---------------------------------------------------------------------------
STYLE = {
    "bg":      "#f4f1ea",   # off-white ground
    "ink":     "#1b1b1b",   # near-black roads (try #333 for softer charcoal)
    "label":   "#1b1b1b",
    "network": "drive",     # drivable roads only -> no footpath noise
    "show_label": True,     # city name + coords at bottom
    "show_coords": True,
}

# Global line-weight multiplier. Tuned for 16x20. Nudge up/down to taste.
LINE_SCALE = 1.55

# road-class -> base linewidth (hierarchy that makes it read as a real map)
WIDTHS = {
    "motorway": 1.7, "motorway_link": 1.0,
    "trunk":    1.5, "trunk_link":    0.9,
    "primary":  1.15,"primary_link":  0.8,
    "secondary":0.9, "secondary_link":0.7,
    "tertiary": 0.7, "tertiary_link": 0.6,
    "residential": 0.42, "living_street": 0.42,
    "unclassified": 0.42, "service": 0.0,   # service roads hidden = cleaner
}
DEFAULT_W = 0.42

# ---------------------------------------------------------------------------
# CITIES — (name, lat, lon, footprint WIDTH in metres). Height derives from RATIO.
# Smaller width = zoomed in = denser cities stay legible (equal ink density).
# Tune `w` per city after viewing the contact sheet.
# ---------------------------------------------------------------------------
CITIES = [
    # ("St. John's",         47.5660,  -52.7126, 6800),
    # ("Hamilton",           43.2557,  -79.8711, 6200),
    ("Toronto",            43.6532,  -79.3832, 3600),
    # ("Kitchener-Waterloo", 43.4580,  -80.5060, 9500),
    # ("Vancouver",          49.2827, -123.1207, 4500),
    # ("Cardiff",            51.4816,   -3.1791, 6200),
    # ("Berlin",             52.5200,   13.4050, 4000),
    # ("Glasgow",            55.8617,   -4.2583, 5500),
    # ("Austin",             30.2672,  -97.7431, 6500),
    # ("Melbourne",         -37.8136,  144.9631, 5500),
]
CITIES_BY_NAME = {c[0]: (c[1], c[2]) for c in CITIES}

def safe_name(name):
    return name.replace(" ", "_").replace(".", "").replace("'", "")

def bbox_from_point(lat, lon, w_m):
    h_m = w_m * RATIO
    dlat = (h_m / 2) / 111320.0
    dlon = (w_m / 2) / (111320.0 * math.cos(math.radians(lat)))
    return (lon - dlon, lat - dlat, lon + dlon, lat + dlat)  # W,S,E,N (osmnx v2)

def get_graph(name, lat, lon, w_m):
    path = os.path.join(CACHE, f"{safe_name(name)}_{int(w_m)}.graphml")
    if os.path.exists(path):
        return ox.load_graphml(path)
    bbox = bbox_from_point(lat, lon, w_m)
    G = ox.graph_from_bbox(bbox, network_type=STYLE["network"],
                           truncate_by_edge=True, retain_all=True)
    ox.save_graphml(G, path)
    return G

def edge_widths(G):
    out = []
    for _, _, d in G.edges(keys=False, data=True):
        hw = d.get("highway", "")
        if isinstance(hw, list):
            hw = hw[0]
        out.append(WIDTHS.get(hw, DEFAULT_W) * LINE_SCALE)
    return out

def render(name, G):
    fig, ax = ox.plot_graph(
        G, show=False, close=False,
        bgcolor=STYLE["bg"], node_size=0,
        edge_color=STYLE["ink"], edge_linewidth=edge_widths(G),
    )
    fig.set_size_inches(PRINT_W, PRINT_H)
    # ox.plot_graph leaves the figure patch off, so the area outside the map axes
    # (our label strip) saves as transparent. Lay down an explicit opaque cream
    # rectangle across the whole figure to guarantee a uniform ground.
    import matplotlib.patches as mpatches
    fig.patch.set_visible(True); fig.patch.set_alpha(1.0)
    fig.set_facecolor(STYLE["bg"])
    fig.add_artist(mpatches.Rectangle((0, 0), 1, 1, transform=fig.transFigure,
                   facecolor=STYLE["bg"], edgecolor="none", zorder=-100))
    ax.set_facecolor(STYLE["bg"])
    ax.set_aspect("auto")
    ax.margins(0)
    ax.set_position([0, 0.075, 1, 0.925])   # map fills top 92.5%; bottom strip = label

    # Labels in ABSOLUTE FIGURE coords so they sit on the cream ground (0..1 = inside canvas)
    if STYLE["show_label"]:
        fig.text(0.5, 0.046, name.upper(), ha="center", va="center",
                 color=STYLE["label"], fontsize=PRINT_W * 2.4,
                 fontweight="medium", family="DejaVu Sans")
        if STYLE["show_coords"]:
            lat, lon = CITIES_BY_NAME[name]
            sub = (f"{abs(lat):.4f}\u00b0{'N' if lat>=0 else 'S'}   /   "
                   f"{abs(lon):.4f}\u00b0{'E' if lon>=0 else 'W'}")
            fig.text(0.5, 0.022, sub, ha="center", va="center",
                     color=STYLE["label"], alpha=0.6,
                     fontsize=PRINT_W * 0.95, family="DejaVu Sans")

    out = os.path.join(OUT, f"{safe_name(name)}.png")
    fig.savefig(out, dpi=DPI, facecolor=STYLE["bg"], edgecolor="none",
                transparent=False)   # exact size, fully opaque cream
    plt.close(fig)
    return out

def contact_sheet(paths):
    from PIL import Image
    n = len(paths); cols = 4; rows = (n + cols - 1) // cols
    fig, axs = plt.subplots(rows, cols, figsize=(5*cols, 6*rows))
    axs = axs.ravel()
    for i, p in enumerate(paths):
        im = Image.open(p); im.thumbnail((900, 1200))   # downsample = memory-safe
        axs[i].imshow(im); axs[i].axis("off")
        axs[i].set_title(os.path.basename(p).replace(".png", ""), fontsize=12)
    for j in range(len(paths), len(axs)):
        axs[j].axis("off")
    fig.patch.set_facecolor("#e9e6df"); plt.tight_layout()
    cs = os.path.join(OUT, "_contact_sheet.png")
    plt.savefig(cs, dpi=90, facecolor="#e9e6df"); plt.close(fig)
    return cs

if __name__ == "__main__":
    print(f"Rendering at {PRINT_W}x{PRINT_H}\" @ {DPI}dpi "
          f"({PRINT_W*DPI}x{PRINT_H*DPI}px), line scale {LINE_SCALE}")
    paths = []
    for name, lat, lon, w in CITIES:
        print(f"  {name} ...", flush=True)
        G = get_graph(name, lat, lon, w)
        paths.append(render(name, G))
    contact_sheet(paths)
    print(f"DONE -> {OUT}")
