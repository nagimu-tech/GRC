from datetime import date, timedelta

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.accounts.models import Company
from apps.catalog.models import Course, CourseSession, CourseSessionPhoto, Position
from apps.people.models import CompanyPerson, CompanyPersonPhoto, Person
from apps.participation.models import Participation


FIRST_NAMES = [
    "Александр", "Алексей", "Андрей", "Анна", "Артём", "Валерия", "Виктория", "Даниил",
    "Дарья", "Дмитрий", "Екатерина", "Елена", "Иван", "Илья", "Кирилл", "Ксения",
    "Мария", "Михаил", "Наталья", "Никита", "Ольга", "Павел", "Полина", "Роман",
    "Светлана", "Сергей", "Софья", "Татьяна", "Юлия", "Ярослав",
]

LAST_NAMES = [
    "Абрамова", "Акимов", "Беляева", "Борисов", "Васильева", "Волков", "Гончарова",
    "Громов", "Денисова", "Егоров", "Зайцева", "Ильин", "Калинина", "Киселёв",
    "Козлова", "Комаров", "Лебедева", "Макаров", "Мельникова", "Миронов",
    "Николаева", "Орлов", "Павлова", "Петров", "Романова", "Семенов", "Соколова",
    "Тарасов", "Федорова", "Чернов",
]

MIDDLE_NAMES = [
    "Александрович", "Алексеевна", "Андреевич", "Викторовна", "Дмитриевич",
    "Игоревна", "Михайлович", "Олеговна", "Павлович", "Сергеевна",
]

POSITION_NAMES = [
    "Куратор потока",
    "Старший ассистент",
    "Ассистент практики",
    "Ассистент группы",
    "Координатор участников",
    "Ментор малой группы",
    "Технический ассистент",
    "Ассистент регистрации",
    "Ассистент упражнений",
    "Ответственный за материалы",
    "Ведущий обратной связи",
    "Помощник тренера",
]


class Command(BaseCommand):
    help = "Наполняет тестовыми данными компанию Ставрополь GRC."

    @transaction.atomic
    def handle(self, *args, **options):
        company, _ = Company.objects.get_or_create(
            name="Ставрополь GRC",
            defaults={"is_active": True},
        )
        course, _ = Course.objects.get_or_create(
            company=company,
            name="Пробуждение личной силы",
            defaults={"description": "Демо-курс для тестовой базы.", "is_active": True},
        )

        positions = []
        for order, name in enumerate(POSITION_NAMES, start=1):
            position, _ = Position.objects.get_or_create(
                name=name,
                defaults={"is_active": True, "order": order},
            )
            positions.append(position)

        people = self._ensure_people(company)
        sessions = self._ensure_sessions(company, course)
        self._ensure_participations(company, sessions, people, positions)
        self._ensure_progression_for_existing_roles(company, course, sessions)
        self._ensure_session_photos(sessions)

        self.stdout.write(self.style.SUCCESS(
            f"Готово: {len(people)} людей, {len(sessions)} потоков курса для {company.name}."
        ))

    def _ensure_people(self, company):
        seeded = list(
            CompanyPerson.objects
            .filter(company=company, notes__contains="seed:stavropol-demo")
            .select_related("person")
            .order_by("pk")
        )

        for index in range(len(seeded), 100):
            first_name = FIRST_NAMES[index % len(FIRST_NAMES)]
            last_name = LAST_NAMES[(index * 7) % len(LAST_NAMES)]
            middle_name = MIDDLE_NAMES[(index * 3) % len(MIDDLE_NAMES)]
            birth_year = 1978 + (index % 24)
            birth_month = 1 + (index % 12)
            birth_day = 1 + (index * 5 % 27)
            phone = f"+7 906 {100 + index:03d} {20 + index % 80:02d} {10 + index % 89:02d}"
            email = f"stavropol.person{index + 1:03d}@example.test"

            person = Person.objects.create(
                last_name=last_name,
                first_name=first_name,
                middle_name=middle_name,
                birth_date=date(birth_year, birth_month, birth_day),
                phone=phone,
                email=email,
            )
            company_person = CompanyPerson.objects.create(
                company=company,
                person=person,
                consent_stored=True,
                consent_contact=True,
                notes=f"Тестовая запись seed:stavropol-demo #{index + 1:03d}",
            )
            seeded.append(company_person)

        for index, company_person in enumerate(seeded[:100]):
            if index % 4 == 0:
                self._ensure_person_photo(company_person, index, 0)
            if index % 17 == 0:
                self._ensure_person_photo(company_person, index, 1)
        return seeded[:100]

    def _ensure_person_photo(self, company_person, person_index, photo_index):
        CompanyPersonPhoto.objects.get_or_create(
            company_person=company_person,
            image_url=f"https://i.pravatar.cc/640?u=grc-stavropol-person-{person_index + 1}-{photo_index + 1}",
            defaults={
                "caption": f"Фото {photo_index + 1}",
                "order": photo_index,
            },
        )

    def _ensure_sessions(self, company, course):
        first_friday = date(2024, 2, 2)
        sessions = []
        for index in range(14):
            start_date = first_friday + timedelta(days=35 * index)
            while start_date.weekday() != 4:
                start_date += timedelta(days=1)
            end_date = start_date + timedelta(days=2)
            session, _ = CourseSession.objects.get_or_create(
                company=company,
                course=course,
                label=f"Поток {index + 1:02d} · {start_date.strftime('%d.%m.%Y')}",
                defaults={
                    "start_date": start_date,
                    "end_date": end_date,
                    "location_format": CourseSession.OFFLINE if index % 3 else CourseSession.HYBRID,
                    "notes": "Тестовый поток, пятница-воскресенье.",
                },
            )
            sessions.append(session)
        return sessions

    def _ensure_participations(self, company, sessions, people, positions):
        studied_before = []
        trainer_pool = []

        for index, session in enumerate(sessions):
            student_start = (index * 7) % len(people)
            students = self._take_rotating(people, student_start, 8)

            assistants_pool = [p for p in studied_before if p not in students]
            assistant_count = min(len(assistants_pool), 12 + (index % 7))
            assistants = self._take_rotating(assistants_pool, index * 5, assistant_count)

            trainer_candidates = [p for p in trainer_pool if p not in students and p not in assistants]
            trainer_count = min(len(trainer_candidates), 2 + (index % 3))
            trainers = self._take_rotating(trainer_candidates, index * 3, trainer_count)

            for company_person in students:
                Participation.objects.get_or_create(
                    company=company,
                    company_person=company_person,
                    session=session,
                    role=Participation.STUDENT,
                )

            for assistant_index, company_person in enumerate(assistants):
                position = positions[assistant_index] if assistant_index < len(positions) else None
                Participation.objects.get_or_create(
                    company=company,
                    company_person=company_person,
                    session=session,
                    role=Participation.ASSISTANT,
                    defaults={"chosen_position": position},
                )

            for company_person in trainers:
                Participation.objects.get_or_create(
                    company=company,
                    company_person=company_person,
                    session=session,
                    role=Participation.TRAINER,
                )

            for company_person in students:
                if company_person not in studied_before:
                    studied_before.append(company_person)
                if index >= 2 and company_person not in trainer_pool and (company_person.pk or 0) % 5 == 0:
                    trainer_pool.append(company_person)

    def _ensure_progression_for_existing_roles(self, company, course, sessions):
        earliest_session = sorted(
            [session for session in sessions if session.start_date],
            key=lambda session: session.start_date,
        )[0]
        non_student_roles = (
            Participation.objects
            .filter(company=company, session__course=course)
            .exclude(role=Participation.STUDENT)
            .select_related("session")
        )
        for participation in non_student_roles:
            has_earlier_student_role = Participation.objects.filter(
                company=company,
                company_person=participation.company_person,
                session__course=course,
                session__start_date__lt=participation.session.start_date,
                role=Participation.STUDENT,
            ).exists()
            if not has_earlier_student_role and earliest_session.start_date < participation.session.start_date:
                Participation.objects.get_or_create(
                    company=company,
                    company_person=participation.company_person,
                    session=earliest_session,
                    role=Participation.STUDENT,
                )

    def _ensure_session_photos(self, sessions):
        for session_index, session in enumerate(sessions):
            for photo_index in range(3):
                CourseSessionPhoto.objects.get_or_create(
                    session=session,
                    image_url=(
                        "https://picsum.photos/seed/"
                        f"grc-stavropol-session-{session_index + 1}-{photo_index + 1}/1200/800"
                    ),
                    defaults={
                        "caption": f"Фото потока {photo_index + 1}",
                        "order": photo_index,
                    },
                )

    def _take_rotating(self, items, start, count):
        if not items or count <= 0:
            return []
        return [items[(start + offset) % len(items)] for offset in range(count)]
