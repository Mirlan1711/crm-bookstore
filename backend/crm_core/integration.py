from datetime import datetime
from functools import wraps
from hmac import compare_digest

from django.conf import settings
from django.db import transaction
from django.utils.dateparse import parse_datetime
from rest_framework import permissions, serializers
from rest_framework.authentication import BaseAuthentication
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.response import Response

from .models import Book, Category, Client, Deal, EntityType, OrderItem, Status
from .serializers import BookSerializer, ClientSerializer, DealSerializer


class IntegrationKeyPermission(permissions.BasePermission):
    message = "Требуется корректный ключ интеграции 1С."

    def has_permission(self, request, view):
        provided = request.headers.get("X-Integration-Key", "")
        expected = getattr(settings, "INTEGRATION_API_KEY", "")
        return bool(expected and provided and compare_digest(provided, expected))


def integration_endpoint(methods):
    def decorator(func):
        decorated = permission_classes([IntegrationKeyPermission])(func)
        decorated = authentication_classes([])(decorated)
        return api_view(methods)(decorated)
    return decorator


def parse_updated_after(request):
    value = request.query_params.get("updated_after")
    if not value:
        return None
    parsed = parse_datetime(value)
    if parsed is None:
        raise serializers.ValidationError({"updated_after": "Используйте ISO-формат даты и времени."})
    return parsed


def order_payload(order):
    return {
        "id": order.id,
        "number": order.name,
        "client_id": order.client_id,
        "client_name": order.client.name,
        "status": order.status.name,
        "amount": str(order.amount),
        "description": order.description,
        "payment_method": order.payment_method,
        "fulfillment_method": order.fulfillment_method,
        "delivery_address": order.delivery_address,
        "customer_comment": order.customer_comment,
        "created_at": order.created_at.isoformat(),
        "updated_at": order.updated_at.isoformat(),
        "items": [
            {
                "book_id": item.book_id,
                "isbn": item.book.isbn,
                "title": item.book.title,
                "quantity": item.quantity,
                "unit_price": str(item.unit_price),
            }
            for item in order.items.select_related("book").all()
        ],
    }


@integration_endpoint(["GET", "POST"])
def integration_clients(request):
    if request.method == "GET":
        updated_after = parse_updated_after(request)
        queryset = Client.objects.select_related("status").order_by("id")
        if updated_after:
            queryset = queryset.filter(updated_at__gt=updated_after)
        return Response({"items": ClientSerializer(queryset, many=True).data})

    data = request.data
    email = (data.get("email") or "").strip().lower()
    if email:
        client, created = Client.objects.get_or_create(
            email=email,
            defaults={"name": data.get("name", "Без имени"), "phone": data.get("phone", "")},
        )
        if not created:
            client.name = data.get("name", client.name)
            client.phone = data.get("phone", client.phone)
            client.description = data.get("description", client.description)
            client.save()
    else:
        client = Client.objects.create(
            name=data.get("name", "Без имени"), phone=data.get("phone", ""), email="",
            description=data.get("description", ""),
            status=Status.objects.get_or_create(name="Новый", entity_type=EntityType.CLIENT)[0],
        )
        created = True
    return Response({"created": created, "client": ClientSerializer(client).data}, status=201 if created else 200)


@integration_endpoint(["GET", "POST"])
def integration_books(request):
    if request.method == "GET":
        updated_after = parse_updated_after(request)
        queryset = Book.objects.select_related("category").order_by("id")
        if updated_after:
            queryset = queryset.filter(updated_at__gt=updated_after)
        return Response({"items": BookSerializer(queryset, many=True).data})

    data = request.data
    isbn = (data.get("isbn") or "").strip()
    if not isbn:
        return Response({"detail": "ISBN обязателен для синхронизации книги."}, status=400)
    category_name = (data.get("category") or "Без категории").strip()
    category, _ = Category.objects.get_or_create(name=category_name)
    book, created = Book.objects.get_or_create(
        isbn=isbn,
        defaults={
            "title": data.get("title", "Без названия"), "author": data.get("author", ""),
            "category": category, "price": data.get("price", 0),
            "stock_quantity": data.get("stock_quantity", 0),
        },
    )
    if not created:
        for field in ("title", "author", "publisher", "description", "price", "stock_quantity", "low_stock_threshold", "is_active"):
            if field in data:
                setattr(book, field, data[field])
        book.category = category
        book.save()
    return Response({"created": created, "book": BookSerializer(book).data}, status=201 if created else 200)


@integration_endpoint(["GET", "POST"])
def integration_orders(request):
    if request.method == "GET":
        updated_after = parse_updated_after(request)
        queryset = Deal.objects.select_related("client", "status").prefetch_related("items__book").order_by("id")
        if updated_after:
            queryset = queryset.filter(updated_at__gt=updated_after)
        status_name = request.query_params.get("status")
        if status_name:
            queryset = queryset.filter(status__name__iexact=status_name)
        return Response({"items": [order_payload(order) for order in queryset]})

    data = request.data
    client_id = data.get("client_id")
    client = Client.objects.filter(id=client_id).first() if client_id else None
    if not client and data.get("client_email"):
        client = Client.objects.filter(email__iexact=data["client_email"].strip()).first()
    if not client:
        return Response({"detail": "Клиент не найден. Передайте client_id или client_email."}, status=400)

    status = None
    if data.get("status"):
        status = Status.objects.filter(entity_type=EntityType.DEAL, id=data["status"]).first()
    if not status and data.get("status_name"):
        status = Status.objects.filter(entity_type=EntityType.DEAL, name__iexact=data["status_name"]).first()
    if not status:
        status = Status.objects.filter(entity_type=EntityType.DEAL, is_active=True).order_by("sort_order", "id").first()

    normalized_items = []
    for item in data.get("items", []):
        book = Book.objects.filter(id=item.get("book_id")).first() if item.get("book_id") else Book.objects.filter(isbn=item.get("isbn", "")).first()
        if not book:
            return Response({"detail": f"Книга не найдена: {item.get('isbn') or item.get('book_id')}."}, status=400)
        normalized_items.append({"book": book.id, "quantity": item.get("quantity", 1), "unit_price": item.get("unit_price", book.price)})

    payload = {
        "name": data.get("number") or data.get("name") or f"1С-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "client": client.id, "status": status.id if status else None,
        "description": data.get("description", ""), "amount": data.get("amount", 0),
        "payment_method": data.get("payment_method", "card"),
        "fulfillment_method": data.get("fulfillment_method", "pickup"),
        "delivery_address": data.get("delivery_address", ""),
        "customer_comment": data.get("customer_comment", ""),
        "items": normalized_items,
    }
    serializer = DealSerializer(data=payload, context={"request": request})
    serializer.is_valid(raise_exception=True)
    order = serializer.save()
    return Response({"created": True, "order": order_payload(order)}, status=201)


@integration_endpoint(["PATCH"])
def integration_order_status(request, order_id):
    if request.method != "PATCH":
        return Response({"detail": "Используйте PATCH для изменения статуса."}, status=405)
    order = Deal.objects.select_related("client", "status").prefetch_related("items__book").filter(id=order_id).first()
    if not order:
        return Response({"detail": "Заказ не найден."}, status=404)
    status = Status.objects.filter(entity_type=EntityType.DEAL, is_active=True).filter(
        id=request.data.get("status")
    ).first() if request.data.get("status") else Status.objects.filter(
        entity_type=EntityType.DEAL, is_active=True, name__iexact=request.data.get("status_name", "")
    ).first()
    if not status:
        return Response({"detail": "Статус заказа не найден."}, status=400)
    serializer = DealSerializer(
        order, data={"status": status.id}, partial=True, context={"request": request}
    )
    serializer.is_valid(raise_exception=True)
    order = serializer.save()
    return Response({"order": order_payload(order)})
