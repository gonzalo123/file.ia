from chainlit.utils import mount_chainlit
from fastapi import FastAPI
from fastapi.responses import RedirectResponse

from settings import APP_ID

app = FastAPI()

@app.get("/")
async def root():
    return RedirectResponse(url=f"/{APP_ID}")

mount_chainlit(app=app, target="main.py", path=f"/{APP_ID}")