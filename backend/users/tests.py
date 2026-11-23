from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase


class UserProfileApiTests(APITestCase):
    def test_registration_creates_regular_user(self):
        response = self.client.post(
            "/api/auth/register/",
            {
                "username": "new_user",
                "email": "NEW@EXAMPLE.COM",
                "first_name": "Новый",
                "password": "StrongPass123!",
                "password_confirm": "StrongPass123!",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        user = get_user_model().objects.get(username="new_user")
        self.assertEqual(user.email, "new@example.com")
        self.assertEqual(user.role, "user")
        self.assertTrue(user.check_password("StrongPass123!"))

    def test_profile_update_and_password_change(self):
        user = get_user_model().objects.create_user(
            username="profile_user", password="OldStrong123!", role="user"
        )
        self.client.force_authenticate(user)
        profile = self.client.patch(
            "/api/auth/me/", {"first_name": "Иван", "phone": "+79990000000"}, format="json"
        )
        self.assertEqual(profile.status_code, 200)
        self.assertEqual(profile.data["first_name"], "Иван")

        password = self.client.post(
            "/api/auth/me/password/",
            {
                "current_password": "OldStrong123!",
                "new_password": "NewStrong123!",
                "new_password_confirm": "NewStrong123!",
            },
            format="json",
        )
        self.assertEqual(password.status_code, 200)
        user.refresh_from_db()
        self.assertTrue(user.check_password("NewStrong123!"))

    def test_unauthenticated_profile_is_forbidden(self):
        response = self.client.get("/api/auth/me/")
        self.assertEqual(response.status_code, 401)

    def test_admin_can_change_role_and_regular_user_cannot(self):
        regular = get_user_model().objects.create_user(
            username="regular", password="StrongPass123!", role="user"
        )
        admin = get_user_model().objects.create_user(
            username="admin", password="StrongPass123!", role="admin", is_staff=True
        )

        self.client.force_authenticate(regular)
        forbidden = self.client.get("/api/auth/users/")
        self.assertEqual(forbidden.status_code, 403)

        self.client.force_authenticate(admin)
        updated = self.client.patch("/api/auth/users/{}/".format(regular.id), {"role": "manager"}, format="json")
        self.assertEqual(updated.status_code, 200)
        regular.refresh_from_db()
        self.assertEqual(regular.role, "manager")

    def test_admin_can_create_and_block_employee(self):
        admin = get_user_model().objects.create_user(
            username="admin_creator", password="StrongPass123!", role="admin", is_staff=True
        )
        self.client.force_authenticate(admin)
        created = self.client.post(
            "/api/auth/users/",
            {
                "username": "new_employee",
                "email": "employee@example.com",
                "first_name": "Новый",
                "role": "manager",
                "password": "EmployeeStrong123!",
                "password_confirm": "EmployeeStrong123!",
            },
            format="json",
        )
        self.assertEqual(created.status_code, 201, created.data)
        employee = get_user_model().objects.get(username="new_employee")
        self.assertTrue(employee.check_password("EmployeeStrong123!"))
        blocked = self.client.patch(
            f"/api/auth/users/{employee.id}/", {"is_active": False}, format="json"
        )
        self.assertEqual(blocked.status_code, 200)
        employee.refresh_from_db()
        self.assertFalse(employee.is_active)

    def test_admin_cannot_block_self_and_supervisor_cannot_create(self):
        admin = get_user_model().objects.create_user(
            username="admin_self", password="StrongPass123!", role="admin", is_staff=True
        )
        self.client.force_authenticate(admin)
        blocked = self.client.patch(
            f"/api/auth/users/{admin.id}/", {"is_active": False}, format="json"
        )
        self.assertEqual(blocked.status_code, 400)

        supervisor = get_user_model().objects.create_user(
            username="supervisor", password="StrongPass123!", role="supervisor"
        )
        self.client.force_authenticate(supervisor)
        forbidden = self.client.post(
            "/api/auth/users/",
            {"username": "not_allowed", "password": "StrongPass123!", "password_confirm": "StrongPass123!"},
            format="json",
        )
        self.assertEqual(forbidden.status_code, 403)
