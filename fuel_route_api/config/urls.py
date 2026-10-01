from django.urls import include, path

from trips.views import index_view

urlpatterns = [
    path("", index_view, name="home"),
    path("api/", include("trips.urls")),
]
