from celery import Celery
from dotenv import load_dotenv
import os

load_dotenv()

celery_app = Celery(
    'my_crew',
    broker=os.getenv('REDIS_URL'),
    backend=os.getenv('REDIS_URL'),
    include=['api.tasks.process_urls_task']
)

celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
) 