import subprocess

def run_uvicorn():
    """Run the FastAPI app using uvicorn."""
    return ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]

def run_celery():
    """Run the Celery worker."""
    return ["celery", "-A", "api.celery_app:celery_app", "worker", "--pool=threads", "--loglevel=info"]

if __name__ == "__main__":
    uvicorn_process = subprocess.Popen(run_uvicorn())
    celery_process = subprocess.Popen(run_celery())

    uvicorn_process.wait()
    celery_process.wait()