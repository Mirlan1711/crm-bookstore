from django.contrib import admin

from .models import ActivityLog, Book, Category, Client, CustomField, Deal, OrderItem, Status, Task


@admin.register(Status)
class StatusAdmin(admin.ModelAdmin):
    list_display = ("name", "entity_type", "sort_order", "is_final", "is_active")
    list_filter = ("entity_type", "is_active")


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "responsible", "status", "created_at")
    search_fields = ("name", "email", "phone")
    list_filter = ("status", "created_at")


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active")
    search_fields = ("name",)
    list_filter = ("is_active",)


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ("title", "author", "category", "price", "stock_quantity", "is_active")
    search_fields = ("title", "author", "isbn")
    list_filter = ("category", "is_active", "created_at")


@admin.register(Deal)
class DealAdmin(admin.ModelAdmin):
    list_display = ("name", "client", "amount", "responsible", "status")
    search_fields = ("name", "client__name")
    list_filter = ("status", "created_at")


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ("deal", "book", "quantity", "unit_price", "inventory_applied")
    search_fields = ("deal__name", "book__title")


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ("title", "assignee", "priority", "status", "due_date")
    search_fields = ("title", "description")
    list_filter = ("priority", "status", "due_date")


@admin.register(CustomField)
class CustomFieldAdmin(admin.ModelAdmin):
    list_display = ("name", "field_key", "entity_type", "data_type", "is_required", "is_active")
    list_filter = ("entity_type", "data_type", "is_active")


@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ("action", "entity_type", "entity_id", "user", "created_at")
    list_filter = ("action", "entity_type", "created_at")
    readonly_fields = [field.name for field in ActivityLog._meta.fields]

