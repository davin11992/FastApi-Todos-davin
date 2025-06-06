# from fastapi import FastAPI, HTTPException
# from fastapi.responses import HTMLResponse
# from pydantic import BaseModel
# import json
# import os
# import logging
# import time
# from multiprocessing import Queue
# from os import getenv
# from fastapi import Request
# from prometheus_fastapi_instrumentator import Instrumentator
# from logging_loki import LokiQueueHandler

# app = FastAPI()

# # Prometheus 메트릭스 엔드포인트 (/metrics)
# Instrumentator().instrument(app).expose(app, endpoint="/metrics")

# loki_logs_handler = LokiQueueHandler(
#     Queue(-1),
#     url=getenv("LOKI_ENDPOINT"),
#     tags={"application": "fastapi"},
#     version="1",
# )

# # Custom access logger (ignore Uvicorn's default logging)
# custom_logger = logging.getLogger("custom.access")
# custom_logger.setLevel(logging.INFO)

# # Add Loki handler (assuming `loki_logs_handler` is correctly configured)
# custom_logger.addHandler(loki_logs_handler)

# async def log_requests(request: Request, call_next):
#     start_time = time.time()
#     response = await call_next(request)
#     duration = time.time() - start_time  # Compute response time

#     log_message = (
#         f'{request.client.host} - "{request.method} {request.url.path} HTTP/1.1" {response.status_code} {duration:.3f}s'
#     )

#     # **Only log if duration exists**
#     if duration:
#         custom_logger.info(log_message)

#     return response

# app.middleware("http")(log_requests)

# # To-Do 항목 모델
# class TodoItem(BaseModel):
#     id: int
#     title: str
#     description: str
#     completed: bool

# # JSON 파일 경로
# TODO_FILE = "todo.json"

# # JSON 파일에서 To-Do 항목 로드
# def load_todos():
#     if os.path.exists(TODO_FILE):
#         with open(TODO_FILE, "r") as file:
#             return json.load(file)
#     return []

# # JSON 파일에 To-Do 항목 저장
# def save_todos(todos):
#     with open(TODO_FILE, "w") as file:
#         json.dump(todos, file, indent=4)

# # To-Do 목록 조회
# @app.get("/todos", response_model=list[TodoItem])
# def get_todos():
#     return load_todos()

# # 신규 To-Do 항목 추가
# @app.post("/todos", response_model=TodoItem)
# def create_todo(todo: TodoItem):
#     todos = load_todos()
#     todos.append(todo.dict())
#     save_todos(todos)
#     return todo

# # To-Do 항목 수정
# @app.put("/todos/{todo_id}", response_model=TodoItem)
# def update_todo(todo_id: int, updated_todo: TodoItem):
#     todos = load_todos()
#     for todo in todos:
#         if todo["id"] == todo_id:
#             todo.update(updated_todo.dict())
#             save_todos(todos)
#             return updated_todo
#     raise HTTPException(status_code=404, detail="To-Do item not found")

# # To-Do 항목 삭제
# @app.delete("/todos/{todo_id}", response_model=dict)
# def delete_todo(todo_id: int):
#     todos = load_todos()
#     todos = [todo for todo in todos if todo["id"] != todo_id]
#     save_todos(todos)
#     return {"message": "To-Do item deleted"}

# # HTML 파일 서빙
# @app.get("/", response_class=HTMLResponse)
# def read_root():
#     with open("templates/index.html", "r", encoding="utf-8") as file:
#         content = file.read()
#     return HTMLResponse(content=content)

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from prometheus_fastapi_instrumentator import Instrumentator
from logging_loki import LokiQueueHandler
from logging.handlers import QueueListener
from multiprocessing import Queue
import json
import os
import logging
import time

app = FastAPI()

# Prometheus 메트릭스 엔드포인트 (/metrics)
Instrumentator().instrument(app).expose(app, endpoint="/metrics")

# Loki 로그 핸들러 설정
queue = Queue(-1)
loki_logs_handler = LokiQueueHandler(
    queue,
    url=os.getenv("LOKI_ENDPOINT"),
    tags={"application": "fastapi"},
    version="1",
)

custom_logger = logging.getLogger("custom.access")
custom_logger.setLevel(logging.INFO)
custom_logger.addHandler(loki_logs_handler)  # ✅ 수정됨

listener = QueueListener(queue, loki_logs_handler.handler)  # ✅ 수정됨
listener.start()

custom_logger.info("✅ FastAPI 서버가 시작되었고, Loki로 로그 전송을 시도합니다.")

# 미들웨어
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time
    log_message = (
        f'{request.client.host} - "{request.method} {request.url.path} HTTP/1.1" '
        f'{response.status_code} {duration:.3f}s'
    )
    custom_logger.info(log_message)
    return response

# ----------------- 이하 동일 -----------------

class TodoItem(BaseModel):
    id: int
    title: str
    description: str
    completed: bool

TODO_FILE = "todo.json"

def load_todos():
    if os.path.exists(TODO_FILE):
        with open(TODO_FILE, "r") as file:
            return json.load(file)
    return []

def save_todos(todos):
    with open(TODO_FILE, "w") as file:
        json.dump(todos, file, indent=4)

@app.get("/todos", response_model=list[TodoItem])
def get_todos():
    return load_todos()

@app.post("/todos", response_model=TodoItem)
def create_todo(todo: TodoItem):
    todos = load_todos()
    todos.append(todo.dict())
    save_todos(todos)
    return todo

@app.put("/todos/{todo_id}", response_model=TodoItem)
def update_todo(todo_id: int, updated_todo: TodoItem):
    todos = load_todos()
    for todo in todos:
        if todo["id"] == todo_id:
            todo.update(updated_todo.dict())
            save_todos(todos)
            return updated_todo
    raise HTTPException(status_code=404, detail="To-Do item not found")

@app.delete("/todos/{todo_id}", response_model=dict)
def delete_todo(todo_id: int):
    todos = load_todos()
    todos = [todo for todo in todos if todo["id"] != todo_id]
    save_todos(todos)
    return {"message": "To-Do item deleted"}

@app.get("/", response_class=HTMLResponse)
def read_root():
    with open("templates/index.html", "r", encoding="utf-8") as file:
        return HTMLResponse(content=file.read())
