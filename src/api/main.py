from dotenv import load_dotenv
from fastapi import FastAPI
import os
from fastapi.middleware.cors import CORSMiddleware
from api.routes.topic import router as topic_router
from api.routes.search import router as search_router
from api.routes.process import router as process_router
from api.routes.generate import router as generate_router
from api.routes.introduction import router as introduction_router
from api.routes.adapt import router as adapt_router
from api.routes.ocr import router as ocr_router
load_dotenv()
port = os.getenv("PORT")
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
app.include_router(adapt_router, tags=["adapt"])
app.include_router(ocr_router, tags=["ocr"])
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(port))

