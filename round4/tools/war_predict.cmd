cd /d C:\ADN\pd-exp-r4
set PYTHONDONTWRITEBYTECODE=1
set PY=C:\ADN\voz\venv\Scripts\python.exe
echo start %DATE% %TIME%
nvidia-smi > round4\logs\war\nvidia_smi_before.txt
%PY% round4\predict.py > round4\logs\war\predict.log 2>&1
echo done %DATE% %TIME%
