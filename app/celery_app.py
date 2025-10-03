from celery import Celery
from app.config import settings

# Create Celery instance
celery_app = Celery(
    'emilai',
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[
        'app.services.cv_parser',
        'app.services.ai_scoring',
        'app.services.email_service'
    ]
)

# Celery configuration
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,  # 5 minutes
)

@celery_app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')