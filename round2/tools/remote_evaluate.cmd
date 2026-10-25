cd /d C:\ADN\pd-exp-r2
set PYTHONDONTWRITEBYTECODE=1
set PY=C:\ADN\voz\venv\Scripts\python.exe
echo start %DATE% %TIME%
%PY% tests\test_checks.py > round2\logs\%1\test_checks.log 2>&1
%PY% round2\verify.py --regenerate round2\regen --report round2\logs\%1\regeneration.json > round2\logs\%1\regeneration.log 2>&1
%PY% -m round2.evaluate --machine %1 > round2\logs\%1\evaluate.log 2>&1
%PY% round2\verify.py --saved %1 > round2\logs\%1\verify_saved.log 2>&1
echo done %DATE% %TIME%
