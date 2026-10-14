from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin

class College(models.Model):
    name = models.CharField(max_length=255)
    institute_code = models.CharField(max_length=50, unique=True, null=True, blank=True, db_index=True)
    aishe_code = models.CharField(max_length=50, blank=True, default="", db_index=True)
    department = models.CharField(max_length=150, default="Directorate of Higher Education")
    district = models.CharField(max_length=100, blank=True, default="", db_index=True)
    institute_type = models.CharField(max_length=50, blank=True, default="")
    institute_category = models.CharField(max_length=100, blank=True, default="")
    affiliation_body_1 = models.CharField(max_length=255, blank=True, default="")
    affiliation_body_2 = models.CharField(max_length=255, blank=True, default="")
    source_reference = models.CharField(max_length=100, default="DHE_SCHOLARSHIP_REGISTRY_2026")
    is_verified = models.BooleanField(default=True)

    def __str__(self):
        if self.institute_code:
            return f"{self.name} ({self.institute_code})"
        return self.name

class UserManager(BaseUserManager):
    def create_user(self, email, full_name, role, password=None, college=None, university=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(
            email=email,
            full_name=full_name,
            role=role,
            college=college,
            university=university,
            **extra_fields
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, full_name, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        
        role = extra_fields.pop('role', 'admin')
        return self.create_user(
            email=email,
            full_name=full_name,
            role=role,
            password=password,
            **extra_fields
        )

class User(AbstractBaseUser, PermissionsMixin):
    ROLE_CHOICES = (
        ('head_admin', 'Head Administrator'),
        ('state_admin', 'State Admin (HSHEC State)'),
        ('sub_admin', 'Sub Administrator'),
        ('council_admin', 'Council Admin Overseer'),
        ('admin', 'DHE Admin (Legacy)'),
        ('committee', 'Screening Committee Member'),
        ('committee_chair', 'Screening Committee Chair'),
        ('empowered_committee', 'Empowered Committee Member'),
        ('empowered_committee_chair', 'Empowered Committee Chair'),
        ('principal', 'College Principal'),
        ('nodal_officer', 'University Nodal Officer'),
        ('university_admin', 'University Administrator'),
    )
    email = models.EmailField(unique=True)
    full_name = models.CharField(max_length=255)
    role = models.CharField(max_length=50, choices=ROLE_CHOICES, default='principal')
    college = models.ForeignKey(College, on_delete=models.SET_NULL, null=True, blank=True, related_name='users')
    university = models.ForeignKey('university.University', on_delete=models.SET_NULL, null=True, blank=True, related_name='users')
    phone_number = models.CharField(max_length=20, blank=True, default='')

    # Incremented whenever every outstanding session must end (password reset, deactivation, role change).
    # Access and refresh JWTs carry it as "tv" and are rejected once it no longer matches.
    token_version = models.PositiveIntegerField(default=0)

    # Institution ownership. A self-registered applicant only *requests* an institution; the binding in
    # `college` / `university` (which every assessment permission checks) is made when an administrator
    # approves the request. Accounts created by the Head Admin are bound directly.
    INSTITUTION_STATUS_CHOICES = (
        ('VERIFIED', 'Verified'),
        ('PENDING', 'Pending approval'),
        ('REJECTED', 'Rejected'),
    )
    institution_status = models.CharField(max_length=10, choices=INSTITUTION_STATUS_CHOICES, default='VERIFIED')
    requested_college = models.ForeignKey(College, on_delete=models.SET_NULL, null=True, blank=True, related_name='pending_users')
    requested_university = models.ForeignKey('university.University', on_delete=models.SET_NULL, null=True, blank=True, related_name='pending_users')

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    
    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['full_name']

    @property
    def is_head_admin(self):
        return self.role == 'head_admin' or self.is_superuser

    @property
    def is_state_admin(self):
        return self.role in ('state_admin', 'sub_admin', 'admin')

    @property
    def is_council_admin(self):
        return self.role == 'council_admin'

    @property
    def is_sub_admin(self):
        return self.role in ('sub_admin', 'admin', 'state_admin')

    @property
    def is_any_admin(self):
        return self.role in ('head_admin', 'state_admin', 'sub_admin', 'admin', 'council_admin') or self.is_superuser

    def revoke_sessions(self):
        """Ends every outstanding session: bumps the JWT token version and revokes stored refresh tokens."""
        User.objects.filter(pk=self.pk).update(token_version=models.F('token_version') + 1)
        self.refresh_from_db(fields=['token_version'])
        RefreshToken.objects.filter(user=self, is_revoked=False).update(is_revoked=True)

    def delete(self, *args, **kwargs):
        if self.role == 'head_admin' and self.is_active:
            remaining = User.objects.filter(role='head_admin', is_active=True).exclude(pk=self.pk).count()
            if remaining == 0:
                raise PermissionError("Cannot delete the last active Head Administrator.")
        return super().delete(*args, **kwargs)

    def __str__(self):
        return f"{self.email} ({self.role})"


class RefreshToken(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='refresh_tokens')
    token = models.CharField(max_length=255, unique=True)  # Stores SHA-256 hash of the token
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_revoked = models.BooleanField(default=False)

    def __str__(self):
        return f"RefreshToken({self.user.email}, revoked={self.is_revoked})"


class OTPVerification(models.Model):
    """
    One OTP challenge. The code itself is never stored: only an HMAC bound to the phone number and purpose.
    A successful verification issues a single-use verification token (also stored as a hash) that the
    follow-up operation (e.g. registration) must present.
    """
    PURPOSE_CHOICES = (('REGISTRATION', 'Registration'),)

    phone_number = models.CharField(max_length=20, db_index=True)
    purpose = models.CharField(max_length=20, choices=PURPOSE_CHOICES, default='REGISTRATION')
    otp_hash = models.CharField(max_length=64, default='')
    attempt_count = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_verified = models.BooleanField(default=False)
    verified_at = models.DateTimeField(null=True, blank=True)
    verification_token_hash = models.CharField(max_length=64, blank=True, default='', db_index=True)
    consumed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"OTP({self.phone_number}, verified={self.is_verified})"


class UserAuditLog(models.Model):
    """
    Append-only audit log for tracking privileged administrative actions on user accounts:
    role assignment/revocation, account activation/deactivation, creation, and profile changes.
    """
    ACTION_CHOICES = (
        ('USER_CREATED', 'User Created'),
        ('ROLE_CHANGED', 'Role Changed'),
        ('ACCOUNT_ACTIVATED', 'Account Activated'),
        ('ACCOUNT_DEACTIVATED', 'Account Deactivated'),
        ('PASSWORD_RESET', 'Password Reset'),
        ('PROFILE_UPDATED', 'Profile Updated'),
        ('HEAD_ADMIN_PROVISIONED', 'Head Admin Provisioned'),
        ('COMMITTEE_ASSIGNED', 'Committee Assigned'),
        ('COMMITTEE_REMOVED', 'Committee Removed'),
        ('INVITATION_CREATED', 'Invitation Created'),
        ('INVITATION_RESENT', 'Invitation Resent'),
        ('INVITATION_REVOKED', 'Invitation Revoked'),
        ('PASSWORD_RESET_REQUESTED', 'Password Reset Requested'),
        ('COMMITTEE_CREATED', 'Committee Created'),
        ('COMMITTEE_MODIFIED', 'Committee Modified'),
        ('COMMITTEE_CHAIR_ASSIGNED', 'Committee Chair Assigned'),
        ('COMMITTEE_MEMBER_ADDED', 'Committee Member Added'),
        ('COMMITTEE_MEMBER_REMOVED', 'Committee Member Removed'),
        ('USER_DELETED', 'User Deleted'),
        ('INSTITUTION_ACCESS_REQUESTED', 'Institution Access Requested'),
        ('INSTITUTION_ACCESS_APPROVED', 'Institution Access Approved'),
        ('INSTITUTION_ACCESS_REJECTED', 'Institution Access Rejected'),
        ('PASSWORD_RESET_LINK_SENT', 'Password Reset Link Sent'),
        ('NOTIFICATION_FAILED', 'Notification Delivery Failed'),
    )

    actor = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='actor_user_audit_logs'
    )
    # SET_NULL (not CASCADE) so a user's audit history survives the deletion of the account; the identity
    # snapshot below keeps the entry attributable afterwards.
    target_user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_logs'
    )
    target_user_ref = models.PositiveIntegerField(null=True, blank=True, db_index=True)
    target_email = models.EmailField(blank=True, default='')
    target_role = models.CharField(max_length=50, blank=True, default='')
    action = models.CharField(max_length=50, choices=ACTION_CHOICES, db_index=True)
    details = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-timestamp']
        verbose_name = 'User Audit Log'
        verbose_name_plural = 'User Audit Logs'

    def __str__(self):
        actor_email = self.actor.email if self.actor else "SYSTEM"
        target_email = self.target_user.email if self.target_user else (self.target_email or "UNKNOWN")
        return f"{actor_email} -> {self.action} on {target_email} at {self.timestamp}"

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValueError("UserAuditLog entries are append-only and cannot be modified.")
        if self.target_user_id and not self.target_user_ref:
            self.target_user_ref = self.target_user_id
            self.target_email = self.target_email or getattr(self.target_user, 'email', '')
            self.target_role = self.target_role or getattr(self.target_user, 'role', '')
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError("UserAuditLog entries cannot be deleted.")


class AccountActivationToken(models.Model):
    """
    Cryptographically secure, single-use, expiring activation token.
    Stores only the SHA-256 hash of the token. The raw token is NEVER persisted.
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='activation_tokens'
    )
    token_hash = models.CharField(max_length=64, unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(db_index=True)
    used_at = models.DateTimeField(null=True, blank=True)
    is_used = models.BooleanField(default=False, db_index=True)
    is_revoked = models.BooleanField(default=False, db_index=True)
    created_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='created_activation_tokens'
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Account Activation Token'
        verbose_name_plural = 'Account Activation Tokens'

    @property
    def is_valid(self):
        from django.utils import timezone
        return not self.is_used and not self.is_revoked and timezone.now() < self.expires_at

    def __str__(self):
        return f"ActivationToken({self.user.email}, active={self.is_valid})"



