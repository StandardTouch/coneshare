from django.db import models
from django.db.models.functions import Lower

from core.models import BaseModel, Organization, User
from permissions_rbac.catalogue import (
    ALL_ROLE_GRANT_PERMISSIONS,
    ALL_SITE_PERMISSIONS,
    SCOPE_CHOICES,
    SITE_ROLE_ADMIN,
    SITE_ROLE_MEMBER,
)


class DataroomRole(BaseModel):
    """Configurable dataroom role (system defaults or org-specific custom roles)."""

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='dataroom_roles',
    )
    slug = models.SlugField(max_length=32)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, default='')
    is_system = models.BooleanField(
        default=False,
        help_text='System roles can be edited but not deleted or renamed (slug locked).',
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['organization', 'slug'],
                name='permissions_rbac_dataroomrole_org_slug_unique',
            ),
            models.UniqueConstraint(
                Lower('name'),
                'organization',
                name='permissions_rbac_dataroomrole_org_name_ci_unique',
            ),
        ]
        ordering = ['name']

    def __str__(self):
        return f'{self.name} ({self.organization_id})'


class DataroomRolePermission(BaseModel):
    role = models.ForeignKey(
        DataroomRole,
        on_delete=models.CASCADE,
        related_name='permission_grants',
    )
    permission = models.CharField(max_length=64, choices=[(p, p) for p in ALL_ROLE_GRANT_PERMISSIONS])
    scope = models.CharField(
        max_length=8,
        choices=[(s, s) for s in SCOPE_CHOICES],
        blank=True,
        default='',
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['role', 'permission'],
                name='permissions_rbac_role_perm_unique',
            ),
        ]

    def __str__(self):
        if self.scope:
            return f'{self.role.slug}:{self.permission} ({self.scope})'
        return f'{self.role.slug}:{self.permission}'


class SiteRolePermission(BaseModel):
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='site_role_permissions',
    )
    site_role = models.CharField(
        max_length=16,
        choices=((SITE_ROLE_ADMIN, 'Admin'), (SITE_ROLE_MEMBER, 'Member')),
    )
    permission = models.CharField(max_length=64, choices=[(p, p) for p in ALL_SITE_PERMISSIONS])

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['organization', 'site_role', 'permission'],
                name='permissions_rbac_site_role_perm_unique',
            ),
        ]


class DataroomFolderRoleRule(BaseModel):
    RULE_HIDDEN = 'hidden'
    RULE_VIEW_ONLY = 'view_only'
    RULE_INHERIT = 'inherit'

    RULE_CHOICES = (
        (RULE_HIDDEN, 'Hidden'),
        (RULE_VIEW_ONLY, 'View only'),
        (RULE_INHERIT, 'Inherit'),
    )

    dataroom_folder = models.ForeignKey(
        'datarooms.DataroomFolder',
        on_delete=models.CASCADE,
        related_name='role_access_rules',
    )
    dataroom_role = models.ForeignKey(
        DataroomRole,
        on_delete=models.CASCADE,
        related_name='folder_rules',
    )
    rule = models.CharField(max_length=16, choices=RULE_CHOICES, default=RULE_INHERIT)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['dataroom_folder', 'dataroom_role'],
                name='permissions_rbac_folder_role_rule_unique',
            ),
        ]

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        from permissions_rbac.services import invalidate_folder_rule_cache

        invalidate_folder_rule_cache(self.dataroom_role)

    def delete(self, *args, **kwargs):
        role = self.dataroom_role
        super().delete(*args, **kwargs)
        from permissions_rbac.services import invalidate_folder_rule_cache

        invalidate_folder_rule_cache(role)


class PermissionAuditLog(BaseModel):
    TARGET_ROLE = 'dataroom_role'
    TARGET_SITE = 'site_role'
    TARGET_FOLDER_RULE = 'folder_rule'

    TARGET_CHOICES = (
        (TARGET_ROLE, 'Dataroom role'),
        (TARGET_SITE, 'Site role'),
        (TARGET_FOLDER_RULE, 'Folder rule'),
    )

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='permission_audit_logs',
    )
    actor = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='permission_audit_actions',
    )
    target_type = models.CharField(max_length=32, choices=TARGET_CHOICES)
    target_id = models.CharField(max_length=26, blank=True, default='')
    summary = models.CharField(max_length=512)
    details = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['organization', '-created_at']),
        ]
