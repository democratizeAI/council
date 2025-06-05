FROM pytorch/pytorch:2.3.0-cuda12.1-cudnn8-runtime

# 1. copy code
WORKDIR /app
COPY trainer_worker.py requirements.txt ./

# 2. install deps (bitsandbytes, transformers, accelerate etc.)
RUN pip install --no-cache-dir -r requirements.txt

# 3. default command keeps container alive & tails logs
CMD ["python", "trainer_worker.py", "--watch", "tasks/lora_queue.json"] 