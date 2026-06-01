from django import forms
from .models import Position, Course, CourseSession, CourseSessionPhoto


class PositionForm(forms.ModelForm):
    class Meta:
        model = Position
        fields = ["name", "description", "is_active", "order"]
        labels = {
            "name": "Название",
            "description": "Описание",
            "is_active": "Активна",
            "order": "Порядок сортировки",
        }
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
        }


class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = ["name", "description", "is_active"]
        labels = {
            "name": "Название курса",
            "description": "Описание",
            "is_active": "Активен",
        }
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
        }


class CourseSessionForm(forms.ModelForm):
    class Meta:
        model = CourseSession
        fields = ["course", "label", "start_date", "end_date", "location_format", "notes"]
        labels = {
            "course": "Курс",
            "label": "Название потока",
            "start_date": "Дата начала",
            "end_date": "Дата окончания",
            "location_format": "Формат",
            "notes": "Заметки",
        }
        widgets = {
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "end_date": forms.DateInput(attrs={"type": "date"}),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, company=None, **kwargs):
        super().__init__(*args, **kwargs)
        if company:
            self.fields["course"].queryset = Course.objects.filter(
                company=company, is_active=True
            )


class CourseSessionPhotoForm(forms.ModelForm):
    class Meta:
        model = CourseSessionPhoto
        fields = ["image_url", "caption", "order"]
        labels = {
            "image_url": "Ссылка на фото",
            "caption": "Подпись",
            "order": "Порядок",
        }
        widgets = {
            "image_url": forms.URLInput(attrs={
                "placeholder": "https://cdn.example.com/session-photo.jpg",
            }),
        }
