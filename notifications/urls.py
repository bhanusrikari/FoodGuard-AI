from django.urls import path

from notifications.views import NotificationDetailView, NotificationListView

app_name = "notifications"

urlpatterns = [
    path("", NotificationListView.as_view(), name="list"),
    path("<int:pk>/", NotificationDetailView.as_view(), name="detail"),
]
