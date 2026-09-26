"""
FoodGuard AI — Food Report service layer.

Responsibilities
----------------
- Image validation (extension, MIME type, size, readability via Pillow)
- Submission state machine (DRAFT → SUBMITTED)

No AI logic.  No complaint logic.  No translation logic.
"""

import io
import os

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from PIL import Image, UnidentifiedImageError

from food_reports.models import FoodReport

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MAX_IMAGE_BYTES = 5 * 1024 * 1024  # 5 MB

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png"}

ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/jpg", "image/png"}


# ---------------------------------------------------------------------------
# Image validation
# ---------------------------------------------------------------------------

class ImageValidationError(ValidationError):
    """Raised when an uploaded image fails any validation check."""


def validate_report_image(image_file) -> None:
    """
    Validate an uploaded image file.

    Checks (in order):
    1. File extension is .jpg / .jpeg / .png
    2. Content-type header is an allowed image MIME type (when available)
    3. File size ≤ 5 MB
    4. File is readable as a real image by Pillow

    Parameters
    ----------
    image_file : InMemoryUploadedFile | TemporaryUploadedFile
        The uploaded file object from request.FILES.

    Raises
    ------
    ImageValidationError
        With a human-readable message describing the problem.
    """
    if image_file is None:
        return  # nothing to validate; presence checks happen elsewhere

    # 1. Extension check
    name = getattr(image_file, "name", "") or ""
    ext = os.path.splitext(name.lower())[1]
    if ext not in ALLOWED_EXTENSIONS:
        raise ImageValidationError(
            _(
                "Unsupported file type '%(ext)s'. "
                "Allowed types: JPEG, JPG, PNG."
            )
            % {"ext": ext or "(none)"}
        )

    # 2. Content-type check (header provided by browser — not definitive
    #    but adds a quick guard before reading the full file)
    content_type = getattr(image_file, "content_type", None)
    if content_type and content_type.lower() not in ALLOWED_CONTENT_TYPES:
        raise ImageValidationError(
            _(
                "Unsupported content type '%(ct)s'. "
                "Allowed: image/jpeg, image/png."
            )
            % {"ct": content_type}
        )

    # 3. Size check
    size = getattr(image_file, "size", None)
    if size is None:
        image_file.seek(0, 2)      # seek to end
        size = image_file.tell()
        image_file.seek(0)
    if size > MAX_IMAGE_BYTES:
        mb = size / (1024 * 1024)
        raise ImageValidationError(
            _("Image file size %(mb).2f MB exceeds the 5 MB limit.") % {"mb": mb}
        )

    # 4. Pillow readability check — catches corrupted or spoofed files
    try:
        image_file.seek(0)
        raw = image_file.read()
        image_file.seek(0)          # reset so Django can save it
        img = Image.open(io.BytesIO(raw))
        img.verify()                # raises if file is corrupt
    except UnidentifiedImageError:
        raise ImageValidationError(
            _("The uploaded file could not be identified as a valid image.")
        )
    except Exception:
        raise ImageValidationError(
            _("The uploaded image file appears to be corrupted or invalid.")
        )


# ---------------------------------------------------------------------------
# Submission service
# ---------------------------------------------------------------------------

class SubmissionValidationError(ValidationError):
    """Raised when a report cannot be submitted."""


class FoodReportSubmissionService:
    """
    Encapsulates the DRAFT → SUBMITTED state transition.

    Usage
    -----
    service = FoodReportSubmissionService(report, requesting_user)
    service.submit()   # raises SubmissionValidationError on any violation
    """

    def __init__(self, report: FoodReport, user) -> None:
        self.report = report
        self.user = user

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def submit(self) -> FoodReport:
        """
        Validate and transition the report from DRAFT to SUBMITTED.

        Returns the updated FoodReport instance.
        Raises SubmissionValidationError if any check fails.
        """
        self._check_ownership()
        self._check_current_status()
        self._check_required_fields()
        self._check_image_present()

        self.report.status = FoodReport.Status.SUBMITTED
        self.report.save(update_fields=["status", "updated_at"])

        from notifications.models import Notification
        from notifications.services import NotificationService
        NotificationService().notify_reviewers_and_admins(
            event_type=Notification.EventType.REPORT_SUBMITTED,
            message=f"New food safety report submitted: \"{self.report.title}\".",
            related_report=self.report,
        )

        return self.report

    # ------------------------------------------------------------------
    # Private checks
    # ------------------------------------------------------------------

    def _check_ownership(self) -> None:
        if self.report.customer_id != self.user.pk:
            raise SubmissionValidationError(
                _("You can only submit your own reports.")
            )

    def _check_current_status(self) -> None:
        if self.report.status != FoodReport.Status.DRAFT:
            raise SubmissionValidationError(
                _(
                    "Only DRAFT reports can be submitted. "
                    "This report is currently '%(status)s'."
                )
                % {"status": self.report.get_status_display()}
            )

    def _check_required_fields(self) -> None:
        errors = []
        if not self.report.title or not self.report.title.strip():
            errors.append(_("Title is required before submission."))
        if not self.report.description or not self.report.description.strip():
            errors.append(_("Description is required before submission."))
        if self.report.restaurant_id is None:
            errors.append(_("A restaurant must be linked before submission."))
        if errors:
            raise SubmissionValidationError(list(errors))

    def _check_image_present(self) -> None:
        if not self.report.image:
            raise SubmissionValidationError(
                _("An image is required before a report can be submitted.")
            )
