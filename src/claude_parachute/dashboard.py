"""dashboard.py — a calm, light-Claude status page for Parachute.

`parachute dashboard` renders a self-contained HTML file (no external assets,
light/dark toggle) into the project's `.parachute/` and opens it. It shows the
snapshot timeline, how much disk the net is using, whether the hooks are armed,
and a clear note on how to pull the cord. Read-only snapshot of the safety net.
"""

from __future__ import annotations

import html
from datetime import datetime, timezone
from pathlib import Path

from .hookconfig import HOOK_TAG, claude_code_home, settings_path
from .snapshots import ShadowRepo

__all__ = ["render_dashboard_html", "write_dashboard"]

_CREAM = "#F4EEE4"
_CARD = "#FBF8F2"
_INK = "#2B2722"
_MUTED = "#8A8178"
_ORANGE = "#D97757"
_LINE = "#E7DFD2"
_OK = "#3F8F77"
_IDLE = "#B8AFA3"

_CLAUDE_LOGO_PATH = "M4.709 15.955l4.72-2.647.08-.23-.08-.128H9.2l-.79-.048-2.698-.073-2.339-.097-2.266-.122-.571-.121L0 11.784l.055-.352.48-.321.686.06 1.52.103 2.278.158 1.652.097 2.449.255h.389l.055-.157-.134-.098-.103-.097-2.358-1.596-2.552-1.688-1.336-.972-.724-.491-.364-.462-.158-1.008.656-.722.881.06.225.061.893.686 1.908 1.476 2.491 1.833.365.304.145-.103.019-.073-.164-.274-1.355-2.446-1.446-2.49-.644-1.032-.17-.619a2.97 2.97 0 01-.104-.729L6.283.134 6.696 0l.996.134.42.364.62 1.414 1.002 2.229 1.555 3.03.456.898.243.832.091.255h.158V9.01l.128-1.706.237-2.095.23-2.695.08-.76.376-.91.747-.492.584.28.48.685-.067.444-.286 1.851-.559 2.903-.364 1.942h.212l.243-.242.985-1.306 1.652-2.064.73-.82.85-.904.547-.431h1.033l.76 1.129-.34 1.166-1.064 1.347-.881 1.142-1.264 1.7-.79 1.36.073.11.188-.02 2.856-.606 1.543-.28 1.841-.315.833.388.091.395-.328.807-1.969.486-2.309.462-3.439.813-.042.03.049.061 1.549.146.662.036h1.622l3.02.225.79.522.474.638-.079.485-1.215.62-1.64-.389-3.829-.91-1.312-.329h-.182v.11l1.093 1.068 2.006 1.81 2.509 2.33.127.578-.322.455-.34-.049-2.205-1.657-.851-.747-1.926-1.62h-.128v.17l.444.649 2.345 3.521.122 1.08-.17.353-.608.213-.668-.122-1.374-1.925-1.415-2.167-1.143-1.943-.14.08-.674 7.254-.316.37-.729.28-.607-.461-.322-.747.322-1.476.389-1.924.315-1.53.286-1.9.17-.632-.012-.042-.14.018-1.434 1.967-2.18 2.945-1.726 1.845-.414.164-.717-.37.067-.662.401-.589 2.388-3.036 1.44-1.882.93-1.086-.006-.158h-.055L4.132 18.56l-1.13.146-.487-.456.061-.746.231-.243 1.908-1.312-.006.006z"  # noqa: E501


def _logo(size=30):
    return (f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" '
            f'xmlns="http://www.w3.org/2000/svg" aria-hidden="true"><title>Claude</title>'
            f'<path d="{_CLAUDE_LOGO_PATH}" fill="{_ORANGE}" fill-rule="nonzero"></path></svg>')


def _claude_logo_svg(size=30):
    """The real Claude logo as a standalone SVG string (reused by the app)."""
    return _logo(size)


def _dir_size(path: Path) -> int:
    total = 0
    try:
        for p in path.rglob("*"):
            if p.is_file():
                try:
                    total += p.stat().st_size
                except OSError:
                    pass
    except OSError:
        pass
    return total


def render_dashboard_html(repo: ShadowRepo) -> str:
    esc = html.escape
    armed = repo.exists()
    snaps = repo.list(200) if armed else []
    size_mb = round(_dir_size(repo.store_dir) / (1024 * 1024), 1) if armed else 0
    sp = settings_path(claude_code_home())
    hook_on = sp.exists() and HOOK_TAG in sp.read_text(encoding="utf-8", errors="ignore")
    now = datetime.now(timezone.utc).astimezone().strftime("%a %d %b %Y, %I:%M %p").lstrip("0")

    if snaps:
        rows = []
        for i, s in enumerate(snaps[:60], 1):
            when = s.time.strftime("%a %d %b %I:%M %p").lstrip("0")
            rows.append(
                f'<div class="snap"><span class="dot"></span>'
                f'<div class="snap-body"><div class="snap-label">{esc(s.label)}</div>'
                f'<div class="snap-meta">{esc(s.short)} &middot; {esc(when)}</div></div>'
                f'<div class="snap-idx">restore {i}</div></div>')
        timeline = "".join(rows)
    else:
        timeline = ('<div class="card empty"><p>No snapshots yet.</p>'
                    '<code>parachute install-hooks</code></div>')

    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Claude Parachute</title>
<style>
  * {{ box-sizing: border-box; }}
  body {{ margin:0; padding:0 0 56px; background:{_CREAM}; color:{_INK};
    font:15px/1.5 -apple-system,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;
    transition:background .25s,color .25s; }}
  .wrap {{ max-width:820px; margin:0 auto; padding:0 24px; }}
  header {{ display:flex; align-items:center; gap:12px; padding:34px 0 6px; }}
  header h1 {{ font-size:24px; margin:0; font-weight:650; letter-spacing:-0.2px; }}
  header .sub {{ color:{_MUTED}; font-size:13px; margin-top:2px; }}
  .tbtn {{ background:{_CARD}; border:1px solid {_LINE}; color:{_MUTED}; flex:none;
    border-radius:999px; padding:6px 14px; font-size:12px; cursor:pointer; }}
  h2 {{ font-size:13px; text-transform:uppercase; letter-spacing:.8px; color:{_MUTED};
    margin:28px 0 12px; font-weight:600; }}
  .stats {{ display:flex; gap:10px; margin:18px 0 4px; flex-wrap:wrap; }}
  .stat {{ flex:1; min-width:120px; background:{_CARD}; border:1px solid {_LINE};
    border-radius:12px; padding:12px 14px; text-align:center; }}
  .stat .num {{ font-size:22px; font-weight:650; color:{_ORANGE}; }}
  .stat .lbl {{ font-size:11px; color:{_MUTED}; margin-top:4px; text-transform:uppercase;
    letter-spacing:.4px; }}
  .card {{ background:{_CARD}; border:1px solid {_LINE}; border-radius:14px;
    padding:16px 18px; margin-bottom:12px; }}
  .snap {{ display:flex; align-items:center; gap:13px; background:{_CARD};
    border:1px solid {_LINE}; border-radius:12px; padding:10px 16px; margin-bottom:8px; }}
  .snap .dot {{ width:10px; height:10px; border-radius:50%; background:{_OK}; flex:none;
    box-shadow:0 0 0 4px rgba(0,0,0,0.03); }}
  .snap-body {{ flex:1; min-width:0; }}
  .snap-label {{ font-weight:600; }}
  .snap-meta {{ color:{_MUTED}; font-size:11.5px; margin-top:2px;
    font-family:ui-monospace,Consolas,monospace; }}
  .snap-idx {{ color:{_MUTED}; font-size:11.5px; font-family:ui-monospace,Consolas,monospace; }}
  .note {{ background:#fff; border:1px dashed {_LINE}; border-radius:12px;
    padding:14px 18px; color:#4a443c; font-size:13.5px; }}
  .empty {{ text-align:center; color:{_MUTED}; }}
  .empty code {{ display:inline-block; margin-top:8px; background:{_CREAM};
    padding:6px 12px; border-radius:8px; color:{_INK}; }}
  footer {{ color:{_MUTED}; font-size:12px; text-align:center; margin-top:30px; }}
  body.dark {{ background:#221d19; color:#ece6dc; }}
  body.dark .sub, body.dark h2, body.dark .stat .lbl, body.dark .snap-meta,
  body.dark .snap-idx, body.dark footer {{ color:#a89f95; }}
  body.dark .stat, body.dark .card, body.dark .snap, body.dark .tbtn {{ background:#2c2620; border-color:#3a332c; }}
  body.dark .note {{ background:#1d1814; border-color:#3a332c; color:#cfc7bb; }}
</style></head>
<body><div class="wrap">
  <header>
    {_logo(32)}
    <div style="flex:1"><h1>Claude Parachute</h1>
      <div class="sub">The safety net for when /rewind can't save you.</div></div>
    <button class="tbtn" id="themeToggle" onclick="toggleTheme()" aria-label="Toggle theme">Dark</button>
  </header>

  <div class="stats">
    <div class="stat"><div class="num">{len(snaps)}</div><div class="lbl">snapshots</div></div>
    <div class="stat"><div class="num">{size_mb}</div><div class="lbl">MB used</div></div>
    <div class="stat"><div class="num">{'On' if hook_on else 'Off'}</div><div class="lbl">auto-snap</div></div>
    <div class="stat"><div class="num">{'Yes' if armed else 'No'}</div><div class="lbl">armed</div></div>
  </div>

  <div class="note">Pull the cord anytime: <code>parachute restore &lt;number&gt;</code>
  (or <code>parachute undo</code>). Every restore takes a safety snapshot first, so
  it's undoable. Parachute writes only inside <code>.parachute/</code> — your real
  <code>.git</code> is never touched.</div>

  <h2>Snapshot timeline ({len(snaps)})</h2>
  {timeline}

  <footer>Project: {esc(str(repo.work_tree))} &middot; taken {esc(now)} &middot; re-run <code>parachute dashboard</code></footer>
</div>
<script>
function applyTheme(t){{ document.body.classList.toggle('dark', t==='dark');
  var b=document.getElementById('themeToggle'); if(b) b.textContent=(t==='dark'?'Light':'Dark'); }}
function toggleTheme(){{ var t=document.body.classList.contains('dark')?'light':'dark';
  try{{ localStorage.setItem('parachute-theme', t); }}catch(e){{}} applyTheme(t); }}
(function(){{ var t='light'; try{{ t=localStorage.getItem('parachute-theme')||'light'; }}catch(e){{}} applyTheme(t); }})();
</script>
</body></html>"""


def write_dashboard(repo: ShadowRepo) -> Path:
    repo.store_dir.mkdir(parents=True, exist_ok=True)
    out = repo.store_dir / "dashboard.html"
    out.write_text(render_dashboard_html(repo), encoding="utf-8")
    return out
