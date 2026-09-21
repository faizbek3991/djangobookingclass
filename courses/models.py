from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify


class Course(models.Model):
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    description = models.TextField()
    price = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    duration_hours = models.PositiveIntegerField(help_text="Total training duration in hours")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    meta_title = models.CharField(
        max_length=70,
        blank=True,
        help_text="SEO page title (falls back to the course title if left blank). Aim for under 60 characters.",
    )
    meta_description = models.CharField(
        max_length=300,
        blank=True,
        help_text="SEO meta description shown in search results (falls back to the course description). Aim for under 160 characters.",
    )
    og_image = models.ImageField(
        upload_to="course_og/",
        blank=True,
        null=True,
        help_text="Image shown when this course is shared on social media (recommended 1200x630).",
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("courses:course_detail", kwargs={"slug": self.slug})

    @property
    def upcoming_sessions(self):
        return self.sessions.filter(start_at__gte=timezone.now()).order_by("start_at")

    @property
    def seo_title(self):
        return self.meta_title or self.title

    @property
    def seo_description(self):
        if self.meta_description:
            return self.meta_description
        from django.utils.text import Truncator

        return Truncator(self.description).words(25)


class Session(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="sessions")
    trainer_name = models.CharField(max_length=150)
    start_at = models.DateTimeField()
    end_at = models.DateTimeField()
    location = models.CharField(
        max_length=200,
        default="Online (link sent after booking)",
        help_text="Physical venue or online meeting info",
    )
    capacity = models.PositiveIntegerField(default=20)
    meeting_link = models.URLField(
        blank=True,
        help_text="Zoom/Meet/Teams link — sent to attendees once their payment is approved",
    )

    class Meta:
        ordering = ["start_at"]

    def __str__(self):
        return f"{self.course.title} — {self.start_at:%d %b %Y %H:%M}"

    @property
    def seats_taken(self):
        return self.bookings.filter(
            status__in=["pending_payment", "awaiting_verification", "confirmed"]
        ).count()

    @property
    def seats_left(self):
        return max(self.capacity - self.seats_taken, 0)

    @property
    def is_full(self):
        return self.seats_left <= 0

    @property
    def is_past(self):
        return self.start_at < timezone.now()


class SiteSEOSettings(models.Model):
    """Singleton: site-wide SEO defaults, editable by admin. Per-course fields override these."""

    site_name = models.CharField(max_length=100, default="TrainBook")
    default_meta_title = models.CharField(max_length=70, default="TrainBook — Online Training Bookings")
    default_meta_description = models.CharField(
        max_length=300,
        default="Browse and book seats in live online training sessions.",
    )
    default_og_image = models.ImageField(upload_to="site_og/", blank=True, null=True)
    google_site_verification = models.CharField(
        max_length=100,
        blank=True,
        help_text="Content value for the google-site-verification meta tag (from Google Search Console), if any.",
    )

    class Meta:
        verbose_name = "SEO settings"
        verbose_name_plural = "SEO settings"

    def __str__(self):
        return "SEO settings"

    @classmethod
    def get_solo(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj
