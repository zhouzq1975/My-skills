# Campaign brief

Use this reference when adding, replacing, or scheduling a weekly campaign.

## Required fields

- Restaurant display name in Chinese, English, and German where they differ.
- Existing restaurant slug and exact coupon ID.
- Offer value and scope, such as all dishes, selected noodles, or one gift chosen from two alternatives.
- Popup display start and end in `Europe/Berlin`.
- Coupon validity period, which may differ from the popup window.
- Redemption restrictions: minimum spend, cash-only, excluded drinks, stock limits, branch restrictions, or other material conditions.
- Short address without postcode plus neighbourhood.
- Source imagery, logo, menu, or official restaurant page available for visual work.

## Eligibility mode

Choose one deliberately:

- `standard`: claimed users no longer see the campaign.
- `urgent-after-claim`: claimed users may still see it during a clearly defined final-use window. Use only when explicitly requested, such as an expiring coupon reminder.

Multiple simultaneous promotions must remain separate campaign objects and separate popup designs. Define selection order or priority so they are not rendered as one combined chooser and do not open on top of each other.

## Time handling

Translate local dates to exact UTC timestamps with daylight-saving time accounted for. Treat the end as exclusive. Test one millisecond before start, at start, one millisecond before end, and at end.

Before releasing, verify that:

- The coupon belongs to the intended restaurant or eligible merchant set.
- The coupon will be claimable throughout the popup display window.
- The restaurant and coupon routes resolve.
- Copy does not promise more than the coupon actually grants.
