import subprocess
import tempfile
import os

def run_code_in_docker(code: str):
    try:
        # Foydalanuvchi tomonidan yuborilgan kodni faylga saqlaymiz
        with tempfile.NamedTemporaryFile(delete=False, mode='w') as f:
            f.write(code)
            file_path = f.name
        
        # Docker komandasini yaratish
        docker_command = [
            "docker", "run", "--rm", "-v", f"{os.getcwd()}:/app",
            "python:3.10-slim", "python", "/app/app/docker/check_code.py", file_path
        ]
        
        # Docker konteynerini ishga tushirish va natijani olish
        result = subprocess.run(docker_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Natijani qaytarish
        if result.returncode == 0:
            return result.stdout.decode("utf-8")
        else:
            return f"Error: {result.stderr.decode('utf-8')}"
    
    except Exception as e:
        return str(e)
