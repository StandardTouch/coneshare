/**
 * Privacy Policy — self-hosted document sharing (Coneshare-based deployment).
 * Operator processes data on infrastructure it controls; adjust for PDPL/GDPR with legal review.
 */

export function PrivacyPolicyContent({
  operatorName = 'Allure Clinic',
  contactEmail = 'share@allureclinics.net',
}) {
  return (
    <>
      <p className="lead">
        <strong>{operatorName}</strong> (&quot;we,&quot; &quot;us,&quot; or the &quot;Operator&quot;) operates
        the secure document sharing application at our dedicated subdomain (the &quot;Service&quot;). This
        Privacy Policy explains what personal information and Google user data we collect, why we collect it,
        how we use and share it, how long we keep it, and how you can contact us or request deletion.
      </p>
      <p>
        <strong>We do not sell your personal information.</strong> We do not use Google user data for
        advertising. Document content and account data are processed to provide the Service to {operatorName}
        and are stored on infrastructure we control or contract for hosting.
      </p>

      <h2 className="mt-8 text-xl font-semibold text-gray-900 dark:text-gray-100">
        Summary of data we collect
      </h2>
      <table className="mt-4 w-full border-collapse text-sm">
        <thead>
          <tr className="border-b border-gray-200 dark:border-gray-700">
            <th className="py-2 pr-4 text-left font-semibold">Category</th>
            <th className="py-2 text-left font-semibold">Examples</th>
            <th className="py-2 text-left font-semibold">Purpose</th>
          </tr>
        </thead>
        <tbody className="text-gray-700 dark:text-gray-300">
          <tr className="border-b border-gray-100 dark:border-gray-800">
            <td className="py-2 pr-4 align-top">Account data</td>
            <td className="py-2 pr-4 align-top">Email, name, password hash, role, language</td>
            <td className="py-2 align-top">Authentication and account management</td>
          </tr>
          <tr className="border-b border-gray-100 dark:border-gray-800">
            <td className="py-2 pr-4 align-top">Usage &amp; security logs</td>
            <td className="py-2 pr-4 align-top">IP address, browser type, login timestamps</td>
            <td className="py-2 align-top">Security, fraud prevention, audit</td>
          </tr>
          <tr className="border-b border-gray-100 dark:border-gray-800">
            <td className="py-2 pr-4 align-top">Documents &amp; metadata</td>
            <td className="py-2 pr-4 align-top">Files you upload, names, sizes, folder paths</td>
            <td className="py-2 align-top">Storage, preview, sharing, versioning</td>
          </tr>
          <tr className="border-b border-gray-100 dark:border-gray-800">
            <td className="py-2 pr-4 align-top">Share-link viewer data</td>
            <td className="py-2 pr-4 align-top">Viewer email (if required), session analytics</td>
            <td className="py-2 align-top">Access control and owner analytics</td>
          </tr>
          <tr className="border-b border-gray-100 dark:border-gray-800">
            <td className="py-2 pr-4 align-top">Google user data (optional)</td>
            <td className="py-2 pr-4 align-top">Profile email/name, OAuth tokens, files you import</td>
            <td className="py-2 align-top">Google Drive import only (see Section 2.6)</td>
          </tr>
        </tbody>
      </table>

      <h2 className="mt-8 text-xl font-semibold text-gray-900 dark:text-gray-100">1. Who this applies to</h2>
      <ul className="list-disc space-y-2 pl-6">
        <li>
          <strong>Organization users</strong> — staff and others with login accounts (email, name, profile settings).
        </li>
        <li>
          <strong>External viewers</strong> — people who open share links or submit files via file-request pages
          (may provide email, name, or custom intake fields).
        </li>
        <li>
          <strong>Administrators</strong> — users who manage accounts, branding, security settings, and audit logs.
        </li>
      </ul>

      <h2 className="mt-8 text-xl font-semibold text-gray-900 dark:text-gray-100">2. Information we collect</h2>

      <h3 className="mt-4 text-lg font-medium text-gray-900 dark:text-gray-100">2.1 Account and profile data</h3>
      <ul className="list-disc space-y-2 pl-6">
        <li>Email address, display name, password (stored hashed), language preference</li>
        <li>Optional avatar image, role (e.g., administrator or member), storage usage metrics</li>
        <li>Login activity (timestamp, IP address, browser user-agent) for security monitoring</li>
      </ul>

      <h3 className="mt-4 text-lg font-medium text-gray-900 dark:text-gray-100">2.2 Documents and metadata</h3>
      <ul className="list-disc space-y-2 pl-6">
        <li>Files you upload, folder structure, versions, and processing status</li>
        <li>Metadata such as file names, sizes, types, and optional uploader attribution on file-request submissions</li>
        <li>Custom intake field values submitted on public upload forms (as configured by your organization)</li>
      </ul>

      <h3 className="mt-4 text-lg font-medium text-gray-900 dark:text-gray-100">2.3 Sharing and viewer analytics</h3>
      <p>When sharing is enabled, we may record:</p>
      <ul className="list-disc space-y-2 pl-6">
        <li>Viewer email (if required on a link), IP address, browser/device information, approximate location (if derived from IP)</li>
        <li>View sessions: time on document, pages viewed, completion estimates, download events</li>
        <li>Video engagement segments (playback ranges, speed, mute/fullscreen where applicable)</li>
        <li>Clicks on links embedded in document previews</li>
        <li>NDA acceptance records (version, timestamp, session identifiers)</li>
        <li>Q&amp;A messages on shared links when that feature is enabled</li>
      </ul>

      <h3 className="mt-4 text-lg font-medium text-gray-900 dark:text-gray-100">2.4 Other cloud import (optional)</h3>
      <p>
        If you connect Dropbox, Nextcloud, or similar providers, we store OAuth tokens (encrypted) and import
        files you explicitly select. Those providers&apos; own privacy policies also apply.
      </p>

      <h3 className="mt-4 text-lg font-medium text-gray-900 dark:text-gray-100">
        2.5 Google user data (Google Drive connection)
      </h3>
      <p>
        If you choose to connect Google Drive, our use of information received from Google APIs adheres to the{' '}
        <a
          className="text-primary underline"
          href="https://developers.google.com/terms/api-services-user-data-policy"
          target="_blank"
          rel="noopener noreferrer"
        >
          Google API Services User Data Policy
        </a>
        , including the Limited Use requirements.
      </p>
      <p>
        <strong>What we access from Google:</strong> With your consent, we request OAuth scopes to read your
        Google account profile (email and basic profile information), list and read files in Google Drive that
        you choose to import, and create or update files in Drive only when you use export features we provide.
        We do not request access to your Gmail, Calendar, Contacts, or other Google products beyond Drive-related
        scopes configured in our OAuth client.
      </p>
      <p>
        <strong>How we use Google user data:</strong> Solely to (1) identify your connected account, (2) display
        files and folders you browse for import, (3) download copies of files you select into {operatorName}&apos;s
        document library on our servers, and (4) upload exported submissions to folders you designate when you
        run an export action. We do not use Google user data for advertising, sell it, or use it to train general
        AI/ML models unrelated to providing this Service to you.
      </p>
      <p>
        <strong>How we store Google user data:</strong> OAuth refresh tokens are stored encrypted in our
        application database. Imported file content is stored in our file storage system like other uploads.
        Connection metadata (account identifier, token expiry) is retained until you disconnect the integration
        or your account is deleted.
      </p>
      <p>
        <strong>Sharing Google user data:</strong> We do not disclose Google user data to third parties except
        (a) subprocessors that host our infrastructure under contract and only as needed to operate the Service,
        (b) when you direct an export to your Google Drive or another integration, or (c) when required by law.
      </p>
      <p>
        <strong>Revoking access:</strong> You may disconnect Google Drive in the Service settings, revoke the app
        at{' '}
        <a
          className="text-primary underline"
          href="https://myaccount.google.com/permissions"
          target="_blank"
          rel="noopener noreferrer"
        >
          Google Account permissions
        </a>
        , or contact us at{' '}
        <a className="text-primary underline" href={`mailto:${contactEmail}`}>{contactEmail}</a>. After
        revocation, we delete or invalidate stored OAuth tokens for that connection within a reasonable period.
      </p>

      <h3 className="mt-4 text-lg font-medium text-gray-900 dark:text-gray-100">2.6 Security and file requests</h3>
      <p>
        When malware scanning is enabled, uploaded files may be scanned before storage; blocked uploads may
        generate security alerts visible to administrators (file name, uploader details, scan result — not
        necessarily full file content in logs).
      </p>

      <h2 className="mt-8 text-xl font-semibold text-gray-900 dark:text-gray-100">3. How we use information</h2>
      <ul className="list-disc space-y-2 pl-6">
        <li>Provide, secure, and maintain the Service (authentication, authorization, quotas, previews)</li>
        <li>Enforce share-link protections (password, email verification, NDA, watermarks, expiry)</li>
        <li>Display analytics to authorized users about how shared content is accessed</li>
        <li>Send transactional emails (verification, notifications, automations configured by your organization)</li>
        <li>Detect abuse, investigate security incidents, and comply with legal obligations</li>
        <li>Improve reliability and fix errors (optional error monitoring if enabled by your IT team)</li>
      </ul>
      <p>
        We do <strong>not</strong> use document contents for third-party advertising profiles. Optional AI or
        MCP integrations, if enabled by your organization, operate under separate settings and API key permissions.
      </p>

      <h2 className="mt-8 text-xl font-semibold text-gray-900 dark:text-gray-100">4. Legal bases (where applicable)</h2>
      <p>
        Depending on your region, we rely on one or more of: performance of a contract (providing the Service),
        legitimate interests (security, analytics for content owners, fraud prevention), consent (where required
        for optional features or marketing), and legal obligation. Health or sensitive data in uploaded files is
        processed on instructions of {operatorName} as the organization responsible for that content.
      </p>

      <h2 className="mt-8 text-xl font-semibold text-gray-900 dark:text-gray-100">5. Sharing and disclosure</h2>
      <p>We may share personal information only:</p>
      <ul className="list-disc space-y-2 pl-6">
        <li>With service providers that host or support the deployment (hosting, email SMTP, backup), under contract</li>
        <li>With integrations you or your admin enable (webhooks, Slack, cloud export destinations)</li>
        <li>When required by law, regulation, or valid legal process</li>
        <li>To protect rights, safety, and security of users, patients, staff, or the Service</li>
      </ul>
      <p>We do not sell personal information.</p>

      <h2 className="mt-8 text-xl font-semibold text-gray-900 dark:text-gray-100">6. Retention</h2>
      <p>
        We retain data while accounts are active and as needed to provide the Service, honor share-link and
        audit requirements, and meet legal or clinical record-keeping rules that apply to {operatorName}.
        Deleted documents may remain in trash for a configured period before permanent removal. Analytics and
        login logs are retained according to administrator settings and internal policy.
      </p>

      <h2 className="mt-8 text-xl font-semibold text-gray-900 dark:text-gray-100">7. Security</h2>
      <p>
        We use administrative, technical, and organizational measures appropriate to a confidential document
        platform (access controls, encrypted credentials, tokenized file URLs, HTTPS, optional virus scanning).
        No system is completely secure; report suspected incidents to{' '}
        <a className="text-primary underline" href={`mailto:${contactEmail}`}>{contactEmail}</a>.
      </p>

      <h2 className="mt-8 text-xl font-semibold text-gray-900 dark:text-gray-100">8. International transfers</h2>
      <p>
        Data is primarily stored in the region where {operatorName} hosts the Service (e.g., within the Kingdom
        of Saudi Arabia if deployed there). Transfers to cloud import providers occur only when you use those
        features.
      </p>

      <h2 className="mt-8 text-xl font-semibold text-gray-900 dark:text-gray-100">9. Your rights and data deletion</h2>
      <p>
        Depending on applicable law (including the Saudi Personal Data Protection Law (PDPL) or GDPR where
        relevant), you may have rights to access, correct, delete, restrict, or object to certain processing,
        and to lodge a complaint with a supervisory authority.
      </p>
      <ul className="list-disc space-y-2 pl-6">
        <li>
          <strong>Organization users:</strong> Contact your {operatorName} administrator for account changes
          or deletion. Administrators can deactivate accounts and remove documents according to internal policy.
        </li>
        <li>
          <strong>External viewers:</strong> Email{' '}
          <a className="text-primary underline" href={`mailto:${contactEmail}`}>{contactEmail}</a> with the
          share link or your email address used on the link so we can locate related viewer records.
        </li>
        <li>
          <strong>Google connection:</strong> Disconnect in app settings or via Google Account permissions (see
          Section 2.5).
        </li>
      </ul>
      <p>
        We will respond to verified requests within the timeframes required by applicable law, typically within
        30 days unless extension is permitted.
      </p>

      <h2 className="mt-8 text-xl font-semibold text-gray-900 dark:text-gray-100">10. Children</h2>
      <p>
        The Service is intended for professional and organizational use. It is not directed at children under
        the age required by local law to consent to data processing without parental involvement.
      </p>

      <h2 className="mt-8 text-xl font-semibold text-gray-900 dark:text-gray-100">11. Changes</h2>
      <p>
        We may update this Privacy Policy. We will revise the &quot;Last updated&quot; date when we do.
        Material changes may be communicated through the Service or by your organization.
      </p>

      <h2 className="mt-8 text-xl font-semibold text-gray-900 dark:text-gray-100">12. Contact</h2>
      <p>
        Privacy inquiries and requests:
        <br />
        <strong>{operatorName}</strong>
        <br />
        Email: <a className="text-primary underline" href={`mailto:${contactEmail}`}>{contactEmail}</a>
      </p>
    </>
  );
}
