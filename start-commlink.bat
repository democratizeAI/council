@echo off
echo Starting CommLink Specialist in Docker...

docker rm -f commlink-specialist 2>nul

docker run -d ^
  --name commlink-specialist ^
  --network council-network ^
  -p 8088:8088 ^
  -v "%CD%\commlink_specialist.py:/app/commlink_specialist.py:ro" ^
  -v "%CD%\commlink_config.txt:/app/commlink_config.txt:ro" ^
  -v "%CD%\agents:/app/agents:ro" ^
  -v "%CD%\prompts:/app/prompts:ro" ^
  -v "%CD%\tests:/app/tests:ro" ^
  -v "%CD%\ops:/app/ops:ro" ^
  -w /app ^
  python:3.11-slim ^
  sh -c "pip install slack-sdk pyyaml prometheus_client requests aiohttp && python -u commlink_specialist.py"

echo CommLink Specialist starting...
echo Check logs with: docker logs commlink-specialist
echo Check metrics at: http://localhost:8088/metrics
pause 