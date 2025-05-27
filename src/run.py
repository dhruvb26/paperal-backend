import subprocess

def run_uvicorn():
    """Run the FastAPI app using uvicorn."""
    return ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

if __name__ == "__main__":
    uvicorn_process = subprocess.Popen(run_uvicorn())
    uvicorn_process.wait()