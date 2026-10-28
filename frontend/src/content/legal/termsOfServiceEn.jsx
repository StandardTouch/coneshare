/**
 * Terms of Service — self-hosted document sharing (Coneshare-based deployment).
 * Replace [Operator] and contact details via Admin → Branding or edit for your jurisdiction.
 * Not legal advice; have counsel review before production use.
 */

export function TermsOfServiceContent({ operatorName = 'Allure Clinic', contactEmail = 'privacy@allureclinic.com' }) {
  return (
    <>
      <p>
        These Terms of Service (&quot;Terms&quot;) govern access to and use of the secure document sharing
        and collaboration platform (the &quot;Service&quot;) operated by <strong>{operatorName}</strong>{' '}
        (&quot;we,&quot; &quot;us,&quot; or &quot;Operator&quot;). The Service enables authorized staff to
        store, organize, and share documents and media with internal teams and external recipients through
        protected links, virtual datarooms, and file-request uploads.
      </p>

      <h2 className="mt-8 text-xl font-semibold text-gray-900 dark:text-gray-100">1. Acceptance</h2>
      <p>
        By creating an account, signing in, uploading content, or accessing a shared link we provide, you
        agree to these Terms. If you use the Service on behalf of an organization, you represent that you
        have authority to bind that organization. If you do not agree, do not use the Service.
      </p>

      <h2 className="mt-8 text-xl font-semibold text-gray-900 dark:text-gray-100">2. The Service</h2>
      <p>The Service may include, without limitation:</p>
      <ul className="list-disc space-y-2 pl-6">
        <li>Document and folder storage, versioning, and preview in the browser</li>
        <li>Share links with optional password, email verification, NDA acceptance, watermarks, and expiry</li>
        <li>Virtual datarooms for grouped due diligence or project files</li>
        <li>Viewer analytics (e.g., page views, session duration, download events where enabled)</li>
        <li>File-request pages for external parties to submit documents without an account</li>
        <li>Optional connections to cloud storage providers (e.g., Google Drive) for import</li>
        <li>Workflow notifications and automations configured by your organization</li>
      </ul>
      <p>
        Features available to you depend on your role, organization settings, and link or dataroom
        permissions. We may update the Service from time to time; material changes will be communicated
        through the application or your administrator.
      </p>

      <h2 className="mt-8 text-xl font-semibold text-gray-900 dark:text-gray-100">3. Accounts and access</h2>
      <ul className="list-disc space-y-2 pl-6">
        <li>Staff accounts are provisioned by your organization&apos;s administrators.</li>
        <li>You must keep login credentials confidential and notify your administrator of suspected unauthorized use.</li>
        <li>
          External recipients may access content only through links or upload pages we or your organization
          issue; they must comply with any password, email, NDA, or other access requirements shown at access time.
        </li>
      </ul>

      <h2 className="mt-8 text-xl font-semibold text-gray-900 dark:text-gray-100">4. Your content and responsibilities</h2>
      <p>
        You and your organization retain ownership of documents and data you upload. You are responsible for:
      </p>
      <ul className="list-disc space-y-2 pl-6">
        <li>Ensuring you have the right to upload, share, and process content (including patient, employee, or third-party data)</li>
        <li>Configuring share settings appropriately (access controls, retention, download permissions)</li>
        <li>Compliance with applicable laws (including health privacy, employment, and commercial confidentiality rules in your region)</li>
        <li>Not uploading malware, unlawful material, or content that infringes others&apos; rights</li>
      </ul>
      <p>
        We may suspend or remove access to content that violates these Terms or law, or when required to
        protect the Service or other users, subject to your organization&apos;s policies.
      </p>

      <h2 className="mt-8 text-xl font-semibold text-gray-900 dark:text-gray-100">5. Sharing and viewer obligations</h2>
      <p>
        If you receive a share link or file-request URL, you may use it only for the purpose intended by the
        sender. You must not attempt to bypass security controls (passwords, watermarks, download blocks),
        scrape bulk content, or redistribute confidential materials except as permitted by the sender or law.
        NDA or consent text presented before viewing is part of your agreement with the organization that shared the content.
      </p>

      <h2 className="mt-8 text-xl font-semibold text-gray-900 dark:text-gray-100">6. Acceptable use</h2>
      <p>You must not:</p>
      <ul className="list-disc space-y-2 pl-6">
        <li>Probe, scan, or test the vulnerability of the Service without written authorization</li>
        <li>Interfere with or overload infrastructure (including automated abuse of upload or auth endpoints)</li>
        <li>Use the Service to send spam or phishing, or to distribute malicious code</li>
        <li>Misrepresent your identity when accessing password- or email-protected links</li>
      </ul>

      <h2 className="mt-8 text-xl font-semibold text-gray-900 dark:text-gray-100">7. Third-party services</h2>
      <p>
        If you connect cloud storage or enable integrations (webhooks, chat notifications, optional monitoring tools),
        those services are governed by their own terms. You authorize the Service to exchange data with connected
        providers only as needed to perform the actions you request (e.g., import a file from Google Drive).
      </p>

      <h2 className="mt-8 text-xl font-semibold text-gray-900 dark:text-gray-100">8. Availability and disclaimers</h2>
      <p>
        The Service is provided on an &quot;AS IS&quot; and &quot;AS AVAILABLE&quot; basis. We strive for reliable
        operation but do not guarantee uninterrupted or error-free service. Document previews, conversions, and
        analytics depend on file type, size, and server capacity. To the fullest extent permitted by law, we
        disclaim warranties of merchantability, fitness for a particular purpose, and non-infringement.
      </p>

      <h2 className="mt-8 text-xl font-semibold text-gray-900 dark:text-gray-100">9. Limitation of liability</h2>
      <p>
        To the maximum extent permitted by law, {operatorName} and its affiliates, officers, and staff shall not
        be liable for indirect, incidental, special, consequential, or punitive damages, or for loss of profits,
        data, or goodwill, arising from use of the Service. Our aggregate liability for claims relating to the
        Service shall not exceed the amount paid by your organization for the Service in the twelve (12) months
        before the claim, or one hundred (100) USD if the Service is provided without charge, whichever is greater,
        except where liability cannot be limited by applicable law.
      </p>

      <h2 className="mt-8 text-xl font-semibold text-gray-900 dark:text-gray-100">10. Termination</h2>
      <p>
        Your organization may deactivate accounts or revoke links at any time. We may suspend access for breach
        of these Terms or to address security risk. Upon termination, your right to use the Service ends;
        retention of stored documents is governed by your organization&apos;s policies and applicable law.
      </p>

      <h2 className="mt-8 text-xl font-semibold text-gray-900 dark:text-gray-100">11. Changes</h2>
      <p>
        We may update these Terms. The &quot;Last updated&quot; date at the top will change when we do.
        Continued use after changes constitutes acceptance, unless applicable law requires a different process.
      </p>

      <h2 className="mt-8 text-xl font-semibold text-gray-900 dark:text-gray-100">12. Governing law</h2>
      <p>
        These Terms are governed by the laws applicable in the jurisdiction where {operatorName} operates,
        without regard to conflict-of-law rules, unless mandatory local consumer protections apply to you.
      </p>

      <h2 className="mt-8 text-xl font-semibold text-gray-900 dark:text-gray-100">13. Contact</h2>
      <p>
        Questions about these Terms:
        <br />
        <strong>{operatorName}</strong>
        <br />
        Email: <a className="text-primary underline" href={`mailto:${contactEmail}`}>{contactEmail}</a>
      </p>
    </>
  );
}
