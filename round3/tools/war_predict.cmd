cd /d C:\ADN\pd-exp-r3
set PYTHONDONTWRITEBYTECODE=1
set PY=C:\ADN\voz\venv\Scripts\python.exe
echo start %DATE% %TIME%
nvidia-smi > round3\logs\war\nvidia_smi_before.txt
%PY% round3\predict.py > round3\logs\war\predict.log 2>&1
echo done %DATE% %TIME%
