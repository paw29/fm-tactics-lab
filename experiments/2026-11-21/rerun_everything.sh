# wait for the running Geometrismo pass (old code, will hit the same check after its screen), then rerun both; saved results are reused
while powershell -NoProfile -Command "if (Get-CimInstance Win32_Process | ? CommandLine -like '*everything.py geometrismo*') { exit 0 } else { exit 1 }"; do sleep 60; done
export PYTHONIOENCODING=utf8
/c/Users/pawan/fm-tactics-lab/.venv/Scripts/python.exe -W ignore -u everything.py diamond > everything_diamond.log 2>&1
/c/Users/pawan/fm-tactics-lab/.venv/Scripts/python.exe -W ignore -u everything.py geometrismo > everything_geometrismo.log 2>&1
