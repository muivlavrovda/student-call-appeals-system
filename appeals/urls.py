from django.urls import path

from appeals.views import AppealListView

app_name = "appeals"

urlpatterns = [
    path("appeals/", AppealListView.as_view(), name="appeal_list"),
]
