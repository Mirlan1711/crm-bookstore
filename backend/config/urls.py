from django.contrib import admin
from django.urls import include, path
from rest_framework_simplejwt.views import TokenRefreshView

from users.views import EmailOrUsernameTokenObtainPairView
from crm_core.openapi import openapi_json, swagger_ui

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/token/", EmailOrUsernameTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("api/auth/", include("users.urls")),
    path("api/", include("crm_core.urls")),
    path("api/openapi.json", openapi_json, name="openapi-json"),
    path("api/docs/", swagger_ui, name="swagger-ui"),
]

