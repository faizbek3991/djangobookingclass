from django import forms

from courses.models import Session

from .models import Booking, CertificateSettings, PaymentSettings


class PaymentSettingsForm(forms.ModelForm):
    class Meta:
        model = PaymentSettings
        fields = ["bank_name", "account_holder", "account_number", "qr_image", "instructions"]
        widgets = {
            "bank_name": forms.TextInput(attrs={"class": "form-control"}),
            "account_holder": forms.TextInput(attrs={"class": "form-control"}),
            "account_number": forms.TextInput(attrs={"class": "form-control"}),
            "qr_image": forms.ClearableFileInput(attrs={"class": "form-control"}),
            "instructions": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }


class BookingRescheduleForm(forms.ModelForm):
    class Meta:
        model = Booking
        fields = ["session"]
        widgets = {
            "session": forms.Select(attrs={"class": "form-select"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        instance = kwargs.get("instance")
        if instance and instance.pk:
            self.fields["session"].queryset = Session.objects.filter(
                course=instance.session.course, start_at__gte=instance.session.start_at
            )

    def clean_session(self):
        session = self.cleaned_data["session"]
        if session != self.instance.session and session.is_full:
            raise forms.ValidationError("That session is already full.")
        return session


class CertificateSettingsForm(forms.ModelForm):
    class Meta:
        model = CertificateSettings
        fields = ["title", "intro_text", "completion_text", "signatory_name", "signatory_title",
                  "footer_note", "accent_color", "border_color"]
        widgets = {f: forms.TextInput(attrs={"class": "form-control"}) for f in fields}
        widgets["accent_color"] = forms.TextInput(attrs={"class": "form-control", "type": "color"})
        widgets["border_color"] = forms.TextInput(attrs={"class": "form-control", "type": "color"})


class BookingCertificateForm(forms.ModelForm):
    class Meta:
        model = Booking
        fields = ["cert_name", "cert_course_title", "cert_date"]
        widgets = {
            "cert_name": forms.TextInput(attrs={"class": "form-control"}),
            "cert_course_title": forms.TextInput(attrs={"class": "form-control"}),
            "cert_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
        }
        help_texts = {
            "cert_name": "Leave blank to use the user's full name.",
            "cert_course_title": "Leave blank to use the course title.",
            "cert_date": "Leave blank to use the session start date.",
        }
