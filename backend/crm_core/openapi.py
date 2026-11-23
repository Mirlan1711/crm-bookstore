import json

from django.http import HttpResponse, JsonResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny


SCHEMA = {
    "openapi": "3.0.3",
    "info": {
        "title": "BookStore CRM — API интеграции с 1С",
        "version": "1.0.0",
        "description": "Методы обмена клиентами, каталогом книг и заказами между CRM и 1С.",
    },
    "servers": [{"url": "/api"}],
    "components": {"securitySchemes": {"IntegrationKey": {"type": "apiKey", "in": "header", "name": "X-Integration-Key"}}},
    "security": [{"IntegrationKey": []}],
    "paths": {
        "/integration/clients/": {
            "get": {"summary": "Получить клиентов", "parameters": [{"$ref": "#/components/parameters/UpdatedAfter"}], "responses": {"200": {"description": "Список клиентов"}}},
            "post": {"summary": "Добавить или обновить клиента", "requestBody": {"required": True, "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ClientInput"}}}}, "responses": {"200": {"description": "Клиент обновлён"}, "201": {"description": "Клиент создан"}}},
        },
        "/integration/books/": {
            "get": {"summary": "Получить книги и остатки", "parameters": [{"$ref": "#/components/parameters/UpdatedAfter"}], "responses": {"200": {"description": "Список книг"}}},
            "post": {"summary": "Добавить или обновить книгу по ISBN", "requestBody": {"required": True, "content": {"application/json": {"schema": {"$ref": "#/components/schemas/BookInput"}}}}, "responses": {"200": {"description": "Книга обновлена"}, "201": {"description": "Книга создана"}}},
        },
        "/integration/orders/": {
            "get": {"summary": "Получить заказы", "parameters": [{"$ref": "#/components/parameters/UpdatedAfter"}], "responses": {"200": {"description": "Список заказов"}}},
            "post": {"summary": "Передать заказ из 1С", "requestBody": {"required": True, "content": {"application/json": {"schema": {"$ref": "#/components/schemas/OrderInput"}}}}, "responses": {"201": {"description": "Заказ создан"}}},
        },
        "/integration/orders/{order_id}/status/": {
            "patch": {"summary": "Изменить статус заказа", "parameters": [{"name": "order_id", "in": "path", "required": True, "schema": {"type": "integer"}}], "requestBody": {"required": True, "content": {"application/json": {"schema": {"type": "object", "properties": {"status_name": {"type": "string"}}}}}}, "responses": {"200": {"description": "Статус изменён"}}},
        },
    },
}
SCHEMA["components"]["parameters"] = {"UpdatedAfter": {"name": "updated_after", "in": "query", "required": False, "schema": {"type": "string", "format": "date-time"}}}
SCHEMA["components"]["schemas"] = {
    "ClientInput": {"type": "object", "required": ["name"], "properties": {"name": {"type": "string"}, "email": {"type": "string"}, "phone": {"type": "string"}}},
    "BookInput": {"type": "object", "required": ["isbn", "title"], "properties": {"isbn": {"type": "string"}, "title": {"type": "string"}, "author": {"type": "string"}, "category": {"type": "string"}, "price": {"type": "number"}, "stock_quantity": {"type": "integer"}}},
    "OrderInput": {"type": "object", "required": ["client_id", "items"], "properties": {"number": {"type": "string"}, "client_id": {"type": "integer"}, "client_email": {"type": "string"}, "status_name": {"type": "string"}, "items": {"type": "array", "items": {"type": "object", "properties": {"book_id": {"type": "integer"}, "isbn": {"type": "string"}, "quantity": {"type": "integer"}, "unit_price": {"type": "number"}}}}}},
}


@api_view(["GET"])
@permission_classes([AllowAny])
def openapi_json(request):
    return JsonResponse(SCHEMA)


@api_view(["GET"])
@permission_classes([AllowAny])
def swagger_ui(request):
    html = """<!doctype html><html lang='ru'><head><meta charset='utf-8'><title>BookStore CRM API</title><link rel='stylesheet' href='https://unpkg.com/swagger-ui-dist@5/swagger-ui.css'></head><body><div id='swagger-ui'></div><script src='https://unpkg.com/swagger-ui-dist@5/swagger-ui-bundle.js'></script><script>window.ui=SwaggerUIBundle({url:'/api/openapi.json',dom_id:'#swagger-ui'});</script></body></html>"""
    return HttpResponse(html)
