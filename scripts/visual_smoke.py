from pathlib import Path
root=Path(__file__).resolve().parents[1]
html=(root/'public'/'index.html').read_text(encoding='utf-8');css=(root/'public'/'styles.css').read_text(encoding='utf-8');js=(root/'public'/'app.js').read_text(encoding='utf-8')
checks={
 'bounded_layout':'--content:' in css and '.shell{' in css,
 'surface_hierarchy':'--surface:' in css and 'box-shadow:' in css,
 'typography':'clamp(' in css and 'letter-spacing:-' in css,
 'responsive':'@media' in css,
 'focus':'focus-visible' in css,
 'reduced_motion':'prefers-reduced-motion' in css,
 'cinema_cards':'.movie-card' in css and '.poster{' in css and 'aspect-ratio:' in css,
 'accessible_login':'<label for="username">' in html and '<label for="password">' in html,
 'script_login_contract':"e.preventDefault()" in js and '/api/auth/login' in js
}
failed=[k for k,v in checks.items() if not v]
if failed: raise SystemExit('VISUAL_CONTRACT_FAILED:'+','.join(failed))
print('visual_smoke_ok')
