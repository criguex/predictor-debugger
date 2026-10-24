cd /d C:\ADN\pd-exp
set PYTHONDONTWRITEBYTECODE=1
set PY=C:\ADN\voz\venv\Scripts\python.exe
echo start %DATE% %TIME%
%PY% tests\test_checks.py > logs\%1\test_checks.log 2>&1
%PY% -m pd.evaluate --machine %1 > logs\%1\evaluate.log 2>&1
%PY% verify.py --saved %1 > logs\%1\verify_saved.log 2>&1
echo done %DATE% %TIME%
