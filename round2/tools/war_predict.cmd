cd /d C:\ADN\pd-exp-r2
set PYTHONDONTWRITEBYTECODE=1
set PY=C:\ADN\voz\venv\Scripts\python.exe
echo start %DATE% %TIME%
nvidia-smi > round2\logs\war\nvidia_smi_before.txt
%PY% -m round2.predict checkpoints > round2\logs\war\predict_checkpoints.log 2>&1
%PY% -m round2.predict graded > round2\logs\war\graded_training.log 2>&1
echo done %DATE% %TIME%
