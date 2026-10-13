from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _


class Committee(models.Model):
    """
    Formal Committee entity for Screening and Empowered Committees.
    Binds an authorized Chair and Members to an institutional assessment framework.
    """
    COMMITTEE_TYPE_CHOICES = (
        ('SCREENING', 'Screening Committee'),
        ('EMPOWERED', 'Empowered Committee'),
    )
    FRAMEWORK_CHOICES = (
        ('COLLEGE_2026', 'Colleges of Haryana Framework (COLLEGE_2026)'),
        ('UNIVERSITY_2026', 'State Universities Framework (UNIVERSITY_2026)'),
        ('ALL', 'Unified Framework (ALL)'),
    )

    name = models.CharField(max_length=200, unique=True, db_index=True)
    description = models.TextField(blank=True, default='')
    committee_type = models.CharField(max_length=50, choices=COMMITTEE_TYPE_CHOICES, default='SCREENING', db_index=True)
    framework = models.CharField(max_length=50, choices=FRAMEWORK_CHOICES, default='COLLEGE_2026', db_index=True)
    chair = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='chaired_committees',
        help_text=_("Authorized Screening or Empowered Committee Chair")
    )
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = _('Committee')
        verbose_name_plural = _('Committees')

    def __str__(self):
        chair_str = self.chair.email if self.chair else "No Chair"
        return f"{self.name} ({self.framework}, Chair: {chair_str}, Active={self.is_active})"


class CommitteeMember(models.Model):
    """
    Individual reviewer membership within a Committee.
    Enforces active scope and prevents duplicate active memberships.
    """
    ROLE_IN_COMMITTEE_CHOICES = (
        ('chair', 'Committee Chair'),
        ('member', 'Committee Member'),
    )

    committee = models.ForeignKey(
        Committee,
        on_delete=models.CASCADE,
        related_name='memberships'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='committee_memberships'
    )
    role_in_committee = models.CharField(
        max_length=20,
        choices=ROLE_IN_COMMITTEE_CHOICES,
        default='member'
    )
    is_active = models.BooleanField(default=True, db_index=True)
    assigned_at = models.DateTimeField(auto_now_add=True, db_index=True)
    removed_at = models.DateTimeField(null=True, blank=True)
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_committee_members'
    )

    class Meta:
        ordering = ['-assigned_at']
        verbose_name = _('Committee Member')
        verbose_name_plural = _('Committee Members')
        constraints = [
            models.UniqueConstraint(
                fields=['committee', 'user'],
                condition=models.Q(is_active=True),
                name='unique_active_committee_member'
            )
        ]

    def __str__(self):
        return f"{self.user.email} in {self.committee.name} ({self.role_in_committee}, Active={self.is_active})"
