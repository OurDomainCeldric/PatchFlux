/**
 * Operator / legal-identity configuration.
 *
 * This is the **single source of truth** for personal-identity fields that
 * appear in the imprint (Impressum) and privacy notice (Datenschutzerklärung).
 *
 * German law requires the following information to be shown on every public
 * telemedia service that is more than a purely private family page:
 *   - §  5  DDG (formerly § 5 TMG) — imprint obligation
 *   - § 18 Abs. 2 MStV — editorially responsible person for journalistic content
 *   - Art. 13 DSGVO — controller identity in the privacy notice
 *
 * Until the fields marked `PENDING` are filled in with the operator's real
 * legal name, postal address, email and so on, the imprint + privacy pages
 * will render a visible red banner warning that the site is NOT ready for
 * public promotion. The {@link isOperatorConfigComplete} helper drives that
 * banner.
 *
 * Replace every `PENDING_*` value with the real data before linking the
 * domain from Search Console, social media, or any third-party aggregator.
 */

/** Sentinel used for placeholder values so they are easy to grep and detect. */
export const PENDING_MARKER = "PENDING_FILL_IN_BEFORE_PUBLIC_LAUNCH" as const;

export interface OperatorConfig {
  /** Full legal name of the natural person operating the site. */
  fullName: string;
  /** Street + house number. */
  street: string;
  /** Postal code + city. */
  postalCode: string;
  city: string;
  /** ISO country name (matches the imprint language). */
  country: string;
  /** Primary contact email address (displayed + mailto). */
  contactEmail: string;
  /**
   * Second quick-contact channel required by § 5 DDG. A clearly distinct
   * email address (e.g. for legal/takedown matters) satisfies recent case
   * law when it is staffed and answered promptly.
   */
  secondContactEmail: string;
  /**
   * VAT ID (Umsatzsteuer-Identifikationsnummer) — only required if the
   * operator is a business. Leave empty for a non-commercial private site.
   */
  vatId: string;
  /**
   * Person responsible for journalistic-editorial content under § 18
   * Abs. 2 MStV. For a single-operator site this is usually identical to
   * the operator — set to the same full name + address.
   */
  mstvResponsibleName: string;
  mstvResponsibleAddress: string;
}

/**
 * Current operator details. Any field equal to {@link PENDING_MARKER} is
 * treated as "not yet filled in" by {@link isOperatorConfigComplete}.
 *
 * SECURITY / LEGAL: do not commit fake names or placeholder addresses that
 * look real — using a made-up identity on a public imprint is itself a
 * violation (Irreführung, § 5 UWG + § 5 DDG). Keep the ``PENDING_MARKER``
 * until the real values are known.
 */
export const operator: OperatorConfig = {
  fullName: "René Omlor",
  street: "Zinzendorfstraße 3",
  postalCode: "01069",
  city: "Dresden",
  country: "Deutschland",
  contactEmail: "contact@patchflux.de",
  secondContactEmail: "legal@patchflux.de",
  vatId: "",
  mstvResponsibleName: "René Omlor",
  mstvResponsibleAddress: "Zinzendorfstraße 3, 01069 Dresden, Deutschland",
};

/**
 * Returns true only when all legally required identity fields carry real
 * (non-placeholder) values. The imprint + privacy pages render a warning
 * banner while this returns false.
 */
export function isOperatorConfigComplete(cfg: OperatorConfig = operator): boolean {
  const required: Array<keyof OperatorConfig> = [
    "fullName",
    "street",
    "postalCode",
    "city",
    "country",
    "contactEmail",
    "secondContactEmail",
    "mstvResponsibleName",
    "mstvResponsibleAddress",
  ];
  return required.every((key) => {
    const value = cfg[key];
    return typeof value === "string" && value.length > 0 && value !== PENDING_MARKER;
  });
}

/**
 * Human-readable display for a placeholder field. Keeps UI output consistent.
 */
export function displayValue(value: string): string {
  return value === PENDING_MARKER ? "[noch einzutragen / to be filled in]" : value;
}
