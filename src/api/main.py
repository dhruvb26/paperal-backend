from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routes.topic import router as topic_router
from api.routes.search import router as search_router
from api.routes.process import router as process_router
from api.routes.generate import router as generate_router
from api.routes.introduction import router as introduction_router

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
app.include_router(process_router, tags=["process"])
app.include_router(generate_router, tags=["generate"])
app.include_router(introduction_router, tags=["introduction"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, port=8000)
