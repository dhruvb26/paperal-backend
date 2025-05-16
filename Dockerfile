FROM python:3.13.3-slim

WORKDIR /project

COPY pyproject.toml .
COPY requirements.txt .

RUN pip install --upgrade pip

RUN pip install --no-cache-dir --use-deprecated=legacy-resolver -r requirements.txt

RUN useradd -m -u 1000 appuser

COPY src/ ./src/

RUN chown -R appuser:appuser /project

EXPOSE 8000

WORKDIR /project/src

USER appuser

CMD ["python", "run.py"]