/** @param {Array<{ id: string, required?: boolean }> | undefined} signerFields */
export function areAllRequiredSignerFieldsFilled(signerFields, fieldValues) {
  const required = (signerFields ?? []).filter((f) => f.required);
  if (required.length === 0) {
    return true;
  }
  return required.every((f) => {
    const value = fieldValues[f.id];
    return value != null && String(value).trim() !== '';
  });
}

/** Build submit payload for the signer's fields only (ULID string ids). */
export function buildSubmitFieldsPayload(signerFields, fieldValues) {
  return (signerFields ?? [])
    .filter((f) => {
      const value = fieldValues[f.id];
      return value != null && String(value).trim() !== '';
    })
    .map((f) => ({
      field_id: String(f.id),
      value: fieldValues[f.id],
    }));
}

export function isSubmitDisabled({ canSign, signerFields, fieldValues }) {
  if (!canSign) {
    return true;
  }
  return !areAllRequiredSignerFieldsFilled(signerFields, fieldValues);
}
