from collections import deque
from app.alerts.base import AlertNotification, AlertProvider


class DashboardAlertProvider(AlertProvider):
    """Provedor em memória de alertas recentes para exibição imediata no Dashboard web."""

    def __init__(self, max_alerts: int = 50) -> None:
        self._alerts: deque[AlertNotification] = deque(maxlen=max_alerts)

    def send_alert(self, alert: AlertNotification) -> bool:
        self._alerts.appendleft(alert)
        return True

    def get_recent_alerts(self) -> list[AlertNotification]:
        return list(self._alerts)
