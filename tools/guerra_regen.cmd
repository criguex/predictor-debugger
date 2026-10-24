cd /d C:\ADN\pd-exp
set PYTHONDONTWRITEBYTECODE=1
set PY=C:\ADN\voz\venv\Scripts\python.exe
echo start %DATE% %TIME%
%PY% tests\test_checks.py > logs\guerra\test_checks.log 2>&1
%PY% verify.py --regenerate regen --splits val test ood --report logs\guerra\regeneration.json > logs\guerra\regeneration.log 2>&1
%PY% -c "import json,sys; r=json.load(open('logs/guerra/regeneration.json')); sys.exit(0 if r['identical']==r['files'] else 3)"
if errorlevel 1 (echo regeneration differs, stopping & exit /b 3)
move regen data
echo done %DATE% %TIME%
