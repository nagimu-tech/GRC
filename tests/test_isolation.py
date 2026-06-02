"""
Тесты изоляции тенантов.
Проверяют, что пользователь компании А не может получить
ни одной записи компании Б — ни через список, ни через прямой URL.
"""
from django.test import TestCase, Client
from django.urls import reverse
from datetime import date

from apps.accounts.models import Company, User
from apps.catalog.models import Course, CourseSession, CourseSessionPhoto
from apps.people.models import Person, CompanyPerson, CompanyPersonPhoto
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

    def test_company_admin_can_clear_person_company(self):
        """Карточку человека можно оставить без компании из пользовательского интерфейса."""
        self.client.force_login(self.admin_a)
        response = self.client.post(
            reverse("people:companyperson_update", args=[self.cp_a.pk]),
            {
                "company": "",
                "notes": "Без компании",
                "consent_stored": "on",
                "consent_contact": "on",
                "is_active": "on",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.cp_a.refresh_from_db()
        self.assertIsNone(self.cp_a.company)

    def test_person_photo_limit_is_five(self):
        """В карточку человека нельзя добавить больше пяти внешних фото-ссылок."""
        self.client.force_login(self.admin_a)
        for index in range(5):
            CompanyPersonPhoto.objects.create(
                company_person=self.cp_a,
                image_url=f"https://example.com/person-{index}.jpg",
            )
        response = self.client.post(
            reverse("people:companyperson_photo_add", args=[self.cp_a.pk]),
            {"image_url": "https://example.com/extra.jpg", "caption": "extra", "order": "9"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.cp_a.photos.count(), 5)


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

    def test_event_title_links_to_calling_session(self):
        """В списке прозвонов заголовок ведёт в начало прозвона."""
        self.client.force_login(self.admin_a)
        response = self.client.get(reverse("calling:event_list"))
        self.assertContains(response, reverse("calling:session", args=[self.event_a.pk]))

    def test_claim_record_without_htmx_redirects_and_claims(self):
        """Кнопка захвата работает как обычная форма, даже если HTMX не загрузился."""
        person = CompanyPerson.objects.create(
            company=self.company_a,
            person=make_person("Звонков", "Павел"),
        )
        record = CallRecord.objects.create(
            company=self.company_a,
            event=self.event_a,
            company_person=person,
        )
        self.client.force_login(self.admin_a)

        response = self.client.post(reverse("calling:claim_record", args=[record.pk]))

        self.assertRedirects(response, reverse("calling:session", args=[self.event_a.pk]))
        record.refresh_from_db()
        self.assertEqual(record.claimed_by, self.admin_a)


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
        self.person = make_person("Иванов", "Ассистент")
        self.company_person = CompanyPerson.objects.create(
            company=self.company,
            person=self.person,
        )
        self.caller = User.objects.create_user(
            username="caller",
            password="testpass123",
            company=self.company,
            person=self.person,
            role=User.CALLER,
        )
        self.event = Event.objects.create(title="Встреча", company=self.company, is_active=True)
        self.event.assigned_callers.add(self.company_person)

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


class CallPoolFillTest(TestCase):
    def setUp(self):
        self.company = make_company("Компания")
        self.admin = make_admin("admin", self.company)
        self.course = Course.objects.create(name="Курс", company=self.company)
        self.other_course = Course.objects.create(name="Другой курс", company=self.company)
        self.old_session = CourseSession.objects.create(
            company=self.company,
            course=self.course,
            label="Старый поток",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 2, 1),
        )
        self.current_session = CourseSession.objects.create(
            company=self.company,
            course=self.course,
            label="Текущий поток",
            start_date=date(2026, 5, 1),
            end_date=None,
        )
        self.other_session = CourseSession.objects.create(
            company=self.company,
            course=self.other_course,
            label="Чужой поток",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 2, 1),
        )
        self.alumni = CompanyPerson.objects.create(
            company=self.company,
            person=make_person("Алумни", "Анна"),
        )
        self.current_student = CompanyPerson.objects.create(
            company=self.company,
            person=make_person("Текущий", "Студент"),
        )
        self.other_alumni = CompanyPerson.objects.create(
            company=self.company,
            person=make_person("Другой", "Курс"),
        )
        Participation.objects.create(
            company=self.company,
            company_person=self.alumni,
            session=self.old_session,
            role=Participation.STUDENT,
        )
        Participation.objects.create(
            company=self.company,
            company_person=self.current_student,
            session=self.old_session,
            role=Participation.STUDENT,
        )
        Participation.objects.create(
            company=self.company,
            company_person=self.current_student,
            session=self.current_session,
            role=Participation.ASSISTANT,
        )
        Participation.objects.create(
            company=self.company,
            company_person=self.other_alumni,
            session=self.other_session,
            role=Participation.STUDENT,
        )
        self.event = Event.objects.create(
            title="Встреча выпускников",
            company=self.company,
            course=self.course,
            date=date(2026, 6, 1),
            is_active=True,
        )

    def test_fill_adds_only_previous_students_of_event_course(self):
        """Заполнение прозвона берёт выпускников нужного курса и исключает текущую команду курса."""
        self.client.force_login(self.admin)
        response = self.client.post(reverse("calling:init_records", args=[self.event.pk]))
        self.assertEqual(response.status_code, 302)
        people_ids = set(
            CallRecord.objects.filter(event=self.event).values_list("company_person_id", flat=True)
        )
        self.assertEqual(people_ids, {self.alumni.pk})


class CourseSessionPhotoLimitTest(TestCase):
    def setUp(self):
        self.company = make_company("Компания")
        self.admin = make_admin("admin", self.company)
        self.course = Course.objects.create(name="Курс", company=self.company)
        self.session = CourseSession.objects.create(
            company=self.company,
            course=self.course,
            label="Поток",
            start_date=date(2026, 5, 1),
            end_date=date(2026, 5, 3),
        )

    def test_session_photo_limit_is_thirty(self):
        """В поток курса нельзя добавить больше тридцати внешних фото-ссылок."""
        self.client.force_login(self.admin)
        for index in range(30):
            CourseSessionPhoto.objects.create(
                session=self.session,
                image_url=f"https://example.com/session-{index}.jpg",
            )
        response = self.client.post(
            reverse("catalog:session_photo_add", args=[self.session.pk]),
            {"image_url": "https://example.com/extra.jpg", "caption": "extra", "order": "31"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.session.photos.count(), 30)
