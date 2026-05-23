from django.urls import path

from public.views import AboutView, CategoriesView, FeedbackView, HomeView

app_name = "public"

urlpatterns = [
    path("", HomeView.as_view(), name="home"),
    path("about/", AboutView.as_view(), name="about"),
    path("categories/", CategoriesView.as_view(), name="categories"),
    path("feedback/", FeedbackView.as_view(), name="feedback"),
]
