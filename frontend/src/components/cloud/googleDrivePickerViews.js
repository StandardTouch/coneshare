/**
 * Google Picker view builders.
 *
 * ViewId.FOLDERS lists folders from every depth in a flat list. Use DocsView with
 * setParent('root') (and optional setOwnedByMe) so navigation stays hierarchical.
 */

export function buildGoogleDriveImportViews(google) {
  const myDriveView = new google.picker.DocsView(google.picker.ViewId.DOCS)
    .setIncludeFolders(true)
    .setParent('root')
    .setOwnedByMe(true);

  const sharedView = new google.picker.DocsView(google.picker.ViewId.DOCS)
    .setIncludeFolders(true)
    .setOwnedByMe(false);

  return { myDriveView, sharedView };
}

/**
 * Destination folder picker for exports — hierarchical My Drive navigation, folder select only.
 */
export function buildGoogleDriveFolderDestinationView(google) {
  return new google.picker.DocsView(google.picker.ViewId.DOCS)
    .setIncludeFolders(true)
    .setSelectFolderEnabled(true)
    .setMimeTypes('application/vnd.google-apps.folder')
    .setParent('root')
    .setOwnedByMe(true);
}
