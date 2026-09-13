from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from adminpanel.models import AdminUser
from .models import (
    Organization,
    OrganizationDocument,
    OrganizationRepresentative,
    OrganizationSocialLink,
    OrganizationVouch,
    VerificationAuditLog,
)

User = get_user_model()


class OrganizationsTestBase(APITestCase):
    def setUp(self):
        self.enabler = User.objects.create_user(
            username='enabler_test', email='enabler@test.com', password='pass',
            role='enabler', is_email_verified=True,
        )
        self.other_enabler = User.objects.create_user(
            username='enabler_two', email='enabler2@test.com', password='pass',
            role='enabler', is_email_verified=True,
        )
        self.pathfinder = User.objects.create_user(
            username='pathfinder_test', email='pathfinder@test.com', password='pass',
            role='pathfinder', is_email_verified=True,
        )


class OrganizationCreateTests(OrganizationsTestBase):
    def test_pathfinder_cannot_create_organization(self):
        self.client.force_authenticate(user=self.pathfinder)
        response = self.client.post(reverse('organization-create'), {
            'name': 'Test Org', 'organization_type': 'ngo', 'country': 'Nigeria',
        })
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_enabler_creates_organization_defaults_to_tier_3_active(self):
        self.client.force_authenticate(user=self.enabler)
        response = self.client.post(reverse('organization-create'), {
            'name': 'Test Org', 'organization_type': 'ngo', 'country': 'Nigeria',
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        organization = Organization.objects.get(name='Test Org')
        self.assertEqual(organization.tier, Organization.Tier.TIER_3)
        self.assertEqual(organization.tier_status, Organization.TierStatus.ACTIVE)
        self.assertEqual(organization.created_by, self.enabler)

    def test_organization_creation_writes_audit_log(self):
        self.client.force_authenticate(user=self.enabler)
        self.client.post(reverse('organization-create'), {
            'name': 'Test Org', 'organization_type': 'ngo', 'country': 'Nigeria',
        })
        organization = Organization.objects.get(name='Test Org')
        log = VerificationAuditLog.objects.get(
            entity_type=VerificationAuditLog.EntityType.ORGANIZATION, entity_id=str(organization.id)
        )
        self.assertEqual(log.action, VerificationAuditLog.Action.SUBMITTED)


class OrganizationRepresentativeTests(OrganizationsTestBase):
    def setUp(self):
        super().setUp()
        self.organization = Organization.objects.create(
            name='Test Org', organization_type='ngo', country='Nigeria', created_by=self.enabler,
        )

    def test_representative_registration_requires_email_or_letter(self):
        self.client.force_authenticate(user=self.enabler)
        url = reverse('organization-representative-list-create', args=[self.organization.id])
        response = self.client.post(url, {
            'full_name': 'Jane Doe', 'role_title': 'Coordinator',
            'phone_number': '+2348000000000', 'social_media_url': 'linkedin.com/in/janedoe',
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_representative_registration_succeeds_as_pending(self):
        self.client.force_authenticate(user=self.enabler)
        url = reverse('organization-representative-list-create', args=[self.organization.id])
        response = self.client.post(url, {
            'full_name': 'Jane Doe', 'role_title': 'Coordinator', 'work_email': 'jane@testorg.com',
            'phone_number': '+2348000000000', 'social_media_url': 'linkedin.com/in/janedoe',
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        representative = OrganizationRepresentative.objects.get(organization=self.organization, user=self.enabler)
        self.assertEqual(representative.verification_status, OrganizationRepresentative.VerificationStatus.PENDING)
        self.assertTrue(
            VerificationAuditLog.objects.filter(
                entity_type=VerificationAuditLog.EntityType.REPRESENTATIVE, entity_id=str(representative.id)
            ).exists()
        )

    def test_duplicate_representative_application_rejected(self):
        self.client.force_authenticate(user=self.enabler)
        url = reverse('organization-representative-list-create', args=[self.organization.id])
        payload = {
            'full_name': 'Jane Doe', 'role_title': 'Coordinator', 'work_email': 'jane@testorg.com',
            'phone_number': '+2348000000000', 'social_media_url': 'linkedin.com/in/janedoe',
        }
        self.client.post(url, payload)
        response = self.client.post(url, payload)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class OrganizationDocumentTests(OrganizationsTestBase):
    def setUp(self):
        super().setUp()
        self.organization = Organization.objects.create(
            name='Test Org', organization_type='ngo', country='Nigeria', created_by=self.enabler,
        )

    def test_non_member_cannot_upload_document(self):
        self.client.force_authenticate(user=self.other_enabler)
        url = reverse('organization-document-list-create', args=[self.organization.id])
        fake_file = SimpleUploadedFile('cert.pdf', b'not a real pdf', content_type='application/pdf')
        response = self.client.post(url, {'document_type': 'cac_certificate', 'file': fake_file}, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_oversized_document_rejected(self):
        self.client.force_authenticate(user=self.enabler)
        url = reverse('organization-document-list-create', args=[self.organization.id])
        from django.test import override_settings

        with override_settings(MAX_ORG_DOCUMENT_MB=0):
            fake_file = SimpleUploadedFile(
                'cert.pdf', b'some bytes that exceed a 0 mb cap', content_type='application/pdf'
            )
            response = self.client.post(
                url, {'document_type': 'cac_certificate', 'file': fake_file}, format='multipart'
            )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_letterhead_accepts_pdf(self):
        """Regression test: letterhead/recognition_letter uploads used to be
        rejected as PDFs even though they're commonly scanned/issued that way."""
        self.client.force_authenticate(user=self.enabler)
        url = reverse('organization-document-list-create', args=[self.organization.id])
        fake_file = SimpleUploadedFile('letterhead.pdf', b'%PDF-1.4 fake pdf bytes', content_type='application/pdf')
        response = self.client.post(url, {'document_type': 'letterhead', 'file': fake_file}, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_recognition_letter_accepts_pdf(self):
        self.client.force_authenticate(user=self.enabler)
        url = reverse('organization-document-list-create', args=[self.organization.id])
        fake_file = SimpleUploadedFile('recognition.pdf', b'%PDF-1.4 fake pdf bytes', content_type='application/pdf')
        response = self.client.post(url, {'document_type': 'recognition_letter', 'file': fake_file}, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)


class OrganizationProfileUpdateTests(OrganizationsTestBase):
    """website + scuml_id, added after frontend feedback flagged both as
    having no writable field anywhere."""

    def setUp(self):
        super().setUp()
        self.ngo = Organization.objects.create(
            name='Test NGO', organization_type='ngo', country='Nigeria', created_by=self.enabler,
        )
        self.company = Organization.objects.create(
            name='Test Company', organization_type='company', country='Nigeria', created_by=self.enabler,
        )

    def test_owner_can_set_website(self):
        self.client.force_authenticate(user=self.enabler)
        url = reverse('organization-detail', args=[self.ngo.id])
        response = self.client.patch(url, {'website': 'theorg.org'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.ngo.refresh_from_db()
        self.assertEqual(self.ngo.website, 'https://theorg.org')

    def test_ngo_can_set_scuml_id(self):
        self.client.force_authenticate(user=self.enabler)
        url = reverse('organization-detail', args=[self.ngo.id])
        response = self.client.patch(url, {'scuml_id': 'SCUML12345'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.ngo.refresh_from_db()
        self.assertEqual(self.ngo.scuml_id, 'SCUML12345')

    def test_non_ngo_cannot_set_scuml_id(self):
        self.client.force_authenticate(user=self.enabler)
        url = reverse('organization-detail', args=[self.company.id])
        response = self.client.patch(url, {'scuml_id': 'SCUML12345'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class OrganizationSocialLinkUpdateTests(OrganizationsTestBase):
    """PATCH on a social link, added after frontend feedback flagged
    delete-then-recreate as the only available "edit" path."""

    def setUp(self):
        super().setUp()
        self.organization = Organization.objects.create(
            name='Test Org', organization_type='ngo', country='Nigeria', created_by=self.enabler,
        )
        self.link = OrganizationSocialLink.objects.create(
            organization=self.organization, platform=OrganizationSocialLink.Platform.LINKEDIN,
            url='https://linkedin.com/company/testorg', activity_verified=True,
        )

    def test_owner_can_edit_url_via_patch(self):
        self.client.force_authenticate(user=self.enabler)
        url = reverse('organization-social-link-detail', args=[self.link.id])
        response = self.client.patch(url, {'url': 'linkedin.com/company/renamed-org'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.link.refresh_from_db()
        self.assertEqual(self.link.url, 'https://linkedin.com/company/renamed-org')

    def test_patch_accepts_partial_payload_platform_unrequired(self):
        """PATCH is a real partial update — sending only `url` must not require
        `platform` too, and must leave the existing platform untouched."""
        self.client.force_authenticate(user=self.enabler)
        url = reverse('organization-social-link-detail', args=[self.link.id])
        response = self.client.patch(url, {'url': 'linkedin.com/company/only-url-changed'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.link.refresh_from_db()
        self.assertEqual(self.link.platform, OrganizationSocialLink.Platform.LINKEDIN)

    def test_editing_link_resets_activity_verified(self):
        self.client.force_authenticate(user=self.enabler)
        url = reverse('organization-social-link-detail', args=[self.link.id])
        self.client.patch(url, {'url': 'linkedin.com/company/renamed-org'}, format='json')
        self.link.refresh_from_db()
        self.assertFalse(self.link.activity_verified)

    def test_non_owner_cannot_edit_link(self):
        self.client.force_authenticate(user=self.other_enabler)
        url = reverse('organization-social-link-detail', args=[self.link.id])
        response = self.client.patch(url, {'url': 'linkedin.com/company/hijacked'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class RepresentativeAppointmentLetterValidationTests(OrganizationsTestBase):
    """Regression test: appointment_letter had no server-side size/format
    validation at all before this."""

    def setUp(self):
        super().setUp()
        self.organization = Organization.objects.create(
            name='Test Org', organization_type='ngo', country='Nigeria', created_by=self.enabler,
        )

    def test_appointment_letter_rejects_unsupported_format(self):
        self.client.force_authenticate(user=self.enabler)
        url = reverse('organization-representative-list-create', args=[self.organization.id])
        fake_file = SimpleUploadedFile('letter.exe', b'not a real file', content_type='application/octet-stream')
        response = self.client.post(url, {
            'full_name': 'Jane Doe', 'role_title': 'Coordinator', 'appointment_letter': fake_file,
            'phone_number': '+2348000000000', 'social_media_url': 'linkedin.com/in/janedoe',
        }, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_appointment_letter_accepts_pdf(self):
        self.client.force_authenticate(user=self.enabler)
        url = reverse('organization-representative-list-create', args=[self.organization.id])
        fake_file = SimpleUploadedFile('letter.pdf', b'%PDF-1.4 fake pdf bytes', content_type='application/pdf')
        response = self.client.post(url, {
            'full_name': 'Jane Doe', 'role_title': 'Coordinator', 'appointment_letter': fake_file,
            'phone_number': '+2348000000000', 'social_media_url': 'linkedin.com/in/janedoe',
        }, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)


class OrganizationMemberPermissionTests(OrganizationsTestBase):
    """Regression tests for the IsOrganizationMember suspended/pending-review
    check that used to only apply to the creator, not representatives."""

    def setUp(self):
        super().setUp()
        self.organization = Organization.objects.create(
            name='Test Org', organization_type='ngo', country='Nigeria', created_by=self.enabler,
        )
        self.representative = OrganizationRepresentative.objects.create(
            organization=self.organization, user=self.other_enabler, full_name='Jane Doe',
            role_title='Coordinator', work_email='jane@testorg.com', phone_number='+2348000000000',
            social_media_url='https://linkedin.com/in/janedoe',
        )

    def test_suspended_organization_hidden_from_representative(self):
        self.organization.tier_status = Organization.TierStatus.SUSPENDED
        self.organization.save(update_fields=['tier_status'])

        self.client.force_authenticate(user=self.other_enabler)
        response = self.client.get(reverse('organization-detail', args=[self.organization.id]))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_suspended_organization_hidden_from_creator(self):
        self.organization.tier_status = Organization.TierStatus.SUSPENDED
        self.organization.save(update_fields=['tier_status'])

        self.client.force_authenticate(user=self.enabler)
        response = self.client.get(reverse('organization-detail', args=[self.organization.id]))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_active_organization_visible_to_representative(self):
        self.client.force_authenticate(user=self.other_enabler)
        response = self.client.get(reverse('organization-detail', args=[self.organization.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class AdminOrganizationWorkflowTests(OrganizationsTestBase):
    """Sprint 3 — admin review workflow."""

    def setUp(self):
        super().setUp()
        self.admin = AdminUser.objects.create(full_name='Admin One', email='admin@afrivate.test')
        self.admin.set_password('pass')
        self.admin.save()
        self.organization = Organization.objects.create(
            name='Test Org', organization_type='ngo', country='Nigeria', created_by=self.enabler,
            tier_status=Organization.TierStatus.PENDING_REVIEW,
        )

    def test_non_admin_cannot_reach_admin_queue(self):
        self.client.force_authenticate(user=self.enabler)
        response = self.client.get(reverse('admin-organization-queue'))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_queue_lists_pending_organizations(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.get(reverse('admin-organization-queue'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = [row['id'] for row in response.data['results']]
        self.assertIn(str(self.organization.id), ids)

    def test_admin_approve_sets_tier_and_logs(self):
        self.client.force_authenticate(user=self.admin)
        url = reverse('admin-organization-approve', args=[self.organization.id])
        response = self.client.post(url, {'tier': 'tier_1', 'notes': 'CAC certificate checks out.'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.organization.refresh_from_db()
        self.assertEqual(self.organization.tier, Organization.Tier.TIER_1)
        self.assertEqual(self.organization.tier_status, Organization.TierStatus.ACTIVE)
        self.assertTrue(
            VerificationAuditLog.objects.filter(
                entity_type=VerificationAuditLog.EntityType.ORGANIZATION,
                entity_id=str(self.organization.id),
                action=VerificationAuditLog.Action.TIER_UPGRADED,
                performed_by_admin=self.admin,
            ).exists()
        )

    def test_admin_approve_tier_2_marks_admin_approved(self):
        self.client.force_authenticate(user=self.admin)
        url = reverse('admin-organization-approve', args=[self.organization.id])
        self.client.post(url, {'tier': 'tier_2', 'notes': 'Phone verification complete.'})

        self.organization.refresh_from_db()
        self.assertEqual(self.organization.tier, Organization.Tier.TIER_2)
        self.assertTrue(self.organization.tier_2_admin_approved)

    def test_admin_reject_requires_reason(self):
        self.client.force_authenticate(user=self.admin)
        url = reverse('admin-organization-reject', args=[self.organization.id])
        response = self.client.post(url, {})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_admin_reject_sets_status_and_logs(self):
        self.client.force_authenticate(user=self.admin)
        url = reverse('admin-organization-reject', args=[self.organization.id])
        response = self.client.post(url, {'reason': 'Certificate is illegible.'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.organization.refresh_from_db()
        self.assertEqual(self.organization.tier_status, Organization.TierStatus.REJECTED)

    def test_admin_suspend_then_reinstate(self):
        self.organization.tier_status = Organization.TierStatus.ACTIVE
        self.organization.save(update_fields=['tier_status'])

        self.client.force_authenticate(user=self.admin)
        suspend_url = reverse('admin-organization-suspend', args=[self.organization.id])
        response = self.client.post(suspend_url, {'reason': 'Fraud report received.'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.organization.refresh_from_db()
        self.assertEqual(self.organization.tier_status, Organization.TierStatus.SUSPENDED)

        # Suspending again should be rejected, not silently re-applied.
        response = self.client.post(suspend_url, {'reason': 'Again.'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        reinstate_url = reverse('admin-organization-reinstate', args=[self.organization.id])
        response = self.client.post(reinstate_url, {'reason': 'Dispute resolved in their favor.'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.organization.refresh_from_db()
        self.assertEqual(self.organization.tier_status, Organization.TierStatus.ACTIVE)

    def test_admin_document_review(self):
        document = OrganizationDocument.objects.create(
            organization=self.organization, document_type=OrganizationDocument.DocumentType.CAC_CERTIFICATE,
            file=SimpleUploadedFile('cert.pdf', b'fake pdf'),
        )
        self.client.force_authenticate(user=self.admin)
        url = reverse('admin-organization-document-review', args=[document.id])
        response = self.client.post(url, {'status': 'approved'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        document.refresh_from_db()
        self.assertEqual(document.review_status, OrganizationDocument.ReviewStatus.APPROVED)
        self.assertEqual(document.reviewed_by_admin, self.admin)

    def test_admin_social_link_verify(self):
        link = OrganizationSocialLink.objects.create(
            organization=self.organization, platform=OrganizationSocialLink.Platform.LINKEDIN,
            url='https://linkedin.com/company/testorg',
        )
        self.client.force_authenticate(user=self.admin)
        url = reverse('admin-organization-social-link-verify', args=[link.id])
        response = self.client.post(url, {'activity_verified': True}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        link.refresh_from_db()
        self.assertTrue(link.activity_verified)

    def test_admin_representative_verify(self):
        representative = OrganizationRepresentative.objects.create(
            organization=self.organization, user=self.other_enabler, full_name='Jane Doe',
            role_title='Coordinator', work_email='jane@testorg.com', phone_number='+2348000000000',
            social_media_url='https://linkedin.com/in/janedoe',
        )
        self.client.force_authenticate(user=self.admin)
        url = reverse('admin-representative-verify', args=[representative.id])
        response = self.client.post(url, {
            'status': 'verified',
            'verification_method': ['work_email_domain_match', 'phone_call'],
            'call_notes': 'Confirmed by phone.',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        representative.refresh_from_db()
        self.assertEqual(representative.verification_status, OrganizationRepresentative.VerificationStatus.VERIFIED)
        self.assertEqual(representative.verified_by_admin, self.admin)
        self.assertTrue(representative.can_attest)

    def test_admin_representative_reject_requires_call_notes(self):
        representative = OrganizationRepresentative.objects.create(
            organization=self.organization, user=self.other_enabler, full_name='Jane Doe',
            role_title='Coordinator', work_email='jane@testorg.com', phone_number='+2348000000000',
            social_media_url='https://linkedin.com/in/janedoe',
        )
        self.client.force_authenticate(user=self.admin)
        url = reverse('admin-representative-verify', args=[representative.id])
        response = self.client.post(url, {'status': 'rejected', 'verification_method': []}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class OrganizationVouchTests(OrganizationsTestBase):
    """Sprint 4 — Tier 2 vouching flow."""

    def setUp(self):
        super().setUp()
        self.voucher_org = Organization.objects.create(
            name='Voucher Org', organization_type='ngo', country='Nigeria', created_by=self.enabler,
            tier=Organization.Tier.TIER_1,
        )
        self.applicant_org = Organization.objects.create(
            name='Applicant Org', organization_type='ngo', country='Nigeria', created_by=self.other_enabler,
        )

    def test_tier1_org_vouch_promotes_applicant_to_tier2(self):
        self.client.force_authenticate(user=self.enabler)
        url = reverse('organization-vouch-create', args=[self.applicant_org.id])
        response = self.client.post(url, {
            'from_organization': str(self.voucher_org.id),
            'vouch_text': 'We have worked with this organization for two years.',
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        self.applicant_org.refresh_from_db()
        self.assertEqual(self.applicant_org.tier, Organization.Tier.TIER_2)
        self.assertTrue(
            VerificationAuditLog.objects.filter(
                entity_type=VerificationAuditLog.EntityType.ORGANIZATION,
                entity_id=str(self.applicant_org.id),
                action=VerificationAuditLog.Action.TIER_UPGRADED,
            ).exists()
        )

    def test_tier3_org_cannot_vouch(self):
        ineligible_org = Organization.objects.create(
            name='Ineligible Org', organization_type='ngo', country='Nigeria', created_by=self.enabler,
        )
        self.client.force_authenticate(user=self.enabler)
        url = reverse('organization-vouch-create', args=[self.applicant_org.id])
        response = self.client.post(url, {
            'from_organization': str(ineligible_org.id), 'vouch_text': 'Trust me.',
        })
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_tier2_org_not_admin_approved_cannot_vouch(self):
        unapproved_tier2 = Organization.objects.create(
            name='Unapproved Tier 2', organization_type='ngo', country='Nigeria', created_by=self.enabler,
            tier=Organization.Tier.TIER_2, tier_2_admin_approved=False,
        )
        self.client.force_authenticate(user=self.enabler)
        url = reverse('organization-vouch-create', args=[self.applicant_org.id])
        response = self.client.post(url, {
            'from_organization': str(unapproved_tier2.id), 'vouch_text': 'Trust me.',
        })
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_approved_tier2_org_can_vouch(self):
        approved_tier2 = Organization.objects.create(
            name='Approved Tier 2', organization_type='ngo', country='Nigeria', created_by=self.enabler,
            tier=Organization.Tier.TIER_2, tier_2_admin_approved=True,
        )
        self.client.force_authenticate(user=self.enabler)
        url = reverse('organization-vouch-create', args=[self.applicant_org.id])
        response = self.client.post(url, {
            'from_organization': str(approved_tier2.id), 'vouch_text': 'Trust me.',
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_cannot_vouch_for_self(self):
        self.client.force_authenticate(user=self.enabler)
        url = reverse('organization-vouch-create', args=[self.voucher_org.id])
        response = self.client.post(url, {
            'from_organization': str(self.voucher_org.id), 'vouch_text': 'Trust me.',
        })
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_non_member_cannot_vouch_on_behalf_of_organization(self):
        self.client.force_authenticate(user=self.other_enabler)
        url = reverse('organization-vouch-create', args=[self.applicant_org.id])
        response = self.client.post(url, {
            'from_organization': str(self.voucher_org.id), 'vouch_text': 'Trust me.',
        })
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_duplicate_vouch_rejected(self):
        self.client.force_authenticate(user=self.enabler)
        url = reverse('organization-vouch-create', args=[self.applicant_org.id])
        payload = {'from_organization': str(self.voucher_org.id), 'vouch_text': 'Trust me.'}
        self.client.post(url, payload)
        response = self.client.post(url, payload)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_cannot_vouch_for_organization_already_tier2(self):
        self.applicant_org.tier = Organization.Tier.TIER_2
        self.applicant_org.save(update_fields=['tier'])

        self.client.force_authenticate(user=self.enabler)
        url = reverse('organization-vouch-create', args=[self.applicant_org.id])
        response = self.client.post(url, {
            'from_organization': str(self.voucher_org.id), 'vouch_text': 'Trust me.',
        })
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class OrganizationRepresentativeRevokeTests(OrganizationsTestBase):
    def setUp(self):
        super().setUp()
        self.organization = Organization.objects.create(
            name='Test Org', organization_type='ngo', country='Nigeria', created_by=self.enabler,
        )
        self.representative = OrganizationRepresentative.objects.create(
            organization=self.organization, user=self.other_enabler, full_name='Jane Doe',
            role_title='Coordinator', work_email='jane@testorg.com', phone_number='+2348000000000',
            social_media_url='https://linkedin.com/in/janedoe',
        )

    def test_owner_can_revoke_representative(self):
        self.client.force_authenticate(user=self.enabler)
        url = reverse('organization-representative-revoke', args=[self.organization.id, self.representative.id])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(OrganizationRepresentative.objects.filter(id=self.representative.id).exists())
        self.assertTrue(
            VerificationAuditLog.objects.filter(
                entity_type=VerificationAuditLog.EntityType.REPRESENTATIVE,
                entity_id=str(self.representative.id),
                action=VerificationAuditLog.Action.REVOKED,
            ).exists()
        )

    def test_non_owner_cannot_revoke_representative(self):
        self.client.force_authenticate(user=self.other_enabler)
        url = reverse('organization-representative-revoke', args=[self.organization.id, self.representative.id])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
