from django.urls import path

from public.views import (
    AboutView,
    AnalyticsView,
    CategoriesView,
    ContactsView,
    DocumentsView,
    FaqView,
    FeedbackView,
    HomeView,
    HowToView,
    ProcessView,
)

app_name = "public"

urlpatterns = [
    path("", HomeView.as_view(), name="home"),
    path("about/", AboutView.as_view(), name="about"),
    path("how-to/", HowToView.as_view(), name="how_to"),
    path("process/", ProcessView.as_view(), name="process"),
    path("categories/", CategoriesView.as_view(), name="categories"),
    path("analytics/", AnalyticsView.as_view(), name="analytics"),
    path("faq/", FaqView.as_view(), name="faq"),
    path("contacts/", ContactsView.as_view(), name="contacts"),
    path("documents/", DocumentsView.as_view(), name="documents"),
    path("feedback/", FeedbackView.as_view(), name="feedback"),
]
