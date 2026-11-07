"""Seed users and data for RBAC Playwright screenshot runs."""
from django.core.management.base import BaseCommand
from django.db import transaction

from core.models import Organization, User
from datarooms.models import Dataroom, DataroomCollaborator, DataroomDocument
from documents.models import Document, DocumentVersion, Folder
from permissions_rbac.catalogue import PERM_FILE_DOWNLOAD, PERM_FILE_VIEW
from permissions_rbac.models import DataroomRole, DataroomRolePermission
from permissions_rbac.seed import ensure_default_roles_for_organization


class Command(BaseCommand):
    help = 'Seed Admin, Manager, Limited users and a shared dataroom for RBAC screenshots.'

    @transaction.atomic
    def handle(self, *args, **options):
        org, _ = Organization.objects.get_or_create(name='Default Organization')
        roles = ensure_default_roles_for_organization(org)
        admin_role = roles['admin']
        manager_role = roles['manager']

        limited, _ = DataroomRole.objects.get_or_create(
            organization=org,
            slug='limited',
            defaults={'name': 'Limited', 'is_system': False, 'description': 'View + download only'},
        )
        DataroomRolePermission.objects.filter(role=limited).delete()
        DataroomRolePermission.objects.bulk_create(
            [
                DataroomRolePermission(role=limited, permission=PERM_FILE_VIEW, scope=''),
                DataroomRolePermission(role=limited, permission=PERM_FILE_DOWNLOAD, scope=''),
            ]
        )

        def ensure_user(email, *, role_site, org_role=None, is_admin=False):
            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    'username': email,
                    'organization': org,
                    'name': email.split('@')[0].title(),
                    'role': role_site,
                },
            )
            user.role = role_site
            user.organization_role = org_role
            user.set_password('password123')
            user.save()
            return user

        admin = ensure_user('admin@coneshare.com', role_site='admin', org_role=None, is_admin=True)
        manager = ensure_user('manager@coneshare.com', role_site='member', org_role=manager_role)
        limited_user = ensure_user('limited@coneshare.com', role_site='member', org_role=limited)

        owner = User.objects.filter(email='test@coneshare.com', organization=org).first() or admin

        dataroom, _ = Dataroom.objects.get_or_create(
            name='RBAC Demo Dataroom',
            organization=org,
            created_by=owner,
            defaults={'enable_qna': True},
        )
        for collab_user in (manager, limited_user):
            DataroomCollaborator.objects.get_or_create(
                dataroom=dataroom,
                user=collab_user,
                defaults={'invited_by': owner},
            )

        root = Folder.objects.get_root_for_org(org)
        pdf, _ = Document.objects.get_or_create(
            name='Signature Demo.pdf',
            organization=org,
            created_by=owner,
            folder=root,
            defaults={'status': 'ready', 'type': 'pdf', 'file_size': 1024},
        )
        if not pdf.versions.filter(is_primary=True).exists():
            DocumentVersion.objects.create(
                document=pdf,
                version_number=1,
                is_primary=True,
                original_storage_key='screenshots/signature-demo.pdf',
                file_size=1024,
            )
        DataroomDocument.objects.get_or_create(
            dataroom=dataroom,
            document=pdf,
            defaults={'name': pdf.name},
        )

        self.stdout.write(self.style.SUCCESS('RBAC screenshot seed complete.'))
        self.stdout.write(f'Admin role id: {admin_role.id}')
        self.stdout.write(f'Limited role id: {limited.id}')
        self.stdout.write(f'Dataroom id: {dataroom.id}')
