from datetime import timedelta
from celery.schedules import crontab
from config_local import *

broker_url='amqp://guest@localhost//'
result_backend = 'mongodb://localhost:27017/'
mongodb_backend_settings = {
    'database': 'celery',
    'taskmeta_collection': 'taskmeta_collection',
}

timezone = 'MST'
enable_utc = True
# Time in seconds
task_time_limit = 600

# Setup routing so that we don't overwhelm the server wh.
task_routes = {
    'atlas.tasks.command_run': {'queue': 'command_queue'},
}

beat_schedule = {
    'launched_cron': {
        'task': 'atlas.tasks.cron',
        'schedule': timedelta(minutes=60),
        'kwargs': {
            "type": "express",
            "status": "launched",
            "exclude_packages": ["cu_classes_bundle"]
        },
    },
    'classes_cron': {
        'task': 'atlas.tasks.cron',
        'schedule': timedelta(hours=2),
        'kwargs': {
            "include_packages": ["cu_classes_bundle"]
        },
    },
    'installed_cron': {
        'task': 'atlas.tasks.cron',
        'schedule': timedelta(hours=3),
        'kwargs': {
            "type": "express",
            "status": "installed",
            "exclude_packages": ["cu_classes_bundle"]
        },
    },
    'available_sites_check': {
        'task': 'atlas.tasks.available_sites_check',
        'schedule': timedelta(minutes=5),
    },
    'delete_stuck_pending_sites': {
        'task': 'atlas.tasks.delete_stuck_pending_sites',
        'schedule': timedelta(minutes=5),
    },
    'remove_stale_available_sites': {
        'task': 'atlas.tasks.delete_all_available_sites',
        'schedule': crontab(minute=0, hour=3),
    },
    'remove_stale_installed_sites': {
        'task': 'atlas.tasks.take_down_installed_35_day_old_sites',
        'schedule': crontab(minute=0, hour=2),
    },
}
