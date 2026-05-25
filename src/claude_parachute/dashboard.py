"""dashboard.py — Parachute's status page, in the fleet's elevated-glass look.

`parachute dashboard` renders this self-contained HTML file (one Google-Fonts link
aside) into the project's `.parachute/` and opens it: snapshot timeline, disk use,
whether the hooks are armed, and a clear "pull the cord" note. Read-only.

Design system (shared across the fleet): warm "Claude brew" identity, real Claude
logo, frosted glassmorphism over a soft drifting aurora, gradient accents,
restrained micro-animations, a sleek dark mode, strong type hierarchy.
"""

from __future__ import annotations

import html
from datetime import datetime, timezone
from pathlib import Path

from .hookconfig import HOOK_TAG, claude_code_home, settings_path
from .snapshots import ShadowRepo

__all__ = ["render_dashboard_html", "write_dashboard", "_claude_logo_svg"]

# Official Claude logo coral — the real mark's colour (the UI accent #C8632F lives
# in the CSS; the logo glyph stays true to brand).
_ORANGE = "#D97757"

_CLAUDE_LOGO_PATH = "M4.709 15.955l4.72-2.647.08-.23-.08-.128H9.2l-.79-.048-2.698-.073-2.339-.097-2.266-.122-.571-.121L0 11.784l.055-.352.48-.321.686.06 1.52.103 2.278.158 1.652.097 2.449.255h.389l.055-.157-.134-.098-.103-.097-2.358-1.596-2.552-1.688-1.336-.972-.724-.491-.364-.462-.158-1.008.656-.722.881.06.225.061.893.686 1.908 1.476 2.491 1.833.365.304.145-.103.019-.073-.164-.274-1.355-2.446-1.446-2.49-.644-1.032-.17-.619a2.97 2.97 0 01-.104-.729L6.283.134 6.696 0l.996.134.42.364.62 1.414 1.002 2.229 1.555 3.03.456.898.243.832.091.255h.158V9.01l.128-1.706.237-2.095.23-2.695.08-.76.376-.91.747-.492.584.28.48.685-.067.444-.286 1.851-.559 2.903-.364 1.942h.212l.243-.242.985-1.306 1.652-2.064.73-.82.85-.904.547-.431h1.033l.76 1.129-.34 1.166-1.064 1.347-.881 1.142-1.264 1.7-.79 1.36.073.11.188-.02 2.856-.606 1.543-.28 1.841-.315.833.388.091.395-.328.807-1.969.486-2.309.462-3.439.813-.042.03.049.061 1.549.146.662.036h1.622l3.02.225.79.522.474.638-.079.485-1.215.62-1.64-.389-3.829-.91-1.312-.329h-.182v.11l1.093 1.068 2.006 1.81 2.509 2.33.127.578-.322.455-.34-.049-2.205-1.657-.851-.747-1.926-1.62h-.128v.17l.444.649 2.345 3.521.122 1.08-.17.353-.608.213-.668-.122-1.374-1.925-1.415-2.167-1.143-1.943-.14.08-.674 7.254-.316.37-.729.28-.607-.461-.322-.747.322-1.476.389-1.924.315-1.53.286-1.9.17-.632-.012-.042-.14.018-1.434 1.967-2.18 2.945-1.726 1.845-.414.164-.717-.37.067-.662.401-.589 2.388-3.036 1.44-1.882.93-1.086-.006-.158h-.055L4.132 18.56l-1.13.146-.487-.456.061-.746.231-.243 1.908-1.312-.006.006z"  # noqa: E501


def _logo(size=28):
    return (f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" '
            f'xmlns="http://www.w3.org/2000/svg" aria-hidden="true"><title>Claude</title>'
            f'<path d="{_CLAUDE_LOGO_PATH}" fill="{_ORANGE}" fill-rule="nonzero"></path></svg>')


def _claude_logo_svg(size=28):
    """The real Claude logo as a standalone SVG string (reused by the app)."""
    return _logo(size)


_CSS = """
  :root{
    --bg1:#F7F2E8; --bg2:#EDE3D1; --ink:#1C1712; --muted:#5F564B; --faint:#8C8174;
    --orange:#C8632F; --orange2:#E0875C; --ok:#2E7D63; --line:rgba(43,39,34,.12);
    --glass:rgba(255,253,249,.38); --glass-strong:rgba(255,253,249,.60);
    --glass-blur:blur(34px) saturate(1.9);
    --sheen:inset 0 1px 0 rgba(255,255,255,.8), inset 0 0 0 1px rgba(255,255,255,.16);
    --shadow:var(--sheen), 0 1px 2px rgba(43,39,34,.05), 0 12px 32px -12px rgba(43,39,34,.24);
    --shadow-hi:var(--sheen), 0 1px 2px rgba(43,39,34,.06), 0 24px 54px -16px rgba(200,99,47,.46);
    --radius:18px; --radius-sm:12px; --grad:linear-gradient(135deg,var(--orange2),var(--orange));
    --aur1:rgba(217,119,87,.40); --aur2:rgba(217,167,87,.34); --aur3:rgba(63,143,119,.30);
  }
  body.dark{
    --bg1:#150F0B; --bg2:#1E1712; --ink:#F7F1E7; --muted:#B7AEA2; --faint:#7A7064;
    --orange:#E0875C; --orange2:#EE9E75; --ok:#4FB592; --line:rgba(255,255,255,.10);
    --glass:rgba(38,31,25,.34); --glass-strong:rgba(46,38,30,.56);
    --glass-blur:blur(36px) saturate(1.7);
    --sheen:inset 0 1px 0 rgba(255,255,255,.14), inset 0 0 0 1px rgba(255,255,255,.05);
    --shadow:var(--sheen), 0 1px 2px rgba(0,0,0,.45), 0 16px 38px -14px rgba(0,0,0,.7);
    --shadow-hi:var(--sheen), 0 1px 2px rgba(0,0,0,.5), 0 28px 60px -18px rgba(232,145,111,.55);
    --aur1:rgba(232,145,111,.42); --aur2:rgba(217,167,87,.26); --aur3:rgba(63,143,119,.36);
  }
  *{box-sizing:border-box}
  html{scroll-behavior:smooth}
  body{margin:0;min-height:100vh;color:var(--ink);
    font:16px/1.6 "Instrument Sans",-apple-system,"Segoe UI",Roboto,sans-serif;
    background:radial-gradient(1100px 680px at 12% -8%, var(--aur1), transparent 60%),
      radial-gradient(900px 620px at 92% 4%, var(--aur2), transparent 58%),
      radial-gradient(1200px 800px at 70% 110%, var(--aur3), transparent 60%),
      linear-gradient(170deg,var(--bg1),var(--bg2));
    background-attachment:fixed;transition:color .4s ease, background .6s ease;}
  .aurora{position:fixed;inset:-20% -10% auto -10%;height:60vh;z-index:0;pointer-events:none;
    background:radial-gradient(420px 320px at 25% 30%, var(--aur1), transparent 70%),
      radial-gradient(380px 300px at 75% 20%, var(--aur2), transparent 70%);
    filter:blur(40px);opacity:.9;animation:drift 22s ease-in-out infinite alternate;}
  @keyframes drift{0%{transform:translate3d(-3%,-2%,0) scale(1)}100%{transform:translate3d(4%,3%,0) scale(1.12)}}
  .wrap{position:relative;z-index:1;max-width:880px;margin:0 auto;padding:0 22px 72px}
  header{display:flex;align-items:center;gap:14px;padding:40px 0 8px}
  .logo{display:inline-flex;width:46px;height:46px;align-items:center;justify-content:center;
    border-radius:14px;background:var(--glass-strong);box-shadow:var(--shadow);
    backdrop-filter:var(--glass-blur);-webkit-backdrop-filter:var(--glass-blur)}
  h1{font-size:27px;margin:0;font-weight:700;letter-spacing:-.4px;line-height:1.05;
    background:linear-gradient(120deg,var(--ink),var(--orange) 140%);
    -webkit-background-clip:text;background-clip:text;-webkit-text-fill-color:transparent}
  body.dark h1{background:linear-gradient(120deg,#fff,var(--orange2));-webkit-background-clip:text;background-clip:text;-webkit-text-fill-color:transparent}
  .sub{color:var(--muted);font-size:13.5px;margin-top:3px}
  .toggle{margin-left:auto;display:inline-flex;align-items:center;gap:8px;cursor:pointer;
    background:var(--glass);color:var(--muted);border-radius:999px;padding:9px 14px;font:inherit;
    font-size:13px;font-weight:600;box-shadow:var(--shadow);border:none;
    backdrop-filter:var(--glass-blur);-webkit-backdrop-filter:var(--glass-blur);
    transition:transform .2s ease, color .2s ease, box-shadow .3s ease}
  .toggle:hover{color:var(--ink);transform:translateY(-1px);box-shadow:var(--shadow-hi)}
  .toggle .ic{width:16px;height:16px;display:inline-block;transition:transform .5s cubic-bezier(.5,1.6,.4,1)}
  .toggle:hover .ic{transform:rotate(35deg)}
  .stats{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:24px 0 14px}
  @media(max-width:620px){.stats{grid-template-columns:repeat(2,1fr)}}
  .stat{position:relative;overflow:hidden;background:var(--glass);border-radius:var(--radius-sm);
    padding:16px 14px;text-align:center;box-shadow:var(--shadow);
    backdrop-filter:var(--glass-blur);-webkit-backdrop-filter:var(--glass-blur);
    transition:transform .25s cubic-bezier(.2,.8,.3,1), box-shadow .3s ease}
  .stat:hover{transform:translateY(-4px);box-shadow:var(--shadow-hi)}
  .stat::after{content:"";position:absolute;inset:0 0 auto 0;height:2px;background:var(--grad);
    transform:scaleX(0);transform-origin:left;transition:transform .4s ease}
  .stat:hover::after{transform:scaleX(1)}
  .stat .num{font-size:26px;font-weight:700;line-height:1.05;letter-spacing:-.5px;
    background:var(--grad);-webkit-background-clip:text;background-clip:text;-webkit-text-fill-color:transparent}
  .stat .lbl{font-size:10.5px;color:var(--muted);margin-top:6px;text-transform:uppercase;letter-spacing:.7px;font-weight:600}
  h2{font-size:12px;text-transform:uppercase;letter-spacing:1.2px;color:var(--muted);
    margin:34px 0 13px;font-weight:700;display:flex;align-items:center;gap:9px}
  h2::before{content:"";width:14px;height:2px;border-radius:2px;background:var(--grad)}
  .cord{position:relative;overflow:hidden;background:var(--glass-strong);border:1px solid rgba(200,99,47,.4);
    border-radius:var(--radius);padding:16px 20px 16px 24px;box-shadow:var(--shadow-hi);margin:8px 0 4px;
    font-size:14px;line-height:1.55;backdrop-filter:var(--glass-blur);-webkit-backdrop-filter:var(--glass-blur)}
  .cord::before{content:"";position:absolute;left:0;top:0;bottom:0;width:4px;background:var(--grad)}
  .cord b{font-weight:700}
  .cord code{background:rgba(200,99,47,.12);color:var(--orange);padding:2px 7px;border-radius:7px;
    font-family:"JetBrains Mono",ui-monospace,Consolas,monospace;font-size:12.5px}
  .snap{display:flex;align-items:center;gap:14px;background:var(--glass);border-radius:14px;
    padding:11px 17px;margin-bottom:9px;box-shadow:var(--shadow);
    backdrop-filter:var(--glass-blur);-webkit-backdrop-filter:var(--glass-blur);
    transition:transform .2s ease, box-shadow .3s ease}
  .snap:hover{transform:translateY(-2px);box-shadow:var(--shadow-hi)}
  .snap .dot{width:11px;height:11px;border-radius:50%;flex:none;position:relative;background:var(--ok);
    box-shadow:0 0 0 4px rgba(46,125,99,.14)}
  .snap.latest .dot::after{content:"";position:absolute;inset:0;border-radius:50%;background:var(--ok);animation:pulse 2s ease-out infinite}
  @keyframes pulse{0%{transform:scale(1);opacity:.7}100%{transform:scale(2.6);opacity:0}}
  .snap-body{flex:1;min-width:0}
  .snap-label{font-weight:600;font-size:14.5px}
  .snap-meta{color:var(--muted);font-size:11.5px;margin-top:2px;font-family:"JetBrains Mono",ui-monospace,Consolas,monospace}
  .snap-idx{color:var(--muted);font-size:11.5px;white-space:nowrap;font-family:"JetBrains Mono",ui-monospace,Consolas,monospace}
  .card{background:var(--glass);border-radius:var(--radius);padding:17px 19px;box-shadow:var(--shadow);
    backdrop-filter:var(--glass-blur);-webkit-backdrop-filter:var(--glass-blur)}
  .empty{text-align:center;color:var(--muted)}
  .empty code{display:inline-block;margin-top:8px;background:var(--glass-strong);padding:6px 12px;border-radius:8px;color:var(--ink);
    font-family:"JetBrains Mono",ui-monospace,Consolas,monospace}
  footer{color:var(--muted);font-size:12.5px;text-align:center;margin-top:40px}
  footer code{background:var(--glass);padding:2px 8px;border-radius:6px}
  .reveal{opacity:0;transform:translateY(16px)}
  .reveal.in{opacity:1;transform:none;transition:opacity .6s ease, transform .6s cubic-bezier(.2,.8,.3,1)}
  @media(prefers-reduced-motion:reduce){.aurora{animation:none}.reveal{opacity:1;transform:none}.snap.latest .dot::after{animation:none}}
"""

_JS = """
  var SUN='<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="4.2"/><path d="M12 2v2M12 20v2M2 12h2M20 12h2M5 5l1.4 1.4M17.6 17.6L19 19M19 5l-1.4 1.4M6.4 17.6L5 19"/></svg>';
  var MOON='<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12.8A9 9 0 1111.2 3a7 7 0 009.8 9.8z"/></svg>';
  function applyTheme(t){var d=t==='dark';document.body.classList.toggle('dark',d);
    var i=document.getElementById('themeIc'),x=document.getElementById('themeTxt');
    if(i)i.innerHTML=d?SUN:MOON; if(x)x.textContent=d?'Light':'Dark';}
  function toggleTheme(){var t=document.body.classList.contains('dark')?'light':'dark';
    try{localStorage.setItem('parachute-theme',t);}catch(e){}applyTheme(t);}
  (function(){var t='light';try{t=localStorage.getItem('parachute-theme')||'light';}catch(e){}applyTheme(t);
    var b=document.getElementById('themeToggle'); if(b)b.addEventListener('click',toggleTheme);})();
  var reduce=matchMedia('(prefers-reduced-motion: reduce)').matches;
  function countUp(el){var tgt=+el.dataset.count,d=1000,s=performance.now();
    function f(now){var p=Math.min((now-s)/d,1);var e=1-Math.pow(1-p,3);el.textContent=Math.round(tgt*e);if(p<1)requestAnimationFrame(f);}requestAnimationFrame(f);}
  window.addEventListener('load',function(){
    if(reduce){document.querySelectorAll('[data-count]').forEach(function(el){el.textContent=el.dataset.count;});
      document.querySelectorAll('.reveal').forEach(function(el){el.classList.add('in');});return;}
    var io=new IntersectionObserver(function(es){es.forEach(function(en){if(en.isIntersecting){en.target.classList.add('in');
      en.target.querySelectorAll('[data-count]').forEach(countUp);io.unobserve(en.target);}});},{threshold:.15});
    var i=0;document.querySelectorAll('.reveal').forEach(function(el){el.style.transitionDelay=(i++*40)+'ms';io.observe(el);});
  });
"""


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
            latest = " latest" if i == 1 else ""
            rows.append(
                f'<div class="snap{latest} reveal"><span class="dot"></span>'
                f'<div class="snap-body"><div class="snap-label">{esc(s.label)}</div>'
                f'<div class="snap-meta">{esc(s.short)} &middot; {esc(when)}</div></div>'
                f'<div class="snap-idx">restore {i}</div></div>')
        timeline = "".join(rows)
    else:
        timeline = ('<div class="card empty reveal"><p>No snapshots yet.</p>'
                    '<code>parachute install-hooks</code></div>')

    return (
        '<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        '<title>Claude Parachute</title>'
        '<link rel="preconnect" href="https://fonts.googleapis.com">'
        '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
        '<link href="https://fonts.googleapis.com/css2?family=Instrument+Sans:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">'
        f'<style>{_CSS}</style></head><body>'
        '<div class="aurora" aria-hidden="true"></div><div class="wrap">'
        '<header class="reveal">'
        f'<span class="logo">{_logo(28)}</span>'
        "<div><h1>Claude Parachute</h1>"
        "<div class=\"sub\">The safety net for when /rewind can't save you.</div></div>"
        '<button class="toggle" id="themeToggle" aria-label="Toggle light and dark theme">'
        '<span class="ic" id="themeIc"></span><span id="themeTxt">Dark</span></button>'
        '</header>'
        '<div class="stats reveal">'
        f'<div class="stat"><div class="num" data-count="{len(snaps)}">0</div><div class="lbl">snapshots</div></div>'
        f'<div class="stat"><div class="num">{size_mb}</div><div class="lbl">MB used</div></div>'
        f'<div class="stat"><div class="num">{"On" if hook_on else "Off"}</div><div class="lbl">auto-snap</div></div>'
        f'<div class="stat"><div class="num">{"Yes" if armed else "No"}</div><div class="lbl">armed</div></div>'
        '</div>'
        '<div class="cord reveal"><b>Pull the cord anytime:</b> <code>parachute restore &lt;number&gt;</code> '
        'or <code>parachute undo</code>. Every restore takes a safety snapshot first, so it\'s always '
        'undoable. Parachute writes only inside <code>.parachute/</code> — your real <code>.git</code> '
        'is never touched.</div>'
        f'<h2 class="reveal">Snapshot timeline ({len(snaps)})</h2>'
        f'{timeline}'
        f'<footer class="reveal">Project: {esc(str(repo.work_tree))} &middot; taken {esc(now)} '
        '&middot; re-run <code>parachute dashboard</code></footer>'
        f'</div><script>{_JS}</script></body></html>'
    )


def write_dashboard(repo: ShadowRepo) -> Path:
    repo.store_dir.mkdir(parents=True, exist_ok=True)
    out = repo.store_dir / "dashboard.html"
    out.write_text(render_dashboard_html(repo), encoding="utf-8")
    return out
