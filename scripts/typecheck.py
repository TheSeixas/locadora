from pathlib import Path
import py_compile
root=Path(__file__).resolve().parents[1]
for f in [root/'server.py',*list((root/'scripts').glob('*.py')),*list((root/'tests').glob('*.py'))]: py_compile.compile(str(f),doraise=True)
print('typecheck_ok')
