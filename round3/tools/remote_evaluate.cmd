cd /d C:\ADN\pd-exp-r3
set PYTHONDONTWRITEBYTECODE=1
set PY=C:\ADN\voz\venv\Scripts\python.exe
echo start %DATE% %TIME%
%PY% tests\test_checks.py > round3\logs\%1\test_checks.log 2>&1
%PY% round2\test_checks2.py > round3\logs\%1\test_checks2.log 2>&1
%PY% round3\test_checks3.py > round3\logs\%1\test_checks3.log 2>&1
%PY% round3\verify.py --regenerate round3\regen --report round3\logs\%1\regeneration.json > round3\logs\%1\regeneration.log 2>&1
%PY% -m round3.evaluate --machine %1 --jobs %2 > round3\logs\%1\evaluate.log 2>&1
%PY% round3\verify.py --saved %1 > round3\logs\%1\verify_saved.log 2>&1
echo done %DATE% %TIME%
