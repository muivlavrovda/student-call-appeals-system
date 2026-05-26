from django.urls import path

from appeals.views import AppealCreateView, AppealDetailView, AppealListView

app_name = "appeals"

urlpatterns = [
    path("appeals/", AppealListView.as_view(), name="appeal_list"),
    path("appeals/new/", AppealCreateView.as_view(), name="appeal_create"),
    path("appeals/<int:pk>/", AppealDetailView.as_view(), name="appeal_detail"),
]
