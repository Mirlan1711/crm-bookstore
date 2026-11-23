from rest_framework.routers import DefaultRouter

from django.urls import path

from .views import (
    ActivityLogViewSet,
    BookViewSet,
    CategoryViewSet,
    ClientStatusViewSet,
    ClientViewSet,
    CustomFieldViewSet,
    DealStatusViewSet,
    DealViewSet,
    OrderItemViewSet,
    TaskStatusViewSet,
    StatusViewSet,
    TaskViewSet,
    dashboard_stats,
)
from .integration import integration_books, integration_clients, integration_order_status, integration_orders

router = DefaultRouter()
router.register("clients", ClientViewSet, basename="clients")
router.register("categories", CategoryViewSet, basename="categories")
router.register("books", BookViewSet, basename="books")
router.register("client-statuses", ClientStatusViewSet, basename="client-statuses")
router.register("deals", DealViewSet, basename="deals")
router.register("order-items", OrderItemViewSet, basename="order-items")
router.register("deal-statuses", DealStatusViewSet, basename="deal-statuses")
router.register("tasks", TaskViewSet, basename="tasks")
router.register("task-statuses", TaskStatusViewSet, basename="task-statuses")
router.register("statuses", StatusViewSet, basename="statuses")
router.register("custom-fields", CustomFieldViewSet, basename="custom-fields")
router.register("activity-log", ActivityLogViewSet, basename="activity-log")

urlpatterns = router.urls + [
    path("dashboard/stats/", dashboard_stats, name="dashboard-stats"),
    path("integration/clients/", integration_clients, name="integration-clients"),
    path("integration/books/", integration_books, name="integration-books"),
    path("integration/orders/", integration_orders, name="integration-orders"),
    path("integration/orders/<int:order_id>/status/", integration_order_status, name="integration-order-status"),
]

