cd /d C:\ADN\pd-exp-r4
set PYTHONDONTWRITEBYTECODE=1
set PY=C:\ADN\voz\venv\Scripts\python.exe
echo start %DATE% %TIME%
%PY% tests\test_checks.py > round4\logs\%1\test_checks.log 2>&1
%PY% round2\test_checks2.py > round4\logs\%1\test_checks2.log 2>&1
%PY% round3\test_checks3.py > round4\logs\%1\test_checks3.log 2>&1
%PY% round4\test_checks4.py > round4\logs\%1\test_checks4.log 2>&1
%PY% round4\verify.py --regenerate round4\regen --report round4\logs\%1\regeneration.json > round4\logs\%1\regeneration.log 2>&1
%PY% -m round4.evaluate --machine %1 --jobs %2 > round4\logs\%1\evaluate.log 2>&1
%PY% round4\verify.py --saved %1 > round4\logs\%1\verify_saved.log 2>&1
echo done %DATE% %TIME%
