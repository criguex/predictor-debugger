cd /d C:\ADN\pd-exp
set PYTHONDONTWRITEBYTECODE=1
set PY=C:\ADN\voz\venv\Scripts\python.exe
echo start %DATE% %TIME%
%PY% verify.py --regenerate regen --splits train val test ood --report logs\war\regeneration.json > logs\war\regeneration.log 2>&1
%PY% -c "import json,sys; r=json.load(open('logs/war/regeneration.json')); sys.exit(0 if r['identical']==r['files'] else 3)"
if errorlevel 1 (echo regeneration differs, stopping & exit /b 3)
move regen data
nvidia-smi > logs\war\nvidia_smi_before_training.txt
%PY% -m pd.train --seed 0 --log logs\war\train_s0.json > logs\war\train_s0.log 2>&1
%PY% -m pd.train --seed 1 --log logs\war\train_s1.json > logs\war\train_s1.log 2>&1
echo done %DATE% %TIME%
