from django import forms

from courses.models import Session

from .models import Booking, PaymentSettings


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
