"""
NukeRef - PureRef-like reference board for the Nuke Node Graph.

Architecture:
    Each reference is backed by a regular BackdropNode that owns the
    position, size and metadata. The image is rendered through two paths:

      1) Native: BackdropNode.setCustomIcon() puts the image on the node at
         the C++ level. This is what feeds the DAG mini-map (which lives
         inside DAG_Window's own paintEvent and we cannot inject Qt into).

      2) Overlay: a transparent QWidget glued to DAG_Window paints the
         image every frame in pure Qt, with no culling. This is what keeps
         deep zooms and partial-offscreen backdrops looking right.

    Both paths render in the same DAG-space rect, so visually they coincide
    in the main DAG. The user sees a single image; the Qt overlay covers
    the native icon. The mini-map only sees the native icon, which is the
    point.

    Resize feedback: while the user drags the backdrop's lower-right
    handle, bdwidth changes fire continuously. We stamp a timestamp on
    each such change and have the overlay paint the image at reduced
    opacity for ~200ms after the last change, then fade back to full.

Install:
    1) Drop this file into ~/.nuke/
    2) Add to ~/.nuke/menu.py:

        import nuke_ref
        nuke_ref.install()
"""

import os
import sys
import time
import nuke

# Platform branch. The Qt overlay (edge-accurate clipping, deep zoom) only
# works where the Node Graph is a stable native widget -- macOS, where the DAG
# is 'DAG_Window'. On Windows the DAG is a volatile QGLWidget whose PySide
# wrapper invalidates between accesses, so we can't attach an overlay; there
# we rely on Nuke's native setCustomIcon to draw references. Everything else
# (creation, storage, copy, metadata) is shared across platforms.
_USE_QT_OVERLAY = (sys.platform == 'darwin')

try:
    from PySide2.QtCore import Qt, QTimer, QRectF, QRunnable, QThreadPool, QEvent, QObject
    from PySide2.QtGui import QPixmap, QImage, QCursor, QPainter, QColor, QFont
    from PySide2.QtWidgets import QApplication, QWidget
    import shiboken2 as shiboken
except ImportError:
    from PySide6.QtCore import Qt, QTimer, QRectF, QRunnable, QThreadPool, QEvent, QObject
    from PySide6.QtGui import QPixmap, QImage, QCursor, QPainter, QColor, QFont
    from PySide6.QtWidgets import QApplication, QWidget
    import shiboken6 as shiboken


SUPPORTED_EXTENSIONS = ('.png', '.jpg', '.jpeg', '.tif', '.tiff', '.webp')

DEFAULT_REF_WIDTH = 400  # DAG units

REF_PATH_KNOB = 'nuke_ref_path'
REF_NATIVE_W_KNOB = 'nuke_ref_native_w'
REF_NATIVE_H_KNOB = 'nuke_ref_native_h'

# How long after the last bdwidth change to keep the image dimmed.
RESIZE_DIM_WINDOW_S = 0.20
# Opacity used while resizing. 0.0 = invisible, 1.0 = opaque.
RESIZE_DIM_OPACITY = 0.30

# Label overlay: a translucent caption bar painted at the bottom of each ref.
# The text comes from the BackdropNode's standard `label` knob, so users edit
# it through the regular node Properties panel. We keep the native label
# invisible (note_font_size=1 in code below) so it doesn't clash with ours.
# Resize feedback opacity and time window (kept; nothing to do with labels).

# Module-level state
_OVERLAYS = {}              # id(DAG_Window) -> _RefOverlay
_PIXMAP_CACHE = {}          # path -> {'native': QPixmap, 'levels': {w: QPixmap}}
_LAST_RESIZE_TS = {}        # node fullname -> time of last bdwidth change
_INSTALL_TIMER = None       # legacy slow timer (cleanup only, not paint)

# Event-driven overlay update: we install an eventFilter on each DAG_Window
# and trigger our overlay's repaint *exactly* when the DAG itself repaints.
# This eliminates the 30Hz polling that the previous version did.
_DAG_FILTER = None          # _DagEventFilter instance, shared across DAGs

# Cached list of "our" backdrop nodes, refreshed only when nodes are added or
# removed. allNodes('BackdropNode') walks the whole graph every call and gets
# expensive once the comp has many regular backdrops too.
_REF_NODES_CACHE = None     # list[nuke.Node] or None when invalidated
_REF_NODES_DIRTY = True

# Dirty-state cache. The overlay only repaints when one of these snapshots
# actually changes between ticks. In idle (no pan, no zoom, no node edits)
# the cost of a tick collapses to a few dict comparisons.
_DIRTY_STATE = {}           # id(DAG_Window) -> dict of last-known scene state


# ---------------------------------------------------------------------------
# Qt object liveness
# ---------------------------------------------------------------------------

def _is_alive(qt_obj):
    """True if the C++ object under a PySide wrapper still exists."""
    if qt_obj is None:
        return False
    try:
        return bool(shiboken.isValid(qt_obj))
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Ref-node cache
# ---------------------------------------------------------------------------
#
# Calling nuke.allNodes('BackdropNode') every paint walks the whole graph in
# Nuke's C++ side and gets noticeable once the comp has many real backdrops
# alongside ours. We cache the filtered list of reference backdrops and
# invalidate it through Nuke callbacks for add/delete events.

def _invalidate_ref_cache(*args, **kwargs):
    """Mark the cached ref-nodes list as stale. Cheap; never traverses."""
    global _REF_NODES_DIRTY
    _REF_NODES_DIRTY = True
    # Force a repaint of every overlay so newly created / deleted refs
    # show up immediately rather than on the next pan/zoom.
    for ov in list(_OVERLAYS.values()):
        if _is_alive(ov):
            try:
                ov.update()
            except RuntimeError:
                pass


def _get_ref_nodes():
    """Return the cached list of reference backdrop nodes. Rebuild if stale."""
    global _REF_NODES_CACHE, _REF_NODES_DIRTY
    if _REF_NODES_DIRTY or _REF_NODES_CACHE is None:
        try:
            _REF_NODES_CACHE = [
                bd for bd in nuke.allNodes('BackdropNode')
                if REF_PATH_KNOB in bd.knobs()
            ]
        except Exception:
            _REF_NODES_CACHE = []
        _REF_NODES_DIRTY = False
    return _REF_NODES_CACHE


# ---------------------------------------------------------------------------
# Event-driven overlay updates
# ---------------------------------------------------------------------------
#
# Instead of polling at 30Hz with a QTimer, we install an event filter on
# each DAG_Window so our overlay repaints *only* when the DAG itself does.
# In idle the cost drops to zero. While the user pans or zooms, Nuke
# already repaints the DAG, and we piggyback on that event.

class _DagEventFilter(QObject):
    """
    Forwards DAG_Window paint/resize events into overlay updates and
    remembers the last mouse-click position in each DAG so paste_reference()
    can drop the new ref where the user last interacted with the graph --
    exactly how Nuke's own node creation behaves.
    """

    # id(DAG_Window) -> (x_local, y_local) of the most recent mouse press
    LAST_CLICK = {}

    def eventFilter(self, obj, event):
        et = event.type()

        # Paint covers pan, zoom, and arbitrary internal Nuke repaints.
        # Resize covers panel layout changes.
        if et == QEvent.Paint or et == QEvent.Resize:
            dag_id = id(obj)
            ov = _OVERLAYS.get(dag_id)
            if ov is not None and _is_alive(ov):
                # Don't synchronously paint here -- that would re-enter Qt's
                # paint pipeline. Schedule a paint for the next tick.
                try:
                    ov.update()
                except RuntimeError:
                    pass

        # Track every mouse press inside any DAG so paste-at-cursor works
        # regardless of where the keyboard focus currently sits when the
        # user hits Ctrl+V. Without this, pressing the shortcut while the
        # cursor is over the menu bar or another panel would stack refs
        # at whatever the global cursor happened to be over.
        elif et == QEvent.MouseButtonPress:
            try:
                pos = event.pos()
                _DagEventFilter.LAST_CLICK[id(obj)] = (pos.x(), pos.y())
            except Exception:
                pass

        # Never consume events: let Nuke handle them normally.
        return False


# ---------------------------------------------------------------------------
# Disk helpers
# ---------------------------------------------------------------------------

def _script_dir_or_none():
    """Return the directory of the saved .nk, or None if unsaved."""
    script_path = nuke.root().name()
    if not script_path or script_path == 'Root':
        return None
    script_dir = os.path.dirname(script_path)
    if not script_dir or not os.path.isdir(script_dir):
        return None
    return script_dir


def _resolve_storage_dir_or_warn():
    """Resolve <script_dir>/nuke_ref_images/ or pop a warning dialog."""
    script_dir = _script_dir_or_none()
    if script_dir is None:
        nuke.message(
            'NukeRef: please save your Nuke script first.\n\n'
            'Reference images are stored alongside the .nk file.'
        )
        return None

    target = os.path.join(script_dir, 'nuke_ref_images')
    try:
        os.makedirs(target, exist_ok=True)
    except OSError as err:
        nuke.message('NukeRef: could not create {}: {}'.format(target, err))
        return None
    return target


def _unique_filename(directory, prefix='ref'):
    ts = int(time.time() * 1000)
    candidate = os.path.join(directory, '{}_{}.png'.format(prefix, ts))
    counter = 0
    while os.path.exists(candidate):
        counter += 1
        candidate = os.path.join(
            directory, '{}_{}_{}.png'.format(prefix, ts, counter)
        )
    return candidate


def _save_qimage_as_png(qimage):
    directory = _resolve_storage_dir_or_warn()
    if directory is None:
        return None
    path = _unique_filename(directory)
    if not qimage.save(path, 'PNG', 100):
        raise IOError('Failed to write reference image to {}'.format(path))
    return path


# ---------------------------------------------------------------------------
# Clipboard helpers
# ---------------------------------------------------------------------------

def _grab_clipboard_payload():
    """Pull image data from the clipboard in one pass."""
    clipboard = QApplication.clipboard()

    image = clipboard.image()
    if image is not None and not image.isNull():
        return ('image', image)

    mime = clipboard.mimeData()
    if mime is not None:
        try:
            has_urls = mime.hasUrls()
        except RuntimeError:
            has_urls = False
        if has_urls:
            try:
                urls = list(mime.urls())
            except RuntimeError:
                urls = []
            for url in urls:
                if not url.isLocalFile():
                    continue
                local = url.toLocalFile()
                if local.lower().endswith(SUPPORTED_EXTENSIONS):
                    return ('path', local)

    return (None, None)


# ---------------------------------------------------------------------------
# DAG widget discovery + coordinate mapping
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# DAG widget discovery + coordinate mapping
# ---------------------------------------------------------------------------
#
# The Node Graph surface differs by platform:
#   - macOS native build: className() == 'DAG_Window'
#   - Windows GL build:    'Foundry::UI::GLWidget' whose parent is a
#                          'Foundry::UI::LinkedView' named 'DAG.*'. We attach
#                          the overlay as a CHILD of this GL widget, because
#                          that is the configuration where the overlay is
#                          transparent AND passes mouse events through to the
#                          graph underneath (verified working). The Viewer is
#                          also a GLWidget, so we disambiguate via the parent.
#
# The GL widget is generally stable during normal interaction; the 'C++
# object already deleted' errors seen earlier were provoked by debug code
# that pumped the event loop (time.sleep + processEvents). In normal use we
# find it fresh each pass and guard every access, so a transient teardown is
# handled gracefully rather than crashing.

def _looks_like_dag(w):
    """True if widget w is the Node Graph GL surface (or macOS DAG_Window)."""
    try:
        cls = w.metaObject().className()
    except Exception:
        return False

    # macOS native.
    if cls == 'DAG_Window':
        return True

    # Windows GL build: GLWidget whose parent LinkedView is named 'DAG.*'.
    # The Viewer is also a GLWidget but its parent isn't a DAG LinkedView.
    if cls == 'Foundry::UI::GLWidget':
        try:
            parent = w.parent()
            if parent is None:
                return False
            pcls = parent.metaObject().className()
            pname = parent.objectName()
        except Exception:
            return False
        if 'LinkedView' in pcls and pname and pname.startswith('DAG'):
            return True
        return False

    # Generic QGraphicsView-with-scene fallback (other builds).
    if 'QGraphicsView' in cls:
        try:
            if w.scene() is not None:
                return True
        except Exception:
            pass
    return False


def _all_dag_widgets():
    """Every live, visible Node Graph surface on this platform."""
    app = QApplication.instance()
    if app is None:
        return []
    out = []
    for w in app.allWidgets():
        try:
            if not _is_alive(w):
                continue
            if not w.isVisible():
                continue
            if not _looks_like_dag(w):
                continue
            _ = w.width()  # liveness probe
        except Exception:
            continue
        out.append(w)
    return out


def _dag_widget_under_cursor():
    """Visible DAG under the mouse cursor, or fallback to any visible one."""
    cursor_pos = QCursor.pos()
    fallback = None
    for w in _all_dag_widgets():
        try:
            local = w.mapFromGlobal(cursor_pos)
            if w.rect().contains(local):
                return w
            fallback = w
        except RuntimeError:
            # Widget died mid-iteration; skip it.
            continue
    return fallback


def _paste_target_coords():
    """
    Decide where the next pasted reference should land in DAG (node) space.

    Priority:
      1) If the cursor is currently over a DAG, use that position (macOS-style
         "hover the graph, hit the shortcut").
      2) Otherwise, fall back to the last recorded mouse-click position inside
         any DAG (Windows-style "click in graph, then go to a menu, then hit
         the shortcut"). Same model Nuke uses for its own node creation.
      3) If neither exists, return None and callers will drop at (0, 0).

    Every widget access is guarded: on Windows the DAG GLWidget can be torn
    down and recreated when tabs change, leaving stale wrappers that raise
    RuntimeError on touch.
    """
    zoom = nuke.zoom()
    center = nuke.center()
    if not zoom or zoom <= 0 or center is None:
        return None

    # Path 1: cursor over a DAG right now.
    dag_under = _dag_widget_under_cursor()
    if dag_under is not None and _is_alive(dag_under):
        try:
            cursor_global = QCursor.pos()
            local = dag_under.mapFromGlobal(cursor_global)
            if dag_under.rect().contains(local):
                dx_px = local.x() - dag_under.width() / 2.0
                dy_px = local.y() - dag_under.height() / 2.0
                return (int(center[0] + dx_px / zoom),
                        int(center[1] + dy_px / zoom))
        except RuntimeError:
            pass

    # Path 2: most recent click inside a DAG.
    for dag in _all_dag_widgets():
        if not _is_alive(dag):
            continue
        try:
            click = _DagEventFilter.LAST_CLICK.get(id(dag))
            if click is None:
                continue
            cx, cy = click
            dx_px = cx - dag.width() / 2.0
            dy_px = cy - dag.height() / 2.0
            return (int(center[0] + dx_px / zoom),
                    int(center[1] + dy_px / zoom))
        except RuntimeError:
            continue

    return None


# Kept for backwards compatibility with anything that still imports it.
def _cursor_to_dag_coords():
    return _paste_target_coords()


def _dag_to_widget_rect(dag, x_node, y_node, w_node, h_node):
    """Map a DAG-space rect to widget pixel coordinates inside `dag`."""
    zoom = nuke.zoom()
    center = nuke.center()
    if not zoom or zoom <= 0 or center is None:
        return None

    half_w = dag.width() / 2.0
    half_h = dag.height() / 2.0
    px = (x_node - center[0]) * zoom + half_w
    py = (y_node - center[1]) * zoom + half_h
    return QRectF(px, py, w_node * zoom, h_node * zoom)


# ---------------------------------------------------------------------------
# Mip-pyramid pixmap cache
# ---------------------------------------------------------------------------
#
# Painting a 4K QPixmap into a 400px rect 30 times a second is what kills the
# overlay. Qt has to downsample 4K -> 400px every frame, with smoothing on.
#
# Instead, for each source PNG we keep multiple pre-scaled copies (a "mip
# pyramid") at fixed widths: 4096, 2048, 1024, 512, 256, 128, 64. At paint
# time we pick the smallest level whose width is >= the on-screen width, so
# Qt does at most a minor downscale (which is fast). When the on-screen size
# changes by less than ~10% from a level, we even skip SmoothPixmapTransform.
#
# Levels are computed lazily on first use, so users don't pay the upfront
# cost when opening a script with many refs they aren't looking at yet.

# Cache structure: _PIXMAP_CACHE[path] = {
#   'native': QPixmap,        # full-resolution, decoded once
#   'levels': {w: QPixmap},   # width-keyed downscaled copies
# }
_MIP_LEVELS = (4096, 2048, 1024, 512, 256, 128, 64)


def _get_native_pixmap(path):
    """Decode the source file once and remember it."""
    if not path:
        return None
    entry = _PIXMAP_CACHE.get(path)
    if entry is not None:
        return entry['native']
    if not os.path.isfile(path):
        return None
    pix = QPixmap(path)
    if pix.isNull():
        return None
    _PIXMAP_CACHE[path] = {'native': pix, 'levels': {}}
    return pix


def _pick_mip_level(native_w, on_screen_w):
    """
    Choose the mip width to use for a given on-screen size.

    Pick the smallest level whose width is >= on_screen_w, so we always
    downscale (which is cheap and looks good) and never upscale (which
    blurs). Cap at the native width.
    """
    target = max(1, int(on_screen_w))
    candidates = [w for w in _MIP_LEVELS if w >= target and w <= native_w]
    if candidates:
        return min(candidates)
    # On-screen is bigger than every preset level -> use the native pixmap.
    return native_w


def _get_pixmap_for_size(path, on_screen_w):
    """
    Return a QPixmap roughly matching on_screen_w in width.

    Uses the mip cache. Generates the requested level on demand the first
    time it's asked for, then reuses it for subsequent frames.

    Returns (pixmap, exact_size_match):
        pixmap          - the QPixmap to blit
        exact_size_match - True if the chosen level's width is within 10%
                           of on_screen_w (signal to skip smooth scaling)
    """
    native = _get_native_pixmap(path)
    if native is None:
        return (None, False)

    native_w = native.width()
    if native_w <= 0:
        return (None, False)

    level_w = _pick_mip_level(native_w, on_screen_w)

    # Native fits the bill (target bigger than top mip, or path's native
    # width is smaller than the smallest mip level larger than target).
    if level_w == native_w:
        ratio = abs(level_w - on_screen_w) / max(on_screen_w, 1.0)
        return (native, ratio < 0.10)

    entry = _PIXMAP_CACHE[path]
    cached = entry['levels'].get(level_w)
    if cached is None:
        # First time we need this level for this image. Scale by width and
        # let Qt compute the matching height to preserve aspect.
        cached = native.scaledToWidth(level_w, Qt.SmoothTransformation)
        entry['levels'][level_w] = cached

    ratio = abs(level_w - on_screen_w) / max(on_screen_w, 1.0)
    return (cached, ratio < 0.10)


def _purge_pixmap_cache():
    _PIXMAP_CACHE.clear()


# ---------------------------------------------------------------------------
# Background mip-level pre-generation
# ---------------------------------------------------------------------------
#
# Synchronously building a 4K -> 128px mip the first time it's needed creates
# a hiccup right when many small refs appear at once (typical when zooming
# out). To avoid that, every time we add or load a reference we kick off a
# QRunnable that builds all the cheap mip levels (<= 1024px) up front in
# a background thread. The biggest levels (2048, 4096) we still build on
# demand because they're rarely the right pick anyway.
#
# QPixmap operations are GUI-thread-only, so the worker uses QImage for the
# scaling (which is thread-safe), then hands the result to the GUI thread
# via QTimer.singleShot(0, ...) to convert to QPixmap and install in the
# cache. That trampoline is the only thread-safe way to publish a QPixmap
# from a worker thread.

_PREWARM_LEVELS = (1024, 512, 256, 128, 64)
_PREWARMED_PATHS = set()  # paths whose cheap levels we've already kicked off


class _MipPrewarmJob(QRunnable):
    """Loads a source image and pre-scales it down to common small sizes."""

    def __init__(self, path):
        super(_MipPrewarmJob, self).__init__()
        self._path = path
        self.setAutoDelete(True)

    def run(self):
        path = self._path
        if not os.path.isfile(path):
            return
        # Decode in the worker thread so the GUI thread never has to wait
        # on disk I/O for big PNGs.
        src = QImage(path)
        if src.isNull():
            return
        native_w = src.width()
        if native_w <= 0:
            return

        # Pre-scale to the requested mip levels using QImage (thread-safe).
        # Skip levels at or above native_w -- those would be the native image.
        scaled = {}
        for level_w in _PREWARM_LEVELS:
            if level_w >= native_w:
                continue
            try:
                img = src.scaledToWidth(
                    level_w,
                    Qt.SmoothTransformation,
                )
            except Exception:
                continue
            if not img.isNull():
                scaled[level_w] = img

        # Hand the result back to the GUI thread for QPixmap conversion +
        # cache install. Capture by default args so the closure doesn't
        # share state with subsequent jobs.
        def _publish(path=path, src_img=src, scaled_imgs=scaled):
            entry = _PIXMAP_CACHE.get(path)
            if entry is None:
                # Convert source to QPixmap once; it becomes the cache 'native'.
                native_pix = QPixmap.fromImage(src_img)
                if native_pix.isNull():
                    return
                entry = {'native': native_pix, 'levels': {}}
                _PIXMAP_CACHE[path] = entry
            for level_w, img in scaled_imgs.items():
                if level_w in entry['levels']:
                    continue
                pix = QPixmap.fromImage(img)
                if not pix.isNull():
                    entry['levels'][level_w] = pix

        QTimer.singleShot(0, _publish)


def _prewarm_mips(path):
    """Schedule background mip generation for a path (idempotent)."""
    if not path or path in _PREWARMED_PATHS:
        return
    _PREWARMED_PATHS.add(path)
    QThreadPool.globalInstance().start(_MipPrewarmJob(path))


# ---------------------------------------------------------------------------
# Native icon (feeds the mini-map and is a fallback)
# ---------------------------------------------------------------------------

def _refresh_native_icon(backdrop):
    """
    Re-set the BackdropNode's custom icon so the mini-map shows the image.

    scale = bdwidth / native_width; matches the Qt overlay's geometry so
    the two render paths line up visually in the main DAG.
    """
    if REF_PATH_KNOB not in backdrop.knobs():
        return
    if REF_NATIVE_W_KNOB not in backdrop.knobs():
        return
    path = backdrop[REF_PATH_KNOB].value()
    if not path or not os.path.isfile(path):
        return

    native_w = backdrop[REF_NATIVE_W_KNOB].value()
    if not native_w or native_w <= 0:
        return
    scale = float(backdrop['bdwidth'].value()) / float(native_w)
    if scale <= 0:
        return

    try:
        backdrop.setCustomIcon(path, scale, 0, 0)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Overlay widget
# ---------------------------------------------------------------------------

class _RefOverlay(QWidget):
    """Transparent overlay glued to a DAG_Window. Paints references in Qt."""

    def __init__(self, dag_widget):
        super(_RefOverlay, self).__init__(dag_widget)
        self._dag = dag_widget

        self.setGeometry(0, 0, dag_widget.width(), dag_widget.height())
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WA_NoSystemBackground, True)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.raise_()
        self.show()

    def _sync_geometry(self):
        if not _is_alive(self._dag):
            return False
        try:
            if self.size() != self._dag.size():
                self.setGeometry(0, 0, self._dag.width(), self._dag.height())
        except RuntimeError:
            # Dag died between the liveness check and the access.
            return False
        return True

    def paintEvent(self, event):
        if not self._sync_geometry():
            return

        refs = []
        for bd in _get_ref_nodes():
            try:
                path = bd[REF_PATH_KNOB].value()
            except Exception:
                continue
            if not path:
                continue
            refs.append((bd, path))
        if not refs:
            return

        now = time.time()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, False)

        overlay_rect = QRectF(self.rect())

        for bd, path in refs:
            try:
                x = int(bd['xpos'].value())
                y = int(bd['ypos'].value())
                w = int(bd['bdwidth'].value())
                h = int(bd['bdheight'].value())
                full_name = bd.fullName()
            except Exception:
                continue
            if w <= 0 or h <= 0:
                continue

            dst = _dag_to_widget_rect(self._dag, x, y, w, h)
            if dst is None:
                continue
            if not dst.intersects(overlay_rect):
                continue

            on_screen_w = dst.width()
            pix, close_match = _get_pixmap_for_size(path, on_screen_w)
            if pix is None:
                continue

            painter.setRenderHint(
                QPainter.SmoothPixmapTransform, not close_match
            )

            last_ts = _LAST_RESIZE_TS.get(full_name)
            dim_active = (
                last_ts is not None and (now - last_ts) < RESIZE_DIM_WINDOW_S
            )
            painter.setOpacity(RESIZE_DIM_OPACITY if dim_active else 1.0)

            # --- Edge-clip fix -------------------------------------------------
            # The on-screen destination rect `dst` is the backdrop's four
            # corners mapped to widget pixels. When a corner runs off the
            # window, only PART of the image is visible. We always:
            #   1) compute the visible part of dst (intersection with window),
            #   2) map that visible part back to the matching sub-rectangle of
            #      the source pixmap, as simple [0..1] fractions of dst,
            #   3) draw only that sub-rectangle into the visible rect.
            #
            # Because the fractions are taken relative to the FULL dst, a
            # backdrop clipped on its LEFT or TOP edge yields a positive source
            # offset (the bug before was treating that offset incorrectly).
            # Clamping the fractions into the unit square makes it robust at
            # any zoom level, and never asks Qt to draw an oversized rect.
            visible = dst.intersected(overlay_rect)
            if visible.isEmpty():
                continue

            dst_w = dst.width()
            dst_h = dst.height()
            pix_w = pix.width()
            pix_h = pix.height()
            if dst_w <= 0 or dst_h <= 0 or pix_w <= 0 or pix_h <= 0:
                continue

            fx = (visible.left() - dst.left()) / dst_w
            fy = (visible.top() - dst.top()) / dst_h
            fw = visible.width() / dst_w
            fh = visible.height() / dst_h

            # Clamp so float rounding can't push the source past the edges.
            fx = min(max(fx, 0.0), 1.0)
            fy = min(max(fy, 0.0), 1.0)
            fw = min(max(fw, 0.0), 1.0 - fx)
            fh = min(max(fh, 0.0), 1.0 - fy)
            if fw <= 0.0 or fh <= 0.0:
                continue

            src = QRectF(fx * pix_w, fy * pix_h, fw * pix_w, fh * pix_h)
            painter.drawPixmap(visible, pix, src)

        painter.end()


# ---------------------------------------------------------------------------
# Overlay lifecycle: bootstrap, monitor, cleanup
# ---------------------------------------------------------------------------

def _ensure_overlays():
    """Maintain one _RefOverlay per live DAG. No-op when the Qt overlay path
    is disabled (non-macOS), where references are drawn by setCustomIcon."""
    if not _USE_QT_OVERLAY:
        return

    global _DAG_FILTER
    if _DAG_FILTER is None:
        _DAG_FILTER = _DagEventFilter()

    live_dags = _all_dag_widgets()
    live_ids = {id(d) for d in live_dags}

    # Drop dead overlays. We key by id() because once the C++ object is
    # destroyed, equality-comparing the Python wrapper raises RuntimeError.
    for dag_id in list(_OVERLAYS.keys()):
        ov = _OVERLAYS.get(dag_id)
        dead = False
        try:
            dead = (dag_id not in live_ids
                    or not _is_alive(ov)
                    or not _is_alive(ov._dag))
        except Exception:
            dead = True
        if dead:
            try:
                if _is_alive(ov):
                    ov.deleteLater()
            except Exception:
                pass
            _OVERLAYS.pop(dag_id, None)
            _DIRTY_STATE.pop(dag_id, None)

    # Add overlays for newly-visible DAGs and install the event filter on
    # each DAG. Each widget is handled in isolation so a single stale GL
    # wrapper can't abort the whole pass (and can't spam the console).
    for dag in live_dags:
        try:
            if not _is_alive(dag):
                continue
            dag_id = id(dag)
            if dag_id not in _OVERLAYS:
                # Building the overlay touches dag.width()/height(); if the
                # widget dies right here we just skip it this cycle.
                ov = _RefOverlay(dag)
                _OVERLAYS[dag_id] = ov
                _DIRTY_STATE.pop(dag_id, None)
                try:
                    dag.installEventFilter(_DAG_FILTER)
                except Exception:
                    pass
            else:
                _OVERLAYS[dag_id].raise_()
        except RuntimeError:
            # Stale GL wrapper. Drop any half-built state for it silently.
            try:
                _OVERLAYS.pop(id(dag), None)
                _DIRTY_STATE.pop(id(dag), None)
            except Exception:
                pass
            continue
        except Exception:
            continue


def _slow_cleanup():
    """
    Low-frequency housekeeping (called every 2s, not every frame).

    Catches new DAG panels appearing (after splitting / docking) and expires
    the resize-dim timestamps. All errors are swallowed quietly: on Windows
    the DAG GLWidget is frequently torn down and recreated, and we don't want
    transient 'already deleted' noise in the console.
    """
    try:
        _ensure_overlays()
    except Exception:
        pass

    # Any node currently within the dim window forces a quick repaint so
    # the opacity animation finishes cleanly. Once the timestamps expire
    # we stop triggering.
    now = time.time()
    expired_names = []
    needs_repaint = False
    for name, ts in list(_LAST_RESIZE_TS.items()):
        if (now - ts) < RESIZE_DIM_WINDOW_S:
            needs_repaint = True
        else:
            expired_names.append(name)
    for name in expired_names:
        _LAST_RESIZE_TS.pop(name, None)
        needs_repaint = True

    if needs_repaint:
        for ov in _OVERLAYS.values():
            if _is_alive(ov):
                try:
                    ov.update()
                except RuntimeError:
                    pass


# ---------------------------------------------------------------------------
# Aspect lock + resize timestamp + native icon refresh on bdwidth change
# ---------------------------------------------------------------------------

def _on_knob_changed():
    """
    Fires for every knob change on BackdropNodes. On our refs:
        - bdwidth: lock bdheight to source aspect, stamp the time so the
          overlay knows to render dimmed, and re-issue setCustomIcon.
        - label: trigger an overlay repaint so caption updates appear live.

    Nuke repaints the DAG itself on geometry changes (xpos/ypos/bdwidth/
    bdheight), so _DagEventFilter picks those up for free. Label changes
    don't necessarily invalidate the DAG, so we nudge our overlay manually.
    """
    node = nuke.thisNode()
    if node.Class() != 'BackdropNode':
        return
    if REF_PATH_KNOB not in node.knobs():
        return

    knob = nuke.thisKnob()
    if knob is None:
        return
    name = knob.name()

    if name != 'bdwidth':
        return

    if REF_NATIVE_W_KNOB not in node.knobs():
        return
    if REF_NATIVE_H_KNOB not in node.knobs():
        return

    nw = float(node[REF_NATIVE_W_KNOB].value())
    nh = float(node[REF_NATIVE_H_KNOB].value())
    if nw <= 0 or nh <= 0:
        return

    bdw = float(node['bdwidth'].value())
    target_h = int(round(bdw * nh / nw))
    if int(node['bdheight'].value()) != target_h:
        node['bdheight'].setValue(target_h)

    # Tag this node as "actively resizing" so the overlay dims it.
    try:
        _LAST_RESIZE_TS[node.fullName()] = time.time()
    except Exception:
        pass

    # Re-issue the native icon at the new scale, so the mini-map updates.
    _refresh_native_icon(node)


# ---------------------------------------------------------------------------
# Backdrop creation
# ---------------------------------------------------------------------------

def _make_reference_backdrop(image_path, source_image=None):
    if source_image is not None and not source_image.isNull():
        native_w = source_image.width()
        native_h = source_image.height()
    else:
        probe = QImage(image_path)
        if probe.isNull():
            native_w = native_h = DEFAULT_REF_WIDTH
        else:
            native_w = probe.width()
            native_h = probe.height()

    safe_path = image_path.replace('\\', '/')

    display_w = min(native_w, DEFAULT_REF_WIDTH)
    display_h = int(round(display_w * native_h / max(native_w, 1)))

    # Position at the cursor by letting Nuke create the node the same way it
    # creates any node from a shortcut: nuke.createNode() drops the node at
    # the current mouse position in the Node Graph automatically. This is the
    # native mechanism and works identically on macOS and Windows -- no Qt
    # widget hunting, no event filters, no volatile GLWidget access.
    #
    # createNode also auto-connects to the selected node; we suppress that by
    # clearing the selection first and removing inputs after.
    for n in nuke.allNodes():
        try:
            n['selected'].setValue(False)
        except Exception:
            pass

    bd = nuke.createNode('BackdropNode', inpanel=False)

    # createNode put the node's top-left at the cursor. Re-center it on the
    # cursor by shifting up-left by half the display size, and set our size +
    # appearance.
    cur_x = int(bd['xpos'].value())
    cur_y = int(bd['ypos'].value())
    bd['xpos'].setValue(int(cur_x - display_w / 2))
    bd['ypos'].setValue(int(cur_y - display_h / 2))
    bd['bdwidth'].setValue(display_w)
    bd['bdheight'].setValue(display_h)
    bd['note_font_size'].setValue(1)
    bd['label'].setValue('')
    bd['tile_color'].setValue(0x202020ff)
    try:
        bd['z_order'].setValue(-10)
    except Exception:
        pass

    path_knob = nuke.String_Knob(REF_PATH_KNOB, 'ref path')
    path_knob.setFlag(nuke.INVISIBLE)
    bd.addKnob(path_knob)
    bd[REF_PATH_KNOB].setValue(safe_path)

    nw_knob = nuke.Int_Knob(REF_NATIVE_W_KNOB, 'native w')
    nw_knob.setFlag(nuke.INVISIBLE)
    bd.addKnob(nw_knob)
    bd[REF_NATIVE_W_KNOB].setValue(int(native_w))

    nh_knob = nuke.Int_Knob(REF_NATIVE_H_KNOB, 'native h')
    nh_knob.setFlag(nuke.INVISIBLE)
    bd.addKnob(nh_knob)
    bd[REF_NATIVE_H_KNOB].setValue(int(native_h))

    # Native icon: this is the PRIMARY renderer on Windows/Linux and the
    # mini-map feed on macOS (where the Qt overlay draws the main view).
    _refresh_native_icon(bd)

    # Background mip generation (used by the macOS overlay path).
    _prewarm_mips(safe_path)

    for n in nuke.allNodes():
        try:
            n['selected'].setValue(False)
        except Exception:
            pass
    bd['selected'].setValue(True)

    return bd


# ---------------------------------------------------------------------------
# Public commands
# ---------------------------------------------------------------------------

def _delegate_native_paste():
    """
    Hand off to Nuke's normal paste behaviour.

    Our Ctrl+V command shadows the built-in paste, so when the clipboard is
    NOT an image we must reproduce the native behaviour ourselves. We try
    the documented entry points in order and stop at the first that works.
    Crucially, every failure is swallowed so a paste attempt can never raise
    into Nuke's shortcut handler (which is what made Read-node pastes appear
    'broken' for the tester: an exception aborted the whole paste).
    """
    # 1) nodePaste() with no args: reads Nuke's own node clipboard and pastes
    #    at the cursor, exactly like the built-in Ctrl+V.
    try:
        nuke.nodePaste()
        return
    except Exception:
        pass
    # 2) Explicit system clipboard token, older API spelling.
    try:
        nuke.nodePaste('%clipboard%')
        return
    except Exception:
        pass


def paste_reference():
    kind, value = _grab_clipboard_payload()

    # If the clipboard isn't an image, this is an ordinary Nuke paste
    # (nodes, text, etc). Delegate immediately and do nothing else, so we
    # never interfere with normal copy/paste of Read nodes or anything else.
    if kind is None:
        _delegate_native_paste()
        return

    # From here on we know it's an image. Images require a saved script so
    # the PNG can live next to the .nk.
    if _script_dir_or_none() is None:
        nuke.message(
            'NukeRef: please save your Nuke script first.\n\n'
            'Reference images are stored alongside the .nk file.'
        )
        return

    if kind == 'image':
        try:
            path = _save_qimage_as_png(value)
        except Exception as err:
            nuke.message('NukeRef: could not save image: {}'.format(err))
            return
        if path is None:
            return
        _make_reference_backdrop(path, source_image=value)
        return

    if kind == 'path':
        _make_reference_backdrop(value)
        return

    # Shouldn't reach here, but be safe.
    _delegate_native_paste()


def copy_reference():
    """
    Bound to Ctrl+C in the Node Graph.

    If exactly one reference backdrop (one carrying our image) is selected,
    copy its IMAGE into the system clipboard so it can be pasted into other
    apps -- mirroring PureRef. Anything else (a plain backdrop, multiple
    nodes, regular nodes) falls through to Nuke's normal copy so node
    copy/paste is never disturbed.
    """
    try:
        selected = nuke.selectedNodes()
    except Exception:
        selected = []

    ref_backdrops = [
        n for n in selected
        if n.Class() == 'BackdropNode' and REF_PATH_KNOB in n.knobs()
    ]

    # Copy the image only when the selection is exactly one reference and
    # nothing else. Otherwise behave like a normal node copy.
    if len(selected) == 1 and len(ref_backdrops) == 1:
        bd = ref_backdrops[0]
        try:
            path = bd[REF_PATH_KNOB].value()
        except Exception:
            path = None
        if path and os.path.isfile(path):
            img = QImage(path)
            if not img.isNull():
                try:
                    QApplication.clipboard().setImage(img)
                    nuke.tprint('[NukeRef] Copied reference image to clipboard.')
                    return
                except Exception as err:
                    nuke.tprint(
                        '[NukeRef] clipboard setImage failed: {}'.format(err))
        # If we couldn't load the image, fall through to native copy so the
        # user at least gets the node on the clipboard.

    # Native node copy.
    try:
        nuke.nodeCopy('%clipboard%')
    except Exception:
        pass


def refresh_references():
    """Force overlay rebuild + native icon refresh on every ref."""
    _purge_pixmap_cache()
    _PREWARMED_PATHS.clear()
    _ensure_overlays()
    for bd in nuke.allNodes('BackdropNode'):
        if REF_PATH_KNOB in bd.knobs():
            _refresh_native_icon(bd)
            try:
                _prewarm_mips(bd[REF_PATH_KNOB].value())
            except Exception:
                pass
    for ov in _OVERLAYS.values():
        if _is_alive(ov):
            ov.update()
    nuke.tprint('[NukeRef] References refreshed.')


def _on_script_load():
    """Re-apply native icons and pre-warm mip caches after a script opens."""
    for bd in nuke.allNodes('BackdropNode'):
        if REF_PATH_KNOB in bd.knobs():
            _refresh_native_icon(bd)
            try:
                _prewarm_mips(bd[REF_PATH_KNOB].value())
            except Exception:
                pass


# ---------------------------------------------------------------------------
# Installation
# ---------------------------------------------------------------------------

def install():
    global _INSTALL_TIMER

    menu = nuke.menu('Node Graph')
    for item in ('Paste Reference', 'Copy Reference', 'Refresh References'):
        try:
            menu.removeItem(item)
        except Exception:
            pass

    menu.addCommand(
        'Paste Reference',
        'import nuke_ref; nuke_ref.paste_reference()',
        'ctrl+v',
    )
    menu.addCommand(
        'Copy Reference',
        'import nuke_ref; nuke_ref.copy_reference()',
        'ctrl+c',
    )
    menu.addCommand(
        'Refresh References',
        'import nuke_ref; nuke_ref.refresh_references()',
    )

    nuke.addKnobChanged(_on_knob_changed, nodeClass='BackdropNode')
    nuke.addOnScriptLoad(_on_script_load)

    # Node-lifecycle callbacks invalidate the ref-nodes cache, so the next
    # paint sees added/removed refs without scanning the whole graph each
    # frame. We register for BackdropNode only; other classes never have
    # our REF_PATH_KNOB anyway.
    nuke.addOnUserCreate(_invalidate_ref_cache, nodeClass='BackdropNode')
    nuke.addOnCreate(_invalidate_ref_cache, nodeClass='BackdropNode')
    nuke.addOnDestroy(_invalidate_ref_cache, nodeClass='BackdropNode')

    # Bring overlays + DAG event filters up immediately so the first paste
    # works without waiting for the housekeeping timer to tick.
    try:
        _ensure_overlays()
    except Exception as err:
        nuke.tprint('[NukeRef] initial _ensure_overlays failed: {}'.format(err))

    # Slow housekeeping loop. Runs every 2 seconds, far cheaper than the
    # old 30 Hz tick: it only re-walks the widget tree to catch newly
    # opened DAG panels and expires resize-dim timestamps. All real paints
    # are now event-driven via _DagEventFilter.
    if _INSTALL_TIMER is None:
        _INSTALL_TIMER = QTimer()
        _INSTALL_TIMER.setInterval(2000)
        _INSTALL_TIMER.timeout.connect(_slow_cleanup)
        _INSTALL_TIMER.start()

    nuke.tprint('[NukeRef] Installed (Ctrl+V to paste reference).')
