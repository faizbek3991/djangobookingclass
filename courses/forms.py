from django import forms

from .models import Course, Session, SiteSEOSettings


class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = [
            "title",
            "description",
            "price",
            "duration_hours",
            "is_active",
            "meta_title",
            "meta_description",
            "og_image",
        ]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
            "price": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "duration_hours": forms.NumberInput(attrs={"class": "form-control"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "meta_title": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Leave blank to use the course title"}
            ),
            "meta_description": forms.Textarea(
                attrs={"class": "form-control", "rows": 2, "placeholder": "Leave blank to use the course description"}
            ),
            "og_image": forms.ClearableFileInput(attrs={"class": "form-control"}),
        }


class SEOSettingsForm(forms.ModelForm):
    class Meta:
        model = SiteSEOSettings
        fields = [
            "site_name",
            "default_meta_title",
            "default_meta_description",
            "default_og_image",
            "google_site_verification",
        ]
        widgets = {
            "site_name": forms.TextInput(attrs={"class": "form-control"}),
            "default_meta_title": forms.TextInput(attrs={"class": "form-control"}),
            "default_meta_description": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
            "default_og_image": forms.ClearableFileInput(attrs={"class": "form-control"}),
            "google_site_verification": forms.TextInput(attrs={"class": "form-control"}),
        }


class SessionForm(forms.ModelForm):
    class Meta:
        model = Session
        fields = ["course", "trainer_name", "start_at", "end_at", "location", "capacity", "meeting_link"]
        widgets = {
            "course": forms.Select(attrs={"class": "form-select"}),
            "trainer_name": forms.TextInput(attrs={"class": "form-control"}),
            "start_at": forms.DateTimeInput(attrs={"class": "form-control", "type": "datetime-local"}, format="%Y-%m-%dT%H:%M"),
            "end_at": forms.DateTimeInput(attrs={"class": "form-control", "type": "datetime-local"}, format="%Y-%m-%dT%H:%M"),
            "location": forms.TextInput(attrs={"class": "form-control"}),
            "capacity": forms.NumberInput(attrs={"class": "form-control"}),
            "meeting_link": forms.URLInput(attrs={"class": "form-control", "placeholder": "https://zoom.us/j/..."}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["start_at"].input_formats = ["%Y-%m-%dT%H:%M"]
        self.fields["end_at"].input_formats = ["%Y-%m-%dT%H:%M"]

    def clean(self):
        cleaned = super().clean()
        start_at = cleaned.get("start_at")
        end_at = cleaned.get("end_at")
        if start_at and end_at and end_at <= start_at:
            raise forms.ValidationError("End time must be after the start time.")
        return cleaned
