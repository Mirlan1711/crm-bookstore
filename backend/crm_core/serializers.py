from django.db import transaction
from rest_framework import serializers

from .models import ActivityLog, Book, Category, Client, CustomField, Deal, EntityType, OrderItem, Status, Task


class CustomDataValidationMixin:
    entity_type = None

    def validate_custom_data(self, value):
        if value is None:
            return {}
        if not isinstance(value, dict):
            raise serializers.ValidationError("Пользовательские данные должны быть объектом.")

        fields = CustomField.objects.filter(
            entity_type=self.entity_type, is_active=True
        )
        field_map = {field.field_key: field for field in fields}
        unknown_keys = set(value) - set(field_map)
        if unknown_keys:
            raise serializers.ValidationError(
                {key: "Поле не настроено или отключено." for key in unknown_keys}
            )

        errors = {}
        for key, field in field_map.items():
            raw_value = value.get(key)
            if field.is_required and (raw_value is None or raw_value == ""):
                errors[key] = "Поле обязательно для заполнения."
                continue
            if raw_value in (None, ""):
                continue
            if field.data_type == CustomField.DataType.NUMBER:
                try:
                    float(raw_value)
                except (TypeError, ValueError):
                    errors[key] = "Ожидается число."
            elif field.data_type == CustomField.DataType.BOOLEAN and not isinstance(raw_value, bool):
                errors[key] = "Ожидается логическое значение."
            elif field.data_type == CustomField.DataType.SELECT and raw_value not in (field.options or []):
                errors[key] = "Значение отсутствует в списке вариантов."
        if errors:
            raise serializers.ValidationError(errors)
        return value


class StatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = Status
        fields = ("id", "name", "entity_type", "color", "sort_order", "is_final", "is_active")

    def validate_entity_type(self, value):
        if self.instance and self.instance.entity_type != value:
            raise serializers.ValidationError("Тип сущности существующего статуса нельзя изменить.")
        return value


class ClientSerializer(CustomDataValidationMixin, serializers.ModelSerializer):
    entity_type = EntityType.CLIENT
    responsible_name = serializers.CharField(source="responsible.username", read_only=True)
    status_name = serializers.CharField(source="status.name", read_only=True)

    class Meta:
        model = Client
        fields = (
            "id", "name", "phone", "email", "description", "responsible",
            "responsible_name", "status", "status_name", "custom_data",
            "created_at", "updated_at",
        )
        read_only_fields = ("responsible_name", "status_name", "created_at", "updated_at")
        extra_kwargs = {"status": {"required": False, "allow_null": True}}

    def validate_email(self, value):
        return value.strip().lower()

    def create(self, validated_data):
        if validated_data.get("status") is None:
            validated_data.pop("status", None)
        if not validated_data.get("status"):
            status, _ = Status.objects.get_or_create(
                name="Новый", entity_type="client", defaults={"color": "#2563eb"}
            )
            validated_data["status"] = status
        if not validated_data.get("responsible"):
            validated_data["responsible"] = self.context["request"].user
        return super().create(validated_data)


class CategorySerializer(serializers.ModelSerializer):
    book_count = serializers.IntegerField(source="books.count", read_only=True)

    class Meta:
        model = Category
        fields = ("id", "name", "description", "is_active", "book_count")


class BookSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)
    is_low_stock = serializers.BooleanField(read_only=True)

    class Meta:
        model = Book
        fields = (
            "id", "title", "author", "isbn", "category", "category_name", "publisher",
            "publication_year", "description", "price", "stock_quantity", "low_stock_threshold",
            "is_active", "is_low_stock", "created_at", "updated_at",
        )
        read_only_fields = ("category_name", "is_low_stock", "created_at", "updated_at")

    def validate_price(self, value):
        if value < 0:
            raise serializers.ValidationError("Цена не может быть отрицательной.")
        return value


class OrderItemSerializer(serializers.ModelSerializer):
    deal = serializers.PrimaryKeyRelatedField(queryset=Deal.objects.all(), required=False)
    book_title = serializers.CharField(source="book.title", read_only=True)
    total = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = OrderItem
        fields = ("id", "deal", "book", "book_title", "quantity", "unit_price", "total", "inventory_applied")
        read_only_fields = ("book_title", "total", "inventory_applied")
        extra_kwargs = {"deal": {"required": False}, "unit_price": {"required": False}}

    def validate_quantity(self, value):
        if value < 1:
            raise serializers.ValidationError("Количество должно быть больше нуля.")
        return value

    def validate(self, attrs):
        if not attrs.get("unit_price") and attrs.get("book"):
            attrs["unit_price"] = attrs["book"].price
        return attrs


class OrderItemInputSerializer(serializers.Serializer):
    book = serializers.PrimaryKeyRelatedField(queryset=Book.objects.all())
    quantity = serializers.IntegerField(min_value=1)
    unit_price = serializers.DecimalField(max_digits=12, decimal_places=2, required=False)

    def validate(self, attrs):
        if "unit_price" not in attrs:
            attrs["unit_price"] = attrs["book"].price
        return attrs


class DealSerializer(CustomDataValidationMixin, serializers.ModelSerializer):
    entity_type = EntityType.DEAL
    client_name = serializers.CharField(source="client.name", read_only=True)
    responsible_name = serializers.CharField(source="responsible.username", read_only=True)
    status_name = serializers.CharField(source="status.name", read_only=True)
    items = OrderItemInputSerializer(many=True, required=False)

    class Meta:
        model = Deal
        fields = (
            "id", "name", "client", "client_name", "responsible", "responsible_name",
            "status", "status_name", "amount", "description", "planned_end_date",
            "payment_method", "fulfillment_method", "delivery_address", "customer_comment",
            "custom_data", "items", "created_at", "updated_at",
        )
        read_only_fields = ("client_name", "responsible_name", "status_name", "created_at", "updated_at")
        extra_kwargs = {"status": {"required": False, "allow_null": True}}

    def create(self, validated_data):
        items = validated_data.pop("items", [])
        if not validated_data.get("status"):
            status, _ = Status.objects.get_or_create(
                name="Новая", entity_type="deal", defaults={"color": "#2563eb"}
            )
            validated_data["status"] = status
        if not validated_data.get("responsible"):
            validated_data["responsible"] = self.context["request"].user
        with transaction.atomic():
            deal = super().create(validated_data)
            self._replace_items(deal, items, restore_existing=False)
        return deal

    def validate(self, attrs):
        fulfillment_method = attrs.get("fulfillment_method", getattr(self.instance, "fulfillment_method", Deal.FulfillmentMethod.PICKUP))
        address = attrs.get("delivery_address", getattr(self.instance, "delivery_address", ""))
        if fulfillment_method == Deal.FulfillmentMethod.DELIVERY and not address:
            raise serializers.ValidationError({"delivery_address": "Укажите адрес доставки."})
        return attrs

    def update(self, instance, validated_data):
        items = validated_data.pop("items", None)
        with transaction.atomic():
            instance = super().update(instance, validated_data)
            if items is not None:
                self._replace_items(instance, items, restore_existing=True)
            else:
                self._sync_inventory_for_status(instance)
        return instance

    def _is_cancelled(self, deal):
        status_name = (deal.status.name if deal.status_id else "").strip().lower()
        return status_name in {"отменён", "отменен", "отменённый", "cancelled", "canceled"}

    def _restore_item(self, item):
        if item.inventory_applied:
            item.book.stock_quantity += item.quantity
            item.book.save(update_fields=["stock_quantity", "updated_at"])
            item.inventory_applied = False
            item.save(update_fields=["inventory_applied"])

    def _apply_item(self, item):
        book = item.book
        if book.stock_quantity < item.quantity:
            raise serializers.ValidationError(
                {"items": f"Недостаточно книги «{book.title}» на складе. Остаток: {book.stock_quantity}."}
            )
        book.stock_quantity -= item.quantity
        book.save(update_fields=["stock_quantity", "updated_at"])
        item.inventory_applied = True
        item.save(update_fields=["inventory_applied"])

    def _replace_items(self, deal, items, restore_existing):
        if restore_existing:
            for old_item in deal.items.select_related("book").all():
                self._restore_item(old_item)
            deal.items.all().delete()

        total = 0
        for raw_item in items:
            raw_item.pop("deal", None)
            item = OrderItem.objects.create(deal=deal, **raw_item)
            if not self._is_cancelled(deal):
                self._apply_item(item)
            else:
                item.inventory_applied = False
                item.save(update_fields=["inventory_applied"])
            total += item.total

        if items:
            deal.amount = total
            deal.save(update_fields=["amount", "updated_at"])

    def _sync_inventory_for_status(self, deal):
        cancelled = self._is_cancelled(deal)
        for item in deal.items.select_related("book").all():
            if cancelled:
                self._restore_item(item)
            elif not item.inventory_applied:
                self._apply_item(item)


class TaskSerializer(CustomDataValidationMixin, serializers.ModelSerializer):
    entity_type = EntityType.TASK
    assignee_name = serializers.CharField(source="assignee.username", read_only=True)
    client_name = serializers.CharField(source="client.name", read_only=True)
    deal_name = serializers.CharField(source="deal.name", read_only=True)
    status_name = serializers.CharField(source="status.name", read_only=True)

    class Meta:
        model = Task
        fields = (
            "id", "title", "description", "assignee", "assignee_name", "client", "client_name",
            "deal", "deal_name", "status", "status_name", "priority", "due_date", "custom_data",
            "created_at", "updated_at",
        )
        read_only_fields = (
            "assignee_name", "client_name", "deal_name", "status_name", "created_at", "updated_at",
        )
        extra_kwargs = {"status": {"required": False, "allow_null": True}}

    def validate(self, attrs):
        deal = attrs.get("deal")
        client = attrs.get("client")
        if deal and client and deal.client_id != client.id:
            raise serializers.ValidationError({"client": "Клиент задачи должен совпадать с клиентом сделки."})
        if deal and not client:
            attrs["client"] = deal.client
        return attrs

    def create(self, validated_data):
        if not validated_data.get("status"):
            status, _ = Status.objects.get_or_create(
                name="Новая", entity_type=EntityType.TASK, defaults={"color": "#2563eb"}
            )
            validated_data["status"] = status
        if not validated_data.get("assignee"):
            validated_data["assignee"] = self.context["request"].user
        return super().create(validated_data)


class CustomFieldSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomField
        fields = (
            "id", "name", "field_key", "entity_type", "data_type", "options",
            "is_required", "is_active", "sort_order",
        )

    def validate_field_key(self, value):
        return value.strip().lower()

    def validate(self, attrs):
        data_type = attrs.get("data_type", getattr(self.instance, "data_type", None))
        options = attrs.get("options", getattr(self.instance, "options", []))
        if data_type == CustomField.DataType.SELECT:
            if not isinstance(options, list) or not options or not all(isinstance(item, str) and item.strip() for item in options):
                raise serializers.ValidationError({"options": "Для списка укажите непустой массив строк."})
        elif options:
            raise serializers.ValidationError({"options": "Варианты можно задавать только для поля-списка."})
        return attrs


class ActivityLogSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)
    entity_type_name = serializers.CharField(source="get_entity_type_display", read_only=True)

    class Meta:
        model = ActivityLog
        fields = (
            "id", "username", "action", "entity_type", "entity_type_name", "entity_id",
            "description", "ip_address", "created_at",
        )

