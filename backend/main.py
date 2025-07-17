from fastapi import FastAPI
from upload_and_train.routes import router

app = FastAPI()
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Or ["http://localhost:3000"] if your frontend runs on port 3000
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# The main upload and train logic is in the 'upload_and_train' package
app.include_router(router) 