from django.contrib.auth.mixins import UserPassesTestMixin


class StaffRequiredMixin(UserPassesTestMixin):
    """Restricts a view to staff (admin dashboard) users only."""

    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.is_staff
