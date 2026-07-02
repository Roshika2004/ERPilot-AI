from django.db import models
from django.contrib.auth.models import User


class Claim(models.Model):

    STATUS_CHOICES = (
        ('PENDING', 'Pending'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
    )

    employee = models.ForeignKey(
        User,
        on_delete=models.CASCADE
    )

    title = models.CharField(
        max_length=255
    )

    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    invoice = models.FileField(
        upload_to='invoices/'
    )

    # ==========================
    # AI Fields
    # ==========================

    ai_confidence = models.FloatField(
        default=0
    )

    fraud_score = models.FloatField(
        default=0
    )

    ai_recommendation = models.TextField(
        blank=True
    )

    ai_reasoning = models.TextField(
        blank=True,
        null=True
    )

    # ==========================
    # Claim Status
    # ==========================

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='PENDING'
    )

    # ==========================
    # Manager Override
    # ==========================

    override_status = models.CharField(
        max_length=20,
        choices=(
            ('NONE', 'No Override'),
            ('APPROVED', 'Manager Approved'),
            ('REJECTED', 'Manager Rejected'),
        ),
        default='NONE'
    )

    override_reason = models.TextField(
        blank=True,
        null=True,
        help_text="Manager's reason for overriding AI decision"
    )

    overridden_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='overridden_claims',
        help_text="The manager who overrode the decision"
    )

    overridden_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the decision was overridden"
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    # =====================================
    # Display AI Confidence as Percentage
    # =====================================

    @property
    def get_display_ai_confidence(self):
        """
        ai_confidence is stored as:
            0.0 -> 1.0

        Display as:
            0 -> 100%
        """

        if self.ai_confidence is None:
            return 0

        return round(self.ai_confidence)

    def __str__(self):
        return f"{self.title} - {self.employee.username}"