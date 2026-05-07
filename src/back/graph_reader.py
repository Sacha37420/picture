"""
graph_reader.py – GraphReader class and GraphConfig dataclass.

Reads text-based data files and renders them as matplotlib figures
that are added to a MultiImage as regular Image objects.

Supported input formats
-----------------------
  .csv / .tsv    Tabular data – separator auto-detected.
  .json          Custom chart schema (see below).
  .xlsx / .xls   Excel spreadsheet (one image per sheet, requires openpyxl).
  .rec           Text recording file (space / comma / tab separated).
  .sec           Text data file (security / sensor records), same parsing as CSV.
  .bin           Binary data – tries NumPy .npy first, then raw float64 columns.

JSON chart schema
-----------------
  {
    "type":    "auto|bar|line|scatter|pie|histogram|area",   # optional
    "title":   "My Chart",                                   # optional
    "x":       "column_name",                                # optional
    "y":       "column_name"  OR  ["col1", "col2"],          # optional
    "x_label": "...",                                        # optional
    "y_label": "...",                                        # optional
    "data":    [{"col": val, ...}, ...],                     # inline rows
    "source":  "relative/path/to/data.csv"                  # OR external CSV
  }
"""
from __future__ import annotations

import io
import json
import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Union

import numpy as np

from .image import Image
from .multiimage import MultiImage

# ------------------------------------------------------------------ #
# Constants exported to the UI                                         #
# ------------------------------------------------------------------ #

GRAPH_EXTENSIONS = frozenset({
    ".csv", ".tsv", ".json", ".xlsx", ".xls",
    ".rec", ".sec", ".bin",
})

# Curated matplotlib style list (names valid in mpl ≥ 3.6)
GRAPH_STYLES: List[str] = [
    "default",
    "seaborn-v0_8",
    "seaborn-v0_8-darkgrid",
    "seaborn-v0_8-whitegrid",
    "seaborn-v0_8-paper",
    "seaborn-v0_8-talk",
    "ggplot",
    "bmh",
    "fivethirtyeight",
    "dark_background",
    "Solarize_Light2",
    "tableau-colorblind10",
]

CHART_TYPES: List[str] = [
    "auto", "bar", "line", "scatter", "pie", "histogram", "area"
]

COLORMAPS: List[str] = [
    "tab10", "tab20", "Set1", "Set2", "Set3",
    "Paired", "Dark2", "viridis", "plasma", "inferno",
]


# ------------------------------------------------------------------ #
# Configuration dataclass                                              #
# ------------------------------------------------------------------ #

@dataclass
class GraphConfig:
    """
    Rendering parameters for chart generation.

    Parameters
    ----------
    chart_type : str
        One of CHART_TYPES.  ``"auto"`` lets the reader choose.
    style : str
        matplotlib style name (see GRAPH_STYLES).
    figsize : tuple[float, float]
        Figure width × height in inches.
    dpi : int
        Output resolution (pixels = figsize * dpi).
    colormap : str
        matplotlib colormap name used to colour data series.
    title : str
        Default chart title (overridden by JSON ``"title"`` field).
    x_label : str
        Override for the X-axis label.
    y_label : str
        Override for the Y-axis label.
    grid : bool
        Whether to show a grid.
    """
    chart_type:     str = "auto"
    style:          str = "seaborn-v0_8"
    figsize:        Tuple[float, float] = (10.0, 6.0)
    dpi:            int = 150
    colormap:       str = "tab10"
    title:          str = ""
    x_label:        str = ""
    y_label:        str = ""
    grid:           bool = True
    overlap_hints:  bool = False
    x_col:          Optional[str] = None   # user-forced X-axis column (None = auto)
    x_min:          Optional[float] = None # forced X-axis minimum (None = auto)
    x_max:          Optional[float] = None # forced X-axis maximum (None = auto)
    y_min:          Optional[float] = None # forced Y-axis minimum (None = auto)
    y_max:          Optional[float] = None # forced Y-axis maximum (None = auto)


# ------------------------------------------------------------------ #
# Overlap-hint constants                                               #
# ------------------------------------------------------------------ #

# Cycling line dash patterns (line / area / fallback charts)
_LINE_STYLES = ["-", "--", "-.", ":"]

# Cycling marker shapes used when overlap_hints is active
_MARKERS = ["o", "s", "^", "D", "v", "p", "*", "h"]

# Hatch patterns for bar charts
_HATCHES = ["", "/", "\\\\", "|", "-", "+", "x", "o", "*"]

# ------------------------------------------------------------------ #
# Internal rendering helpers                                           #
# ------------------------------------------------------------------ #

def _get_colors(n: int, colormap: str) -> list:
    """Return *n* colours from *colormap*."""
    import matplotlib.cm as cm
    import matplotlib.colors as mcolors
    try:
        cmap = cm.get_cmap(colormap)
        return [mcolors.to_hex(cmap(i / max(n - 1, 1))) for i in range(n)]
    except Exception:
        return ["#89b4fa", "#a6e3a1", "#f38ba8", "#f9e2af",
                "#cba6f7", "#fab387", "#74c7ec", "#94e2d5"][:n]


def _safe_style(style: str) -> str:
    """Return *style* if available in the current matplotlib, else 'default'."""
    import matplotlib.pyplot as plt
    if style in plt.style.available:
        return style
    # Try without the version suffix (e.g. seaborn-v0_8 → seaborn)
    bare = style.replace("-v0_8", "")
    if bare in plt.style.available:
        return bare
    return "default"


def _auto_chart_type(df, x_col: Optional[str], y_cols: List[str]) -> str:
    """Heuristically determine the best chart type."""
    import pandas as pd

    if not y_cols:
        return "bar"

    # Single column, no x → histogram
    if x_col is None and len(y_cols) == 1:
        return "histogram"

    if x_col and x_col in df.columns:
        # Date/time x → line
        try:
            pd.to_datetime(df[x_col], infer_datetime_format=True)
            return "line"
        except Exception:
            pass
        # Categorical x with few unique values → bar
        if df[x_col].dtype == object and df[x_col].nunique() <= 30:
            if len(y_cols) == 1:
                return "bar"
            return "line"

    # Two numeric columns → scatter
    numeric = df.select_dtypes(include="number").columns.tolist()
    if len(numeric) == 2 and x_col in numeric:
        return "scatter"

    return "line"


def _pick_columns(
    df,
    x_override: Optional[str],
    y_override: Optional[Union[str, List[str]]],
) -> Tuple[Optional[str], List[str]]:
    """Return (x_col, y_cols) picking sensible defaults when not overridden."""
    import pandas as pd

    numeric = df.select_dtypes(include="number").columns.tolist()
    non_numeric = df.select_dtypes(exclude="number").columns.tolist()

    # Detect datetime-like columns
    datetime_cols = []
    for col in non_numeric:
        try:
            pd.to_datetime(df[col], infer_datetime_format=True)
            datetime_cols.append(col)
        except Exception:
            pass

    # X column
    if x_override and x_override in df.columns:
        x_col = x_override
    elif datetime_cols:
        x_col = datetime_cols[0]
    elif non_numeric:
        x_col = non_numeric[0]
    else:
        x_col = None  # will use the index

    # Y columns
    if y_override:
        y_cols = [y_override] if isinstance(y_override, str) else list(y_override)
        y_cols = [c for c in y_cols if c in df.columns]
    else:
        y_cols = [c for c in numeric if c != x_col]
        if not y_cols:
            y_cols = numeric[:1]  # fallback

    return x_col, y_cols


def _render_figure(df, config: GraphConfig, x_col, y_cols,
                   title: str = "", x_label: str = "", y_label: str = "") -> np.ndarray:
    """
    Render a matplotlib figure from a DataFrame and return an RGBA ndarray.
    """
    import matplotlib
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_agg import FigureCanvasAgg

    chart_type = config.chart_type
    if chart_type == "auto":
        chart_type = _auto_chart_type(df, x_col, y_cols)

    style = _safe_style(config.style)
    colors = _get_colors(max(len(y_cols), 1), config.colormap)

    with matplotlib.style.context(style):
        fig = Figure(figsize=config.figsize, dpi=config.dpi)
        canvas = FigureCanvasAgg(fig)
        ax = fig.add_subplot(111)

        t = title or config.title or ""
        xl = x_label or config.x_label or (x_col or "")
        yl = y_label or config.y_label or (", ".join(y_cols) if y_cols else "")

        oh = config.overlap_hints   # shorthand

        # ── bar ──────────────────────────────────────────────────── #
        if chart_type == "bar":
            x_data = df[x_col].astype(str) if x_col else df.index.astype(str)
            x_pos = np.arange(len(x_data))
            n = len(y_cols)
            w = 0.8 / n
            for i, (col, color) in enumerate(zip(y_cols, colors)):
                offset = (i - n / 2 + 0.5) * w
                hatch = _HATCHES[i % len(_HATCHES)] if oh else ""
                ax.bar(x_pos + offset, df[col], width=w, label=col,
                       color=color, hatch=hatch,
                       alpha=0.75 if oh else 1.0,
                       edgecolor="white" if oh else color)
            ax.set_xticks(x_pos)
            ax.set_xticklabels(x_data, rotation=45, ha="right")
            if n > 1:
                ax.legend()

        # ── line / area ───────────────────────────────────────────── #
        elif chart_type in ("line", "area"):
            import pandas as pd
            x_data = df[x_col] if x_col else df.index
            # Try to parse dates for nicer x-axis
            if x_col:
                try:
                    x_data = pd.to_datetime(df[x_col], infer_datetime_format=True)
                    fig.autofmt_xdate()
                except Exception:
                    pass

            # Marker step: one marker every ~50 points to avoid clutter
            n_pts = len(df)
            m_every = max(1, n_pts // 50)

            for i, (col, color) in enumerate(zip(y_cols, colors)):
                ls     = _LINE_STYLES[i % len(_LINE_STYLES)] if oh else "-"
                marker = _MARKERS[i % len(_MARKERS)]         if oh else None
                alpha  = 0.80                                if oh else 1.0
                lw     = 1.8

                # ① halo: wide, low-alpha line drawn first (below)
                if oh:
                    ax.plot(x_data, df[col], color=color,
                            linewidth=lw + 4, alpha=0.18, linestyle="-",
                            zorder=1)

                # ② main line
                ax.plot(x_data, df[col], label=col, color=color,
                        linestyle=ls, linewidth=lw, alpha=alpha,
                        marker=marker,
                        markevery=m_every if oh else None,
                        markersize=5 if oh else 3,
                        zorder=2)

                if chart_type == "area":
                    ax.fill_between(x_data, df[col],
                                    alpha=0.18 if oh else 0.25, color=color)
            if len(y_cols) > 1:
                ax.legend()

        # ── scatter ───────────────────────────────────────────────── #
        elif chart_type == "scatter":
            y_col = y_cols[0] if y_cols else df.columns[-1]
            x_data = df[x_col] if x_col else df.index
            if oh:
                # Jitter to separate perfectly overlapping points
                rng   = np.random.default_rng(42)
                x_arr = np.asarray(x_data, dtype=float)
                y_arr = np.asarray(df[y_col], dtype=float)
                jitter_scale = (x_arr.max() - x_arr.min() + 1e-9) * 0.005
                x_arr = x_arr + rng.normal(0, jitter_scale, len(x_arr))
                ax.scatter(x_arr, y_arr, color=colors[0],
                           alpha=0.55, s=35, edgecolors=colors[0], linewidths=0.5)
            else:
                ax.scatter(x_data, df[y_col], color=colors[0], alpha=0.7, s=30)
            xl = xl or (x_col or "Index")
            yl = yl or y_col

        # ── pie ───────────────────────────────────────────────────── #
        elif chart_type == "pie":
            y_col = y_cols[0] if y_cols else df.columns[-1]
            labels = df[x_col].astype(str) if x_col else df.index.astype(str)
            ax.pie(df[y_col].abs(), labels=labels,
                   colors=_get_colors(len(df), config.colormap),
                   autopct="%1.1f%%", startangle=90)
            ax.axis("equal")
            xl = ""
            yl = ""

        # ── histogram ─────────────────────────────────────────────── #
        elif chart_type == "histogram":
            col = y_cols[0] if y_cols else df.select_dtypes(include="number").columns[0]
            if oh and len(y_cols) > 1:
                # Overlay histograms with per-series alpha so overlaps show
                for i, (c, color) in enumerate(zip(y_cols, colors)):
                    ax.hist(df[c].dropna(), bins="auto", label=c,
                            color=color, alpha=0.50,
                            hatch=_HATCHES[i % len(_HATCHES)],
                            edgecolor="white")
                ax.legend()
            else:
                ax.hist(df[col].dropna(), bins="auto",
                        color=colors[0], alpha=0.85, edgecolor="white")
            xl = xl or col
            yl = yl or "Fréquence"

        # ── fallback ──────────────────────────────────────────────── #
        else:
            x_data = df[x_col] if x_col else df.index
            for col, color in zip(y_cols, colors):
                ax.plot(x_data, df[col], label=col, color=color)
            if len(y_cols) > 1:
                ax.legend()

        if t:
            ax.set_title(t, pad=12)
        if xl:
            ax.set_xlabel(xl)
        if yl:
            ax.set_ylabel(yl)
        if config.grid and chart_type not in ("pie",):
            ax.grid(True, alpha=0.3)

        # ── forced axis limits ────────────────────────────────────── #
        if chart_type not in ("pie",):
            xlim_lo = config.x_min
            xlim_hi = config.x_max
            if xlim_lo is not None or xlim_hi is not None:
                cur_lo, cur_hi = ax.get_xlim()
                ax.set_xlim(
                    xlim_lo if xlim_lo is not None else cur_lo,
                    xlim_hi if xlim_hi is not None else cur_hi,
                )
            ylim_lo = config.y_min
            ylim_hi = config.y_max
            if ylim_lo is not None or ylim_hi is not None:
                cur_lo, cur_hi = ax.get_ylim()
                ax.set_ylim(
                    ylim_lo if ylim_lo is not None else cur_lo,
                    ylim_hi if ylim_hi is not None else cur_hi,
                )

        fig.tight_layout()
        canvas.draw()

        w, h = canvas.get_width_height()
        arr = np.frombuffer(canvas.buffer_rgba(), dtype=np.uint8).reshape(h, w, 4).copy()
    return arr


def _df_to_image(df, config: GraphConfig,
                 x_override=None, y_override=None,
                 title="", x_label="", y_label="") -> Image:
    """Convert a DataFrame to an Image using config."""
    # caller (e.g. JSON schema) takes priority; fall back to config.x_col
    x_ov = x_override if x_override is not None else config.x_col
    x_col, y_cols = _pick_columns(df, x_ov, y_override)
    arr = _render_figure(df, config, x_col, y_cols,
                         title=title, x_label=x_label, y_label=y_label)
    return Image(arr)


# ------------------------------------------------------------------ #
# Public class                                                         #
# ------------------------------------------------------------------ #

class GraphReader:
    """
    Render a text-based data file as one or more chart images and add
    them to a :class:`MultiImage`.

    If no *multiimage* is supplied a new one is created.

    Parameters
    ----------
    path : str
        Path to the data file (.csv, .tsv, .json, .xlsx, .xls).
    multiimage : MultiImage, optional
        Collection to append to.
    config : GraphConfig, optional
        Rendering configuration.  Defaults to :class:`GraphConfig()`.

    Raises
    ------
    ImportError
        If ``pandas`` or ``matplotlib`` are not installed.
    ValueError
        If the file format is not recognised or the data is empty.
    """

    def __init__(
        self,
        path: str,
        multiimage: Optional[MultiImage] = None,
        config: Optional[GraphConfig] = None,
    ) -> None:
        self.multiimage: MultiImage = (
            multiimage if multiimage is not None else MultiImage()
        )
        self._config = config or GraphConfig()
        self._load(path)

    @staticmethod
    def read_columns(path: str) -> List[str]:
        """
        Return the column names found in *path* without rendering a chart.

        Returns an empty list if the format is unsupported or an error occurs.
        """
        try:
            import pandas as pd
            ext = os.path.splitext(path)[1].lower()

            if ext in (".csv", ".tsv"):
                with open(path, "r", encoding="utf-8-sig", errors="replace") as f:
                    sample = f.read(4096)
                sep = "\t" if sample.count("\t") > sample.count(",") else ","
                return list(pd.read_csv(path, sep=sep, encoding="utf-8-sig",
                                        nrows=0).columns)

            if ext == ".json":
                with open(path, "r", encoding="utf-8") as f:
                    schema = json.load(f)
                if "source" in schema:
                    src = os.path.join(os.path.dirname(path), schema["source"])
                    return list(pd.read_csv(src, nrows=0).columns)
                if "data" in schema and schema["data"]:
                    return list(pd.DataFrame(schema["data"][:1]).columns)
                return []

            if ext in (".xlsx", ".xls"):
                try:
                    xl = pd.ExcelFile(path, engine="openpyxl")
                except Exception:
                    xl = pd.ExcelFile(path)
                cols: List[str] = []
                for sheet in xl.sheet_names:
                    for c in xl.parse(sheet, nrows=0).columns:
                        if c not in cols:
                            cols.append(c)
                return cols

            if ext in (".rec", ".sec"):
                import io as _io
                with open(path, "r", encoding="utf-8-sig", errors="replace") as f:
                    lines = [l for l in f if not l.lstrip().startswith(("#", "%"))]
                if not lines:
                    return []
                sample2 = "".join(lines[:10])
                counts = {s: sample2.count(s) for s in ("\t", ",", ";", " ")}
                sep2 = max(counts, key=counts.get)
                if sep2 == " ":
                    sep2 = r"\s+"
                return list(pd.read_csv(_io.StringIO("".join(lines)),
                                        sep=sep2, engine="python", nrows=0).columns)

            if ext == ".bin":
                try:
                    arr = np.load(path, allow_pickle=False)
                    n = 1 if arr.ndim == 1 else arr.shape[1]
                    return [f"ch_{i}" for i in range(n)]
                except Exception:
                    pass
                raw = np.fromfile(path, dtype="<f8")
                for n in (1, 2, 3, 4, 6, 8, 12, 16):
                    if raw.size % n == 0:
                        break
                else:
                    n = 1
                return [f"ch_{i}" for i in range(n)]

        except Exception:
            pass
        return []

    # ---------------------------------------------------------------- #

    def _load(self, path: str) -> None:
        self._check_imports()
        ext = os.path.splitext(path)[1].lower()
        if ext in (".csv", ".tsv"):
            self._load_csv(path)
        elif ext == ".json":
            self._load_json(path)
        elif ext in (".xlsx", ".xls"):
            self._load_excel(path)
        elif ext in (".rec", ".sec"):
            self._load_text_records(path)
        elif ext == ".bin":
            self._load_bin(path)
        else:
            raise ValueError(
                f"Unsupported graph format: '{ext}'.  "
                f"Supported: {sorted(GRAPH_EXTENSIONS)}"
            )

    @staticmethod
    def _check_imports() -> None:
        missing = []
        try:
            import pandas  # noqa: F401
        except ImportError:
            missing.append("pandas")
        try:
            import matplotlib  # noqa: F401
        except ImportError:
            missing.append("matplotlib")
        if missing:
            pkgs = " ".join(missing)
            raise ImportError(
                f"{', '.join(missing)} is required for graph reading.  "
                f"Install with:  pip install {pkgs}"
            )

    def _load_csv(self, path: str) -> None:
        import pandas as pd
        # Auto-detect separator
        with open(path, "r", encoding="utf-8-sig", errors="replace") as f:
            sample = f.read(4096)
        sep = "\t" if sample.count("\t") > sample.count(",") else ","
        df = pd.read_csv(path, sep=sep, encoding="utf-8-sig")
        if df.empty:
            raise ValueError(f"CSV file is empty: {path}")
        title = self._config.title or os.path.splitext(os.path.basename(path))[0]
        self.multiimage.add_image(_df_to_image(df, self._config, title=title))

    def _load_json(self, path: str) -> None:
        import pandas as pd
        with open(path, "r", encoding="utf-8") as f:
            schema = json.load(f)

        if not isinstance(schema, dict) or (
            "data" not in schema and "source" not in schema
        ):
            raise ValueError(
                f"JSON file '{path}' does not match the expected chart schema.  "
                "Expected keys: 'data' or 'source'."
            )

        # Load data
        if "source" in schema:
            src = os.path.join(os.path.dirname(path), schema["source"])
            df = pd.read_csv(src)
        else:
            df = pd.DataFrame(schema["data"])

        if df.empty:
            raise ValueError(f"Chart data is empty in: {path}")

        # Build a per-chart config overlay
        cfg = GraphConfig(
            chart_type = schema.get("type", self._config.chart_type),
            style      = self._config.style,
            figsize    = self._config.figsize,
            dpi        = self._config.dpi,
            colormap   = self._config.colormap,
            title      = schema.get("title", self._config.title),
            x_label    = schema.get("x_label", self._config.x_label),
            y_label    = schema.get("y_label", self._config.y_label),
            grid       = self._config.grid,
        )
        img = _df_to_image(
            df, cfg,
            x_override = schema.get("x"),
            y_override = schema.get("y"),
            title      = cfg.title,
            x_label    = cfg.x_label,
            y_label    = cfg.y_label,
        )
        self.multiimage.add_image(img)

    def _load_excel(self, path: str) -> None:
        import pandas as pd
        try:
            xl = pd.ExcelFile(path, engine="openpyxl")
        except Exception:
            xl = pd.ExcelFile(path)  # fallback to xlrd for .xls

        for sheet in xl.sheet_names:
            df = xl.parse(sheet)
            if df.empty:
                continue
            title = self._config.title or f"{os.path.splitext(os.path.basename(path))[0]} – {sheet}"
            self.multiimage.add_image(
                _df_to_image(df, self._config, title=title)
            )

    def _load_text_records(self, path: str) -> None:
        """
        Load .rec or .sec files.

        Both formats are treated as plain-text tabular data.  The
        separator is auto-detected (tab, comma, semicolon, or space).
        Lines starting with '#' or '%' are skipped as comments.
        If no header row is detected, columns are named col_0, col_1…
        """
        import pandas as pd

        with open(path, "r", encoding="utf-8-sig", errors="replace") as f:
            lines = [l for l in f if not l.lstrip().startswith(("#", "%"))]

        if not lines:
            raise ValueError(f"File is empty or contains only comments: {path}")

        sample = "".join(lines[:20])
        # Pick the most frequent delimiter
        counts = {s: sample.count(s) for s in ("\t", ",", ";", " ")}
        sep = max(counts, key=counts.get)
        if sep == " ":
            sep = r"\s+"   # collapse multiple spaces

        import io as _io
        text = "".join(lines)
        try:
            df = pd.read_csv(_io.StringIO(text), sep=sep, engine="python",
                             comment=None)
        except Exception:
            df = pd.read_csv(_io.StringIO(text), sep=",", engine="python")

        # If all column names look like integers, there was no header
        if all(str(c).lstrip("-").isdigit() for c in df.columns):
            df = pd.read_csv(_io.StringIO(text), sep=sep, engine="python",
                             header=None)
            df.columns = [f"col_{i}" for i in range(df.shape[1])]

        if df.empty:
            raise ValueError(f"No data found in: {path}")

        title = self._config.title or os.path.splitext(os.path.basename(path))[0]
        self.multiimage.add_image(_df_to_image(df, self._config, title=title))

    def _load_bin(self, path: str) -> None:
        """
        Load a .bin binary data file.

        Strategy (tried in order):
          1. NumPy .npy format (``np.load``).
          2. Raw little-endian float64 array → reshaped to ≤ 16 columns.
          3. Raw little-endian float32 array → same reshaping.

        The resulting array is wrapped in a DataFrame and rendered as a
        line chart.
        """
        import pandas as pd

        base = os.path.splitext(os.path.basename(path))[0]
        title = self._config.title or base

        # ── 1. NumPy npy ────────────────────────────────────────────
        try:
            arr = np.load(path, allow_pickle=False)
            if arr.ndim == 1:
                arr = arr.reshape(-1, 1)
            df = pd.DataFrame(arr, columns=[f"ch_{i}" for i in range(arr.shape[1])])
            self.multiimage.add_image(_df_to_image(df, self._config, title=title))
            return
        except Exception:
            pass

        # ── 2 & 3. Raw float array ───────────────────────────────────
        raw = np.fromfile(path, dtype="<f8")   # float64 little-endian
        if raw.size == 0:
            raw = np.fromfile(path, dtype="<f4").astype(np.float64)
        if raw.size == 0:
            raise ValueError(f"Binary file is empty or unreadable: {path}")

        # Guess column count: prefer power-of-2 or common sensor counts
        n_total = raw.size
        for n_cols in (1, 2, 3, 4, 6, 8, 12, 16):
            if n_total % n_cols == 0:
                break
        else:
            n_cols = 1

        arr = raw[: (n_total // n_cols) * n_cols].reshape(-1, n_cols)
        df = pd.DataFrame(arr, columns=[f"ch_{i}" for i in range(arr.shape[1])])
        self.multiimage.add_image(_df_to_image(df, self._config, title=title))
