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
 'script_login_contract':"e.preventDefault()" in js and '/api/auth/login' in js,
 'brand_is_customer_facing':'Locadora Fênix' in html and 'BDK FACTORY' not in html and 'BDK Generated Site' not in html,
 'registration_form':'registerForm' in html and '/api/auth/register' in js,
 'no_prompt_alert':'prompt(' not in js and 'alert(' not in js,
 'user_modal':'userDialog' in html and 'userFormError' in html,
 'operator_role_selector':'id="newRole"' in html and 'value="OPERATIONAL">Operador' in html,
 'user_edit_action':'data-edit-user' in js and "function openUserDialog(user=null)" in js,
 'friendly_age_validation':'Informe uma idade válida em anos completos.' in js and 'Informe uma idade inteira entre 0 e 120.' not in js
}
failed=[k for k,v in checks.items() if not v]
if failed: raise SystemExit('VISUAL_CONTRACT_FAILED:'+','.join(failed))
print('visual_smoke_ok')
