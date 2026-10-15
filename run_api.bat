@echo off
rem Queue of API evolution runs (v3 fitness, T25 UAV params). Waits for luna s1 to finish, then runs sequentially.
cd /d C:\ISDEA
for /f "usebackq" %%k in (`findstr /b "sk-or-" API_KEY.txt`) do set LLM_API_KEY=%%k
echo waiting for or_gpt6luna_T3_v3_s1 to finish...
:wait
findstr /c:"DONE best" experiments\results\evolve\or_gpt6luna_T3_v3_s1.log >nul 2>&1
if errorlevel 1 (
  timeout /t 120 /nobreak >nul
  goto wait
)
call :run evolve_or_haiku55_T3 0
call :run evolve_or_haiku55_T3 1
call :run evolve_or_haiku55_T3 2
call :run evolve_or_qwen35_9b_T3 0
call :run evolve_or_qwen35_9b_T3 1
call :run evolve_or_qwen35_9b_T3 2
call :run evolve_or_gpt6sol_T3 0
echo ALL API RUNS FINISHED
goto :eof

:run
set n=%~1
set n=%n:evolve_=%
echo %date% %time%  start %n% seed %2
python src/llm_evolve.py --config experiments/configs/%~1.json --seed %2 --out experiments/results/evolve/%n%_v3_s%2 > experiments/results/evolve/%n%_v3_s%2.log 2>&1
goto :eof
