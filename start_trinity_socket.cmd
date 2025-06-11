@echo off
echo Starting Trinity Socket Mode Handler...

docker run -d --name trinity-socket-trinity ^
  --env-file commlink_config.txt ^
  -v "E:\LAB\socket_mode_handler_trinity.py:/app/socket_mode_handler_trinity.py:ro" ^
  -w /app ^
  python:3.11-slim ^
  sh -c "pip install slack-bolt httpx aiohttp && python socket_mode_handler_trinity.py"

echo Trinity Socket Mode Handler started!
timeout /t 3 /nobreak >nul
docker logs trinity-socket-trinity --tail 10 