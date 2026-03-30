"""Scheduled insight generation agent (stub with APScheduler)."""

from apscheduler.schedulers.background import BackgroundScheduler

from services.alert_service import AlertService


class InsightAgent:
    def __init__(
        self,
        scheduler: BackgroundScheduler | None = None,
        alert_service: AlertService | None = None,
    ):
        self._alerts = alert_service or AlertService()
        self._scheduler = scheduler or BackgroundScheduler(timezone="UTC")
        self._scheduler.add_job(
            self._placeholder_scheduled_job,
            "interval",
            minutes=15,
            id="datapilot_insight_placeholder",
            replace_existing=True,
        )

    def _placeholder_scheduled_job(self) -> None:
        self._alerts.send_placeholder({"event": "insight_tick"})

    def start_scheduler(self) -> None:
        if not self._scheduler.running:
            self._scheduler.start()

    def shutdown_scheduler(self, wait: bool = False) -> None:
        if self._scheduler.running:
            self._scheduler.shutdown(wait=wait)

    def process(self, *args, **kwargs):
        """Placeholder for batch insight synthesis."""
        raise NotImplementedError
