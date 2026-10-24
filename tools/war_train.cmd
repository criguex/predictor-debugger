cd /d C:\ADN\pd-exp
set PYTHONDONTWRITEBYTECODE=1
set PY=C:\ADN\voz\venv\Scripts\python.exe
echo start %DATE% %TIME%
nvidia-smi > logs\war\nvidia_smi_before_training.txt
%PY% -m pd.train --seed 0 --log logs\war\train_s0.json > logs\war\train_s0.log 2>&1
%PY% -m pd.train --seed 1 --log logs\war\train_s1.json > logs\war\train_s1.log 2>&1
echo done %DATE% %TIME%
