import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routes.topic import router as topic_router
from api.routes.search import router as search_router

load_dotenv()

app = FastAPI(
    title="Paperal",
    description="This is the FastAPI backend for Paperal",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {
        "message": "Welcome to Paperal",
    }


app.include_router(topic_router, tags=["topics"])
app.include_router(search_router, tags=["search"])

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000)
