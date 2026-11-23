from django.db import migrations


def seed_categories(apps, schema_editor):
    Category = apps.get_model("crm_core", "Category")
    for name in (
        "Художественная литература",
        "Детские книги",
        "Учебная литература",
        "Бизнес и экономика",
        "Психология",
        "Фантастика",
    ):
        Category.objects.get_or_create(name=name)


def remove_categories(apps, schema_editor):
    Category = apps.get_model("crm_core", "Category")
    Category.objects.filter(name__in=(
        "Художественная литература",
        "Детские книги",
        "Учебная литература",
        "Бизнес и экономика",
        "Психология",
        "Фантастика",
    )).delete()


class Migration(migrations.Migration):
    dependencies = [("crm_core", "0005_alter_activitylog_entity_type_and_more")]
    operations = [migrations.RunPython(seed_categories, remove_categories)]
