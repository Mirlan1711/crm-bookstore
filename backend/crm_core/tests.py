from django.contrib.auth import get_user_model
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APITestCase

from .models import ActivityLog, Book, Category, Client, CustomField, OrderItem, Status


class CRMApiTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="tester", password="StrongPass123!", role="manager"
        )
        self.client.force_authenticate(self.user)
        self.client_status, _ = Status.objects.get_or_create(name="Новый", entity_type="client")
        self.deal_status, _ = Status.objects.get_or_create(name="Новая", entity_type="deal")
        self.task_status, _ = Status.objects.get_or_create(name="Новая", entity_type="task")

    def test_client_and_deal_creation(self):
        client_response = self.client.post("/api/clients/", {"name": "ООО Тест"}, format="json")
        self.assertEqual(client_response.status_code, 201)
        deal_response = self.client.post(
            "/api/deals/",
            {"name": "Первая сделка", "client": client_response.data["id"], "amount": "1500"},
            format="json",
        )
        self.assertEqual(deal_response.status_code, 201)
        self.assertEqual(deal_response.data["client_name"], "ООО Тест")

    def test_task_filter_by_due_date(self):
        response = self.client.post(
            "/api/tasks/",
            {"title": "Позвонить клиенту", "due_date": str(timezone.localdate())},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        filtered = self.client.get("/api/tasks/?due=today")
        self.assertEqual(filtered.status_code, 200)
        self.assertEqual(filtered.data["count"], 1)
        self.assertEqual(len(filtered.data["results"]), 1)

    def test_custom_field_validation(self):
        CustomField.objects.create(
            name="Источник", field_key="source", entity_type="client", data_type="text"
        )
        response = self.client.post(
            "/api/clients/", {"name": "С полем", "custom_data": {"source": "Сайт"}}, format="json"
        )
        self.assertEqual(response.status_code, 201)
        invalid = self.client.post(
            "/api/clients/", {"name": "С ошибкой", "custom_data": {"unknown": "x"}}, format="json"
        )
        self.assertEqual(invalid.status_code, 400)

    def test_dashboard_stats(self):
        response = self.client.get("/api/dashboard/stats/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("clients", response.data)
        self.assertIn("overdue_tasks", response.data)
        self.assertIn("sales_by_month", response.data)
        self.assertIn("manager_activity", response.data)
        self.assertIn("conversion", response.data)
        self.assertIn("books", response.data)
        self.assertIn("low_stock_books", response.data)
        self.assertIn("top_books", response.data)
        self.assertIn("sales_by_category", response.data)

    def test_activity_log_records_create_update_and_delete(self):
        created = self.client.post("/api/clients/", {"name": "Журнал"}, format="json")
        self.assertEqual(created.status_code, 201)
        client_id = created.data["id"]
        updated = self.client.patch(f"/api/clients/{client_id}/", {"phone": "+79990000000"}, format="json")
        self.assertEqual(updated.status_code, 200)
        task = self.client.post("/api/tasks/", {"title": "Удаляемая задача"}, format="json")
        self.assertEqual(task.status_code, 201)
        deleted = self.client.delete(f"/api/tasks/{task.data['id']}/")
        self.assertEqual(deleted.status_code, 204)

        logs = ActivityLog.objects.filter(user=self.user)
        self.assertEqual(logs.count(), 4)
        self.assertEqual(set(logs.values_list("action", flat=True)), {"create", "update", "delete"})
        self.assertTrue(logs.filter(entity_type="client", entity_id=client_id).exists())
        self.assertTrue(logs.filter(ip_address__isnull=False).exists())

    def test_book_creation_and_low_stock_filter(self):
        category = Category.objects.create(name="Тестовая категория")
        created = self.client.post(
            "/api/books/",
            {
                "title": "Тестовая книга",
                "author": "Тестовый автор",
                "category": category.id,
                "price": "799.90",
                "stock_quantity": 1,
                "low_stock_threshold": 2,
            },
            format="json",
        )
        self.assertEqual(created.status_code, 201)
        self.assertTrue(created.data["is_low_stock"])
        filtered = self.client.get("/api/books/?stock=low")
        self.assertEqual(filtered.status_code, 200)
        self.assertEqual(filtered.data["count"], 1)

    def test_order_can_contain_book_items(self):
        category = Category.objects.create(name="Тестовая категория")
        book = Book.objects.create(title="Книга", author="Автор", category=category, price="500.00", stock_quantity=2)
        client = self.client.post("/api/clients/", {"name": "Покупатель"}, format="json")
        order = self.client.post(
            "/api/deals/",
            {
                "name": "Заказ №1",
                "client": client.data["id"],
                "items": [{"book": book.id, "quantity": 2, "unit_price": "500.00"}],
            },
            format="json",
        )
        self.assertEqual(order.status_code, 201, order.data)
        self.assertEqual(len(order.data["items"]), 1)
        self.assertEqual(OrderItem.objects.get(deal_id=order.data["id"]).quantity, 2)
        book.refresh_from_db()
        self.assertEqual(book.stock_quantity, 0)

        cancelled_status, _ = Status.objects.get_or_create(name="Отменён", entity_type="deal", is_final=True)
        cancelled = self.client.patch(
            f"/api/deals/{order.data['id']}/",
            {"status": cancelled_status.id},
            format="json",
        )
        self.assertEqual(cancelled.status_code, 200)
        book.refresh_from_db()
        self.assertEqual(book.stock_quantity, 2)

    @override_settings(INTEGRATION_API_KEY="test-1c-key")
    def test_1c_integration_requires_key_and_syncs_book(self):
        denied = self.client.get("/api/integration/books/")
        self.assertEqual(denied.status_code, 403)
        response = self.client.post(
            "/api/integration/books/",
            {
                "isbn": "978-5-00000-000-1",
                "title": "Книга из 1С",
                "author": "Автор",
                "category": "Импорт",
                "price": "1200.00",
                "stock_quantity": 7,
            },
            HTTP_X_INTEGRATION_KEY="test-1c-key",
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["book"]["stock_quantity"], 7)

    def test_openapi_schema_is_available(self):
        response = self.client.get("/api/openapi.json")
        self.assertEqual(response.status_code, 200)
        self.assertIn("/integration/orders/", response.json()["paths"])
