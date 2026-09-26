# Reconciliation Rules

## Change Classes

| Class | Meaning | Action |
|---|---|---|
| Existing update | App id exists and branch identity is confirmed | Preserve filename/id; change only supported fields |
| New restaurant | No target match after Place ID, coordinates, name, and address review | Create a new YAML in a separate additions PR |
| Suspected duplicate | Some evidence matches but branch identity is inconclusive | Do not write; report for review |
| Closure | Permanent closure is supported | Preserve file and add `hidden: true` with dated evidence |
| Temporary closure | Branch is expected to reopen | Do not use `hidden: true` solely for temporary closure |
| Replacement | A different business occupies the location | Hide old id and create a new id; never reuse the old file |
| Coupon activate | Target restaurant has a current active, non-expired Pinwo offer | Add `hasDiscount: true` and concise `discountInfo` |
| Coupon deactivate | Target is discounted but no current valid Pinwo offer remains | Set false and delete `discountInfo` |
| Coupon blocked | Coupon merchant has no confirmed target restaurant | Keep out of coupon PR; resolve/add restaurant separately |

## Readiness Is Not Operating Status

`quality.servingReadiness` means the Source Packet can compile. It does not prove that a restaurant is open. Use current `inferred.operating_status` and branch evidence for closures or reopenings.

Valid Source Packet values are `operating`, `temporarily_closed`, and `closed_permanently`. An open new restaurant is `operating` plus `is_new_opening: true`.

## Field Mapping

| App YAML field | Preferred Pinwo source |
|---|---|
| `name.en`, `name.zh`, `name.de` | canonical/seed names and confirmed aliases |
| `address.*` | normalized branch address, split conservatively |
| `latitude`, `longitude` | `identity.geo` |
| `placeId` | confirmed `identity.placeId` only |
| `phone` | confirmed identity contact |
| `tags` | explicit mapping to the target's existing 22 tags |
| `chain.*` | confirmed same-brand branch evidence |
| `hidden` | permanent closure/reopening evidence |
| `hasDiscount`, `discountInfo` | current live Pinwo coupon/merchant data |

Do not copy reviews, menus, ratings, opening hours, search terms, internal notes, or third-party descriptions/images into app YAML.

## Coupon Validity

Treat a coupon as current only when `active === true`, `expiresOn` is a valid `YYYY-MM-DD`, `expiresOn` is not before the current date in `Europe/Berlin`, and the merchant resolves to the intended branch.

Use a fresh export every run. If an offer is extended, re-export after its live expiry is updated. Preserve the exact date in PR evidence.

For multiple coupons on one restaurant, create one truthful summary line. Do not imply coupon conditions can be combined. If compact wording would mislead, leave English empty or request copy review.

## Evidence Tiers

- **Confirmed:** exact target id, exact Place ID, or one unambiguous coordinate/branch match plus current first-party data.
- **Probable:** normalized name and address agree but stable identifier is missing; review manually before writing.
- **Unresolved:** conflicting branch, multiple nearby candidates, missing target restaurant, stale source, or unsupported taxonomy; do not write.
