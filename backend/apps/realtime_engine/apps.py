from django.apps import AppConfig


class RealtimeEngineConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.realtime_engine'
    verbose_name = 'Real-Time Market Engine'

    def ready(self):
        """Initialize real-time systems on app startup."""
        import apps.realtime_engine.signals  # noqa