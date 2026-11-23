import os
from datetime import date, timedelta
from decimal import Decimal

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django

django.setup()

from django.db import transaction

from crm_core.models import (
    Book,
    Category,
    Client,
    Deal,
    EntityType,
    OrderItem,
    Status,
    Task,
)
from users.models import User


def get_status(name, entity_type, color, is_final=False):
    status, created = Status.objects.get_or_create(
        name=name,
        entity_type=entity_type,
        defaults={
            "color": color,
            "is_final": is_final,
            "is_active": True,
        },
    )
    if created:
        return status
    return status


@transaction.atomic
def seed():
    active_user = User.objects.filter(is_active=True).order_by("id").first()
    if active_user is None:
        active_user = User.objects.create_user(
            username="demo.manager",
            email="demo.manager@bookstore.local",
            password="Demo12345!",
            first_name="Демо",
            last_name="Менеджер",
            role="manager",
        )

    client_status_new = get_status(
        "Новый", EntityType.CLIENT, "#2563eb"
    )
    deal_status_new = get_status(
        "Новая", EntityType.DEAL, "#2563eb"
    )
    deal_status_processing = get_status(
        "В обработке", EntityType.DEAL, "#d97706"
    )
    deal_status_ready = get_status(
        "Готова к выдаче", EntityType.DEAL, "#2f855a"
    )
    deal_status_done = get_status(
        "Завершена", EntityType.DEAL, "#64748b", is_final=True
    )
    deal_status_cancelled = get_status(
        "Отменён", EntityType.DEAL, "#b42318", is_final=True
    )
    task_status_new = get_status(
        "Новая", EntityType.TASK, "#2563eb"
    )
    task_status_work = get_status(
        "В работе", EntityType.TASK, "#d97706"
    )

    categories = {}
    for name in (
        "Классика",
        "Фантастика",
        "Бизнес",
        "Психология",
        "Детская литература",
        "Программирование",
    ):
        categories[name], _ = Category.objects.get_or_create(
            name=name,
            defaults={
                "description": f"Демонстрационная категория: {name}",
                "is_active": True,
            },
        )

    book_specs = [
        ("9785171187947", "Мастер и Маргарита", "Михаил Булгаков", "Классика", "799.00", 12, 3),
        ("9780099511892", "Три товарища", "Эрих Мария Ремарк", "Классика", "690.00", 4, 3),
        ("9780553573404", "Игра престолов", "Джордж Мартин", "Фантастика", "990.00", 7, 2),
        ("9781593275990", "Python. К вершинам мастерства", "Лучано Рамальо", "Программирование", "1850.00", 5, 2),
        ("9785961473258", "Атомные привычки", "Джеймс Клир", "Психология", "890.00", 3, 3),
        ("9785001173214", "Думай медленно... решай быстро", "Даниэль Канеман", "Психология", "1190.00", 0, 2),
        ("9785389171834", "Маленький принц", "Антуан де Сент-Экзюпери", "Детская литература", "540.00", 9, 2),
        ("9785961434563", "Путь к финансовой свободе", "Бодо Шефер", "Бизнес", "980.00", 2, 3),
        ("9785041228122", "451 градус по Фаренгейту", "Рэй Брэдбери", "Фантастика", "720.00", 6, 2),
        ("9785041682214", "Эссенциализм", "Грег Маккеон", "Бизнес", "850.00", 1, 2),
    ]

    books = {}
    for isbn, title, author, category, price, stock, threshold in book_specs:
        book, _ = Book.objects.get_or_create(
            isbn=isbn,
            defaults={
                "title": title,
                "author": author,
                "category": categories[category],
                "publisher": "BookStore Press",
                "publication_year": 2024,
                "description": f"Демонстрационная карточка книги «{title}».",
                "price": Decimal(price),
                "stock_quantity": stock,
                "low_stock_threshold": threshold,
                "is_active": True,
            },
        )
        books[isbn] = book

    client_specs = [
        ("Анна Петрова", "anna.petrova@example.com", "+7 900 111-22-33"),
        ("Иван Соколов", "ivan.sokolov@example.com", "+7 900 222-33-44"),
        ("Мария Орлова", "maria.orlova@example.com", "+7 900 333-44-55"),
        ("Алексей Волков", "alexey.volkov@example.com", "+7 900 444-55-66"),
        ("Елена Смирнова", "elena.smirnova@example.com", "+7 900 555-66-77"),
    ]

    clients = {}
    for name, email, phone in client_specs:
        client, _ = Client.objects.get_or_create(
            email=email,
            defaults={
                "name": name,
                "phone": phone,
                "description": "Демонстрационная карточка клиента.",
                "responsible": active_user,
                "status": client_status_new,
            },
        )
        clients[email] = client

    order_specs = [
        ("Заказ #1042", "anna.petrova@example.com", deal_status_new, [("9785171187947", 1)]),
        ("Заказ #1041", "ivan.sokolov@example.com", deal_status_processing, [("9785961473258", 1), ("9780099511892", 1)]),
        ("Заказ #1040", "maria.orlova@example.com", deal_status_ready, [("9785389171834", 2)]),
        ("Заказ #1039", "alexey.volkov@example.com", deal_status_done, [("9780553573404", 1), ("9785041228122", 1)]),
        ("Заказ #1038", "elena.smirnova@example.com", deal_status_cancelled, [("9785001173214", 1)]),
    ]

    created_orders = 0
    for name, email, status, items in order_specs:
        order, created = Deal.objects.get_or_create(
            name=name,
            defaults={
                "client": clients[email],
                "responsible": active_user,
                "status": status,
                "description": "Демонстрационный заказ для проверки CRM.",
                "planned_end_date": date.today() + timedelta(days=3),
                "payment_method": "card",
                "fulfillment_method": "pickup",
                "customer_comment": "Позвонить перед выдачей заказа.",
            },
        )
        if not created:
            continue

        total = Decimal("0")
        is_cancelled = status == deal_status_cancelled
        for isbn, quantity in items:
            book = books[isbn]
            unit_price = book.price
            OrderItem.objects.create(
                deal=order,
                book=book,
                quantity=quantity,
                unit_price=unit_price,
                inventory_applied=not is_cancelled,
            )
            if not is_cancelled:
                book.stock_quantity = max(
                    0,
                    book.stock_quantity - quantity,
                )
                book.save(update_fields=["stock_quantity", "updated_at"])
            total += unit_price * quantity

        order.amount = total
        order.save(update_fields=["amount", "updated_at"])
        created_orders += 1

    task_specs = [
        ("Подтвердить заказ Анны Петровой", clients["anna.petrova@example.com"], None, task_status_new, "high", 1),
        ("Подготовить книги к выдаче", clients["maria.orlova@example.com"], "Заказ #1040", task_status_work, "medium", 2),
        ("Связаться с новым клиентом", clients["alexey.volkov@example.com"], None, task_status_new, "low", 4),
        ("Проверить книги с низким остатком", None, None, task_status_new, "high", 1),
    ]

    for title, client, order_name, status, priority, days in task_specs:
        deal = Deal.objects.filter(name=order_name).first() if order_name else None
        Task.objects.get_or_create(
            title=title,
            defaults={
                "description": "Демонстрационная задача для проверки CRM.",
                "assignee": active_user,
                "client": client,
                "deal": deal,
                "status": status,
                "priority": priority,
                "due_date": date.today() + timedelta(days=days),
            },
        )

    print(
        "Demo data ready: "
        f"books={Book.objects.count()}, "
        f"clients={Client.objects.count()}, "
        f"orders={Deal.objects.count()}, "
        f"order_items={OrderItem.objects.count()}, "
        f"tasks={Task.objects.count()}, "
        f"new_orders={created_orders}"
    )


if __name__ == "__main__":
    seed()
