from typing import Any, cast

from arq.connections import RedisSettings
from arq.cron import cron
from arq.typing import WorkerCoroutine

from app.core.config import get_settings
from app.core.logging import configure_logging
from app.db.session import SessionFactory
from app.workers.tasks import publish_outbox_events


async def startup(context: dict[str, Any]) -> None:
    configure_logging()
    context["session_factory"] = SessionFactory


class WorkerSettings:
    functions = [publish_outbox_events]
    cron_jobs = [
        cron(
            cast(WorkerCoroutine, publish_outbox_events),
            second={0, 10, 20, 30, 40, 50},
        )
    ]
    on_startup = startup
    redis_settings = RedisSettings.from_dsn(get_settings().redis_url)
    health_check_interval = 30
