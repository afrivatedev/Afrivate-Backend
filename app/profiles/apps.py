from django.apps import AppConfig

# write your app configuration here. For example, you can import your signals in the ready method to ensure they are registered when the app is ready.
class ProfilesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'profiles'

    def ready(self):
        import profiles.signals
