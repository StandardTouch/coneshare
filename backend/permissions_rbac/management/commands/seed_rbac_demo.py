"""Seed demo users for RBAC unified UI screenshots (local dev only)."""
import json
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from core.models import Organization
from permissions_rbac.models import DataroomRole, DataroomRolePermission
from permissions_rbac.catalogue import PERM_CREATE_DATAROOM, ROLE_SLUG_CONTRIBUTOR, ROLE_SLUG_VIEWER
from permissions_rbac.seed import ensure_default_roles_for_organization

User = get_user_model()

DEMO_PASSWORD = 'password123'

USERS = (
    ('admin@rbac.demo', 'admin', 'RBAC Demo Admin', None),
    ('viewer@rbac.demo', 'member', 'Viewer User', ROLE_SLUG_VIEWER),
    ('contributor@rbac.demo', 'member', 'Contributor User', ROLE_SLUG_CONTRIBUTOR),
    ('custom@rbac.demo', 'member', 'Custom Role User', None),
)

CUSTOM_ROLE_NAME = 'Deal Analyst'
CUSTOM_ROLE_SLUG = 'deal-analyst'


class Command(BaseCommand):
    help = 'Create admin + viewer/contributor/custom demo users for RBAC Playwright captures.'

    def handle(self, *args, **options):
        org = Organization.objects.order_by('created_at').first()
        if not org:
            org = Organization.objects.create(name='Default Organization')
        roles = ensure_default_roles_for_organization(org)

        custom_role, _ = DataroomRole.objects.get_or_create(
            organization=org,
            slug=CUSTOM_ROLE_SLUG,
            defaults={
                'name': CUSTOM_ROLE_NAME,
                'description': 'Custom role for demo screenshots',
                'is_system': False,
            },
        )
        if not custom_role.permission_grants.filter(permission=PERM_CREATE_DATAROOM).exists():
            DataroomRolePermission.objects.get_or_create(
                role=custom_role,
                permission=PERM_CREATE_DATAROOM,
                defaults={'scope': ''},
            )

        slug_to_role = {r.slug: r for r in DataroomRole.objects.filter(organization=org)}

        for email, site_role, name, org_slug in USERS:
            org_role = None
            if email == 'custom@rbac.demo':
                org_role = custom_role
            elif org_slug:
                org_role = slug_to_role.get(org_slug)

            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    'username': email,
                    'name': name,
                    'role': site_role,
                    'organization': org,
                    'organization_role': org_role if site_role == 'member' else None,
                    'is_active': True,
                },
            )
            if created:
                user.set_password(DEMO_PASSWORD)
                user.save()
                self.stdout.write(self.style.SUCCESS(f'Created {email}'))
            else:
                user.name = name
                user.role = site_role
                user.organization = org
                user.organization_role = org_role if site_role == 'member' else None
                user.is_active = True
                user.set_password(DEMO_PASSWORD)
                user.save()
                self.stdout.write(f'Updated {email}')

        from datarooms.models import Dataroom, DataroomCollaborator, DataroomDocument
        from documents.models import Document, DocumentVersion

        admin = User.objects.get(email='admin@rbac.demo')
        viewer = User.objects.get(email='viewer@rbac.demo')
        contributor = User.objects.get(email='contributor@rbac.demo')
        custom = User.objects.get(email='custom@rbac.demo')

        dataroom, _ = Dataroom.objects.get_or_create(
            organization=org,
            name='RBAC Demo Room',
            defaults={'created_by': admin, 'storage_version': 2, 'storage_quota_mb': 10240},
        )
        if dataroom.storage_version < 2:
            dataroom.storage_version = 2
            dataroom.save(update_fields=['storage_version'])

        def ensure_collab(user):
            role = user.organization_role or slug_to_role.get(ROLE_SLUG_VIEWER)
            DataroomCollaborator.objects.update_or_create(
                dataroom=dataroom,
                user=user,
                defaults={'invited_by': admin, 'dataroom_role': role},
            )

        for u in (viewer, contributor, custom):
            ensure_collab(u)

        def ensure_doc(name, owner):
            doc, _ = Document.objects.get_or_create(
                name=name,
                organization=org,
                created_by=owner,
                defaults={'status': 'ready', 'file_size': 512},
            )
            DocumentVersion.objects.get_or_create(
                document=doc,
                version_number=1,
                defaults={
                    'is_primary': True,
                    'original_storage_key': f'demo/{name}',
                    'file_size': 512,
                },
            )
            dd, _ = DataroomDocument.objects.get_or_create(
                dataroom=dataroom,
                document=doc,
                defaults={'name': name},
            )
            return dd

        try:
            from datarooms.services import get_or_create_dataroom_storage_folder

            get_or_create_dataroom_storage_folder(dataroom, requesting_user=admin)
        except Exception:
            pass

        admin_dd = ensure_doc('admin-owned.pdf', admin)
        contributor_dd = ensure_doc('contributor-owned.pdf', contributor)

        meta_path = Path('/opt/cursor/artifacts/rbac-demo-meta.json')
        meta_path.parent.mkdir(parents=True, exist_ok=True)
        meta_path.write_text(
            json.dumps(
                {
                    'dataroom_id': str(dataroom.id),
                    'dataroom_name': dataroom.name,
                    'admin_dataroom_document_id': str(admin_dd.id),
                    'contributor_dataroom_document_id': str(contributor_dd.id),
                }
            ),
            encoding='utf-8',
        )
        self.stdout.write(self.style.SUCCESS(f'Demo dataroom id={dataroom.id}'))
        self.stdout.write(self.style.SUCCESS('Demo users ready (password: password123)'))
