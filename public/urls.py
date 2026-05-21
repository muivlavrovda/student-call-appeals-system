from django.urls import path

from public.views import HomeView

app_name = "public"

urlpatterns = [
    path("", HomeView.as_view(), name="home"),
]
