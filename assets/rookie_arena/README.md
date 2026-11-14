Templates derived from the user's twelve Rookie Arena screenshots.
Coordinates use the game client only, resized to 1280 x 720; the 30 pixel
Windows title bar and one pixel side/bottom borders were excluded.

The full client references are retained in tests/fixtures/rookie_arena.
Reference 10 was a cropped flags counter and is not a complete screen fixture.
Glyph templates cover 0-9 using the header counters, Owned labels, and arena
points; digit 2 comes from the points value 4,216. Zero flags and insufficient
green Owned counts are synthetic tests because those screenshots were not
provided. Red insufficient-resource text is deliberately unknown and must not
authorize a purchase.

RookieArenaVision.observe accepts RGB uint8 [720,1280,3]. Unknown resource
values return None. friendship_available is tri-state: True for the heart
offer, False only for positive cooldown text, None for unrecognized content.
Signature is stable for a roster across small shifts/selection changes by
matching portrait interiors against the previous observed list. Instantiate
one vision object per run. It changes on a materially different roster.

Promotion support uses the centered Confirm control and rank-neutral separator,
then Promotion Rewards title plus Tap to close control. These observations take
priority over the dimmed battle/result background. The return-to-list screenshot
is retained as promoted_list.png and verifies eight flags without reading the
raised purchase plus sign as another digit.

r5 flag OCR uses flagdigit_0 through flagdigit_9 grayscale header references.
At load time these produce multiple thresholded glyph variants. The flags
reader segments by occupied column spans to retain vertically disconnected
strokes and requires noncontradictory readings at multiple thresholds. Currency
Owned OCR continues using only the original digit_* references. flags_five_client
is the regression screenshot for the reported stop after three battles.

Auto state requires a visible control layout. auto_check is the common white
checkmark and blue base cropped from reference 06 at x994:1014, y691:706.
Four repeated checkmarks with blue bases confirm auto, independently of the
rotating A icon. Three large gold skill-frame edges plus the idle A confirm
manual. Hidden control layouts remain unknown. manual_latest_client is the
reported manual battle client, cropped from the user's latest screenshot;
opening_animation is the actual r5 diagnostic capture with hidden controls.
