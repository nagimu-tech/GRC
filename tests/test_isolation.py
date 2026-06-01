"""
Тесты изоляции тенантов.
Проверяют, что пользователь компании А не может получить
ни одной записи компании Б — ни через список, ни через прямой URL.
"""
from django.test import TestCase, Client
from django.urls import reverse

from apps.accounts.models import Company, User
from apps.catalog.models import Course, CourseSession
from apps.people.models import Person, CompanyPerson
from apps.participation.models import Participation
from apps.calling.models import Event, CallRecord


def make_company(name):
    return Company.objects.create(name=name, is_active=True)


def make_admin(username, company):
    return User.objects.create_user(
        username=username,
        password="testpass123",
        company=company,
        role=User.COMPANY_ADMIN,
    )


def make_person(last_name, first_name):
    return Person.objects.create(last_name=last_name, first_name=first_name)


class TenantIsolationCourseTest(TestCase):
    def setUp(self):
        self.company_a = make_company("Компания А")
        self.company_b = make_company("Компания Б")
        self.admin_a = make_admin("admin_a", self.company_a)
        self.admin_b = make_admin("admin_b", self.company_b)
        self.course_a = Course.objects.create(name="Курс А", company=self.company_a)
        self.course_b = Course.objects.create(name="Курс Б", company=self.company_b)

    def test_course_list_isolation(self):
        """Пользователь А не видит курсы компании Б в списке."""
        self.client.force_login(self.admin_a)
        response = self.client.get(reverse("catalog:course_list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Курс А")
        self.assertNotContains(response, "Курс Б")

    def test_course_detail_isolation(self):
        """Пользователь А не может открыть курс компании Б по прямому URL."""
        self.client.force_login(self.admin_a)
        response = self.client.get(reverse("catalog:course_detail", args=[self.course_b.pk]))
        self.assertIn(response.status_code, [403, 404])

    def test_course_update_isolation(self):
        """Пользователь А не может редактировать курс компании Б."""
        self.client.force_login(self.admin_a)
        response = self.client.post(
            reverse("catalog:course_update", args=[self.course_b.pk]),
            {"name": "Взломан", "is_active": True},
        )
        self.assertIn(response.status_code, [403, 404])
        self.course_b.refresh_from_db()
        self.assertEqual(self.course_b.name, "Курс Б")  # не изменился


class TenantIsolationPeopleTest(TestCase):
    def setUp(self):
        self.company_a = make_company("Компания А")
        self.company_b = make_company("Компания Б")
        self.admin_a = make_admin("admin_a", self.company_a)
        self.admin_b = make_admin("admin_b", self.company_b)

        person_a = make_person("Иванов", "Иван")
        person_b = make_person("Петров", "Пётр")

        self.cp_a = CompanyPerson.objects.create(company=self.company_a, person=person_a)
        self.cp_b = CompanyPerson.objects.create(company=self.company_b, person=person_b)

    def test_people_list_isolation(self):
        """Пользователь А не видит людей компании Б."""
        self.client.force_login(self.admin_a)
        response = self.client.get(reverse("people:companyperson_list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Иванов")
        self.assertNotContains(response, "Петров")

    def test_person_detail_isolation(self):
        """Пользователь А не может открыть карточку человека из компании Б."""
        self.client.force_login(self.admin_a)
        response = self.client.get(reverse("people:companyperson_detail", args=[self.cp_b.pk]))
        self.assertIn(response.status_code, [403, 404])

    def test_person_update_isolation(self):
        """Пользователь А не может изменить карточку человека из компании Б."""
        self.client.force_login(self.admin_a)
        response = self.client.post(
            reverse("people:companyperson_update", args=[self.cp_b.pk]),
            {"notes": "Взломано", "consent_stored": True, "consent_contact": True, "is_active": True},
        )
        self.assertIn(response.status_code, [403, 404])


class TenantIsolationCallingTest(TestCase):
    def setUp(self):
        self.company_a = make_company("Компания А")
        self.company_b = make_company("Компания Б")
        self.admin_a = make_admin("admin_a", self.company_a)
        self.admin_b = make_admin("admin_b", self.company_b)

        self.event_a = Event.objects.create(title="Встреча А", company=self.company_a, is_active=True)
        self.event_b = Event.objects.create(title="Встреча Б", company=self.company_b, is_active=True)

    def test_event_list_isolation(self):
        """Пользователь А не видит встречи компании Б."""
        self.client.force_login(self.admin_a)
        response = self.client.get(reverse("calling:event_list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Встреча А")
        self.assertNotContains(response, "Встреча Б")

    def test_event_session_isolation(self):
        """Пользователь А не может открыть сессию прозвона компании Б."""
        self.client.force_login(self.admin_a)
        response = self.client.get(reverse("calling:session", args=[self.event_b.pk]))
        self.assertIn(response.status_code, [403, 404])


class SystemAdminAccessTest(TestCase):
    def setUp(self):
        self.company_a = make_company("Компания А")
        self.company_b = make_company("Компания Б")
        self.sysadmin = User.objects.create_superuser(
            username="sysadmin",
            password="testpass123",
            role=User.SYSTEM_ADMIN,
        )
        self.course_a = Course.objects.create(name="Курс А", company=self.company_a)
        self.course_b = Course.objects.create(name="Курс Б", company=self.company_b)

    def test_sysadmin_sees_all_without_company(self):
        """Системный администратор без выбранной компании видит все курсы."""
        self.client.force_login(self.sysadmin)
        response = self.client.get(reverse("catalog:course_list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Курс А")
        self.assertContains(response, "Курс Б")

    def test_sysadmin_can_access_company_list(self):
        """Системный администратор может открыть список компаний."""
        self.client.force_login(self.sysadmin)
        response = self.client.get(reverse("accounts:company_list"))
        self.assertEqual(response.status_code, 200)


class CallerAccessTest(TestCase):
    def setUp(self):
        self.company = make_company("Компания")
        self.caller = User.objects.create_user(
            username="caller",
            password="testpass123",
            company=self.company,
            role=User.CALLER,
        )
        self.event = Event.objects.create(title="Встреча", company=self.company, is_active=True)
        self.event.assigned_callers.add(self.caller)

    def test_caller_can_access_assigned_event(self):
        """Прозвонщик видит назначенные ему встречи."""
        self.client.force_login(self.caller)
        response = self.client.get(reverse("calling:event_list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Встреча")

    def test_caller_cannot_access_company_list(self):
        """Прозвонщик не может открыть список компаний."""
        self.client.force_login(self.caller)
        response = self.client.get(reverse("accounts:company_list"))
        self.assertIn(response.status_code, [403, 404])

    def test_caller_cannot_create_course(self):
        """Прозвонщик не может создать курс."""
        self.client.force_login(self.caller)
        response = self.client.get(reverse("catalog:course_create"))
        self.assertIn(response.status_code, [403, 404])
