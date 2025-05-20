from mexc_api import get_balance_t
from fastapi import FastAPI, Header, Form, Request
from fastapi.responses import FileResponse, HTMLResponse, Response

app = FastAPI()

#
@app.get("/")
def root():
    return HTMLResponse(content="<h2>Добро пожаловать в NARCISS</h2>")

#получение баланса
@app.get("/api/balance")
def get_balance():
    return get_balance_t()

