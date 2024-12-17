import subprocess
import tempfile
import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List

app = FastAPI()

# Kodni yuborish uchun model
class SubmissionCreate(BaseModel):
    user_id: str
    task_id: str
    language: str  # Tilni tanlash
    code: str

class Submission(BaseModel):
    id: str
    user_id: str
    task_id: str
    code: str
    result: str

# Docker konteynerini ishga tushirish funktsiyasi
def run_code_in_docker(language: str, code: str):
    try:
        # Kodni vaqtincha faylga saqlash
        with tempfile.NamedTemporaryFile(delete=False, mode='w') as f:
            f.write(code)
            file_path = f.name

        # Docker konteyneri tanlash (tilga qarab)
        if language == 'python':
            docker_command = [
                "docker", "run", "--rm", "-v", f"{os.getcwd()}:/app",
                "python:3.10-slim", "python", "/app/app/docker/check_code.py", file_path
            ]
        elif language == 'cpp':
            docker_command = [
                "docker", "run", "--rm", "-v", f"{os.getcwd()}:/app",
                "gcc:latest", "bash", "-c", f"g++ /app/{file_path} -o /app/main && /app/main"
            ]
        else:
            raise HTTPException(status_code=400, detail="Unsupported language")

        # Docker konteynerini ishga tushirish
        result = subprocess.run(docker_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        if result.returncode == 0:
            return result.stdout.decode("utf-8")
        else:
            return f"Error: {result.stderr.decode('utf-8')}"

    except Exception as e:
        return str(e)

# Kodni yuborish va tekshirish
@app.post("/submit/", response_model=Submission)
async def submit_code(submission: SubmissionCreate):
    # Docker konteynerida kodni bajarish
    result = run_code_in_docker(submission.language, submission.code)
    
    # Natijani saqlash (odatda siz buni bazaga saqlaysiz)
    new_submission = {
        "user_id": submission.user_id,
        "task_id": submission.task_id,
        "code": submission.code,
        "result": result
    }
    
    return Submission(id="some_generated_id", user_id=submission.user_id, task_id=submission.task_id, code=submission.code, result=result)
