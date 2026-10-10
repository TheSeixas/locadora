from pathlib import Path
import compileall
root=Path(__file__).resolve().parents[1]
files=[root/'server.py',*list((root/'scripts').glob('*.py')),*list((root/'tests').glob('*.py'))]
for f in files:
    if not f.exists(): raise SystemExit(f'BUILD_INPUT_MISSING:{f.relative_to(root)}')
if not compileall.compile_dir(str(root),quiet=1,force=True): raise SystemExit('PYTHON_COMPILE_FAILED')
(root/'dist').mkdir(exist_ok=True)
(root/'dist'/'BUILD_OK.json').write_text('{"status":"PASS","contract":"locadora-fenix-fullstack"}\n',encoding='utf-8')
print('build_ok')
