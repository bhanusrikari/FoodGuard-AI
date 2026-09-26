import uuid

from django.conf import settings
from django.db import models


def _report_image_upload_path(instance, filename: str) -> str:
    """
    Randomized filename so a report's image URL can't be guessed from a
    sequential/original name — the API's own object-level permissions are
    what should gate access, not obscurity, but an unguessable name closes
    the "just guess the next filename" exposure vector.
    """
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    name = f"{uuid.uuid4().hex}.{ext}" if ext else uuid.uuid4().hex
    return f"food_reports/{name}"


class FoodReport(models.Model):
    """
    A customer's report of a food safety concern at a specific restaurant.

    Lifecycle
    ---------
    DRAFT       — created but not yet submitted; customer may edit/delete
    SUBMITTED   — locked for editing by the customer; awaits review
    UNDER_REVIEW — a Reviewer is actively examining the report
    RESOLVED    — the issue has been addressed
    CLOSED      — report closed without resolution or after resolution

    Multilingual
    ------------
    title and description are stored exactly as entered by the customer.
    The customer's preferred_language is available via customer.preferred_language.
    A future TranslationService will produce localised output without
    overwriting these originals.

    Image
    -----
    Optional at creation; REQUIRED before submission (DRAFT → SUBMITTED).
    Validated by FoodReportSubmissionService using Pillow.
    """

    # ------------------------------------------------------------------
    # Status choices
    # ------------------------------------------------------------------

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        SUBMITTED = "SUBMITTED", "Submitted"
        UNDER_REVIEW = "UNDER_REVIEW", "Under Review"
        RESOLVED = "RESOLVED", "Resolved"
        CLOSED = "CLOSED", "Closed"

    # ------------------------------------------------------------------
    # Priority choices
    # ------------------------------------------------------------------

    class Priority(models.TextChoices):
        LOW = "LOW", "Low"
        MEDIUM = "MEDIUM", "Medium"
        HIGH = "HIGH", "High"
        CRITICAL = "CRITICAL", "Critical"

    # ------------------------------------------------------------------
    # Fields
    # ------------------------------------------------------------------

    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="food_reports",
        verbose_name="customer",
    )

    restaurant = models.ForeignKey(
        "restaurants.Restaurant",
        on_delete=models.PROTECT,
        related_name="food_reports",
        verbose_name="restaurant",
    )

    title = models.CharField(max_length=255, verbose_name="title")

    description = models.TextField(verbose_name="description")

    image = models.ImageField(
        upload_to=_report_image_upload_path,
        blank=True,
        null=True,
        verbose_name="image",
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
        db_index=True,
        verbose_name="status",
    )

    priority = models.CharField(
        max_length=10,
        choices=Priority.choices,
        default=Priority.LOW,
        db_index=True,
        verbose_name="priority",
    )

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    # ------------------------------------------------------------------
    # Meta
    # ------------------------------------------------------------------

    class Meta:
        verbose_name = "food report"
        verbose_name_plural = "food reports"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["customer"], name="report_customer_idx"),
            models.Index(fields=["restaurant"], name="report_restaurant_idx"),
            models.Index(fields=["status"], name="report_status_idx"),
            models.Index(fields=["priority"], name="report_priority_idx"),
        ]

    def __str__(self) -> str:
        return f"[{self.status}] {self.title} — {self.restaurant}"

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @property
    def is_editable(self) -> bool:
        """Only DRAFT reports may be edited or deleted by the customer."""
        return self.status == self.Status.DRAFT
