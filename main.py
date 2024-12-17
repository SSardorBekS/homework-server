import subprocess
from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware

from pydantic import BaseModel
from motor.motor_asyncio import AsyncIOMotorClient
from typing import List, Optional
from bson import ObjectId
import tempfile
import os

app = FastAPI()

origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# MongoDB URI (local MongoDB uchun)
MONGO_URI = "mongodb://localhost:27017"
DATABASE_NAME = "task_db"
USER_COLLECTION = "users"
TASK_COLLECTION = "tasks"
SUBMISSION_COLLECTION = "submissions"

# MongoDB ulanishini o'rnatish
client = AsyncIOMotorClient(MONGO_URI)
db = client[DATABASE_NAME]

# Pydantic modellari
class UserCreate(BaseModel):
    name: Optional[str]
    username: str
    password: str

class TaskCreate(BaseModel):
    title: str
    description: str
    difficulty: str
    input_example: str  # Example input for the task
    output_example: str  # Example expected output for the task


class Task(BaseModel):
    id: str
    title: str
    description: str
    difficulty: str
    input_example: str
    output_example: str


class SubmissionCreate(BaseModel):
    user_id: str
    task_id: str
    code: str
    language: str

class Submission(BaseModel):
    id: str
    user_id: str
    task_id: str
    code: str
    result: str


def object_id_to_str(object_id):
    return str(object_id)

@app.post("/register/")
async def register(user: UserCreate, request: Request):
    user_exists = await db[USER_COLLECTION].find_one({"username": user.username})
    if user_exists:
        raise HTTPException(status_code=400, detail="Username already registered")
    
    new_user = {"username": user.username, "password": user.password, "name": user.name}
    result = await db[USER_COLLECTION].insert_one(new_user)
    return {"id": str(result.inserted_id), "username": user.username}

@app.post("/login/")
async def login(user: UserCreate):
    db_user = await db[USER_COLLECTION].find_one({"username": user.username})
    if not db_user or db_user["password"] != user.password:
        raise HTTPException(status_code=400, detail="Invalid username or password")
    return {"msg": "Login successful"}

@app.get("/tasks/{task_id}", response_model=Task)
async def get_task(task_id: str):
    # Find the task by its ObjectId
    task = await db[TASK_COLLECTION].find_one({"_id": ObjectId(task_id)})
    
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return Task(
        id=str(task["_id"]),
        title=task["title"],
        description=task["description"],
        difficulty=task["difficulty"],
        input_example=task.get("input_example", ""),
        output_example=task.get("output_example", "")
    )


@app.get("/tasks/", response_model=List[Task])
async def get_tasks():
    tasks_cursor = db[TASK_COLLECTION].find()
    tasks = [
        Task(
            id=object_id_to_str(task["_id"]),
            title=task["title"],
            description=task["description"],
            difficulty=task["difficulty"],
            input_example=task.get("input_example", ""),  # Add input_example if exists
            output_example=task.get("output_example", "")  # Add output_example if exists
        ) 
        for task in await tasks_cursor.to_list(length=100)
    ]
    return tasks

@app.post("/tasks/", response_model=Task)
async def create_task(task: TaskCreate):
    # Input validation: check if the required fields are provided
    if not task.title or not task.description or not task.difficulty or not task.input_example or not task.output_example:
        raise HTTPException(status_code=400, detail="All fields (title, description, difficulty, input_example, output_example) are required")

    # Create a new task dictionary with the provided input values
    new_task = {
        "title": task.title, 
        "description": task.description, 
        "difficulty": task.difficulty,
        "input_example": task.input_example,  # Example input for the task
        "output_example": task.output_example  # Expected output for the task
    }

    # Insert the new task into the MongoDB collection
    result = await db[TASK_COLLECTION].insert_one(new_task)

    # Return the newly created task
    return Task(
        id=str(result.inserted_id),  # Convert the ObjectId to a string
        title=task.title,
        description=task.description,
        difficulty=task.difficulty,
        input_example=task.input_example,  # Return input example
        output_example=task.output_example  # Return output example
    )



def run_python_code(code: str) -> str:
    try:
        with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
            f.write(code)
            filename = f.name
            print(f"Temporary Python file created: {filename}")

        result = subprocess.run(["python", filename], capture_output=True, text=True)

        print(f"Subprocess finished with returncode {result.returncode}")
        print(f"stdout: {result.stdout}")
        print(f"stderr: {result.stderr}")

        # Delete the temporary file
        os.remove(filename)

        return result.stdout.strip() if result.returncode == 0 else result.stderr.strip()

    except Exception as e:
        return f"Error running Python code: {e}"


def run_cpp_code(code: str) -> str:
    try:
        # Create a temporary file for the C++ code
        with tempfile.NamedTemporaryFile(suffix=".cpp", mode="w", delete=False) as f:
            f.write(code)
            filename = f.name
        # Compile the C++ code using subprocess
        compile_result = subprocess.run(["g++", filename, "-o", filename + ".out"], capture_output=True, text=True)
        if compile_result.returncode != 0:
            os.remove(filename)
            return compile_result.stderr.strip()

        # Run the compiled C++ program
        exec_result = subprocess.run([filename + ".out"], capture_output=True, text=True)
        os.remove(filename)
        os.remove(filename + ".out")
        return exec_result.stdout.strip() if exec_result.returncode == 0 else exec_result.stderr.strip()
    except Exception as e:
        return f"Error running C++ code: {e}"

@app.post("/submit/", response_model=Submission)
async def submit_code(submission: SubmissionCreate):
    # Run the submitted code based on language
    if submission.language == "python":
        result = run_python_code(submission.code)
    elif submission.language == "cpp":
        result = run_cpp_code(submission.code)
    else:
        raise HTTPException(status_code=400, detail="Unsupported language")

    print(result)
    # Simulating a 'correct' or 'incorrect' check (could be based on the task description or expected output)
    is_correct = "Expected output" in result  # Example check, should be customized

    new_submission = {
        "user_id": submission.user_id,
        "task_id": submission.task_id,
        "code": submission.code,
        "result": "Correct" if is_correct else "Incorrect"
    }
    
    result = await db[SUBMISSION_COLLECTION].insert_one(new_submission)
    return Submission(id=str(result.inserted_id), user_id=submission.user_id, task_id=submission.task_id, code=submission.code, result=new_submission["result"])