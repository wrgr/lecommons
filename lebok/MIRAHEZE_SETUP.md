# LEBOK on Miraheze — click-by-click setup

This guide takes LEBOK from nothing to a moderated public MediaWiki at
**lebok.lecommons.org**, hosted free on [Miraheze](https://meta.miraheze.org)
(a donation-funded nonprofit wiki farm run by the WikiTide Foundation).
Total cost: $0. Your time: ~30 minutes of clicking, spread over a few days
of waiting for approvals.

Paste-ready page content lives in [`skeleton/`](skeleton/) — one `.wikitext`
file per page, in plain MediaWiki markup that renders on a stock install.

## What you'll end up with

- A real MediaWiki at `lebok.miraheze.org`, then at `lebok.lecommons.org`
- **Moderation queue**: anyone can propose an edit; nothing publishes until
  you (or an editor you trust) approve it
- VisualEditor enabled, so educators can contribute without learning wikitext
- Seeded structure: Main Page, Knowledge Areas index, a worked example KA,
  contributor guidelines
- An exit ramp: periodic XML dumps committed to `wrgr/lebok`, importable
  into any self-hosted MediaWiki later

## 1. Create your account

1. Go to <https://meta.miraheze.org/wiki/Special:CreateAccount>
2. Confirm your email (required before you can request a wiki).

## 2. Request the wiki

Go to <https://meta.miraheze.org/wiki/Special:RequestWiki> and fill in:

| Field | Value |
|---|---|
| Subdomain | `lebok` (→ lebok.miraheze.org) |
| Sitename | `LEBOK – Learning Engineering Body of Knowledge` |
| Language | English |
| Category | Education |
| Private | **No** — public wiki |
| License | CC BY-SA 4.0 (standard for public wikis; use CC BY 4.0 if ICICLE prefers attribution-only) |

Purpose / description — paste-ready text (a clear purpose speeds up
volunteer approval):

> LEBOK is the Learning Engineering Body of Knowledge: a public,
> community-maintained reference wiki for the discipline of learning
> engineering, organized into knowledge areas (instructional strategy
> design, learning experience design, evaluation and continuous
> improvement, research methods, and others). It is part of the Learning
> Engineering Commons (lecommons.org) and aligned with the IEEE ICICLE
> community's work toward professional standards. Public contributions
> will go through a moderation queue (Moderation extension) with
> editorial review before anything publishes. Content will be openly
> licensed.

Approval is by volunteer wiki creators — typically a few hours to two days.
You'll get an email; the wiki appears at `https://lebok.miraheze.org`.

## 3. First-visit configuration

On your new wiki (you are automatically the bureaucrat/admin):

1. `Special:ManageWiki/settings` — set the timezone, tagline, and logo
   (any square PNG works to start; the Commons logo is fine as a placeholder).
2. Optional but smart: make a second trusted person an admin early
   (`Special:UserRights` → enter their username → add `Administrator`).
   One-person wikis stall when that person gets busy.

## 4. Enable extensions

`Special:ManageWiki/extensions` — tick these, then save:

- **Moderation** — the load-bearing one. Every edit by a non-trusted user
  goes to a review queue instead of publishing.
- **VisualEditor** — WYSIWYG editing; the single biggest friction-remover
  for non-wiki-native contributors.
- **Cite** — `<ref>` footnotes, needed for an evidence-grounded BoK.
- **CategoryTree** — browsable category hierarchy for the KA structure.

If Moderation is ever unavailable, **FlaggedRevs** is the fallback (drafts
are public-but-flagged until reviewed; more knobs, same goal).

### How the Moderation queue works day-to-day

- New/anonymous users edit → the edit lands at `Special:Moderation`,
  invisible to readers. You get to it whenever; approve or reject with
  one click each.
- Admins skip the queue by default, so your own seeding edits publish
  immediately. (If your edits ever queue, add yourself to the
  `automoderated` group via `Special:UserRights`.)
- When a contributor proves reliable, grant them `automoderated` (their
  edits skip review) and/or `moderator` (they can approve others).

## 5. Permissions: require login to edit (recommended)

Anonymous-IP edits are where wiki spam comes from, and the queue catches it
anyway — but requiring login keeps the queue clean and every edit attributed:

1. `Special:ManageWiki/permissions/*` (the `*` group = logged-out users)
2. Untick `edit`; save. Reading stays open to everyone; account creation
   stays open; logged-in users' edits still go through Moderation until
   you trust them.

## 6. Seed the content

Paste the files from [`skeleton/`](skeleton/) in this order. To create a
page: search its exact title → click the red "create this page" link →
switch to source editing (`</>` icon if VisualEditor opens) → paste →
save. The `<!-- ... -->` headers in each file are wikitext comments and
won't render — leave them in as provenance.

| Create page titled | Paste |
|---|---|
| `Main Page` (exists — edit it) | `skeleton/Main_Page.wikitext` |
| `Knowledge Areas` | `skeleton/Knowledge_Areas.wikitext` |
| `KA10: Evaluation and Continuous Improvement` | `skeleton/KA10_Evaluation_and_Continuous_Improvement.wikitext` |
| `LEBOK:Contributing` | `skeleton/Contributing.wikitext` |

For each further KA, copy `skeleton/KA_page_template.wikitext` into a page
titled `KA<n>: <Name>` and fill in the marked sections. Knowledge-area
names used in the skeleton (KA5, KA6, KA10, KA11) come from the ICICLE
working-draft numbering already cited in the Commons corpus; the rest are
left as placeholders for the working group to confirm — don't invent them.

## 7. Custom domain: lebok.lecommons.org

Do this after the wiki is approved and seeded (it works fine at
lebok.miraheze.org meanwhile, and old URLs redirect after the switch).

1. Read <https://meta.miraheze.org/wiki/Custom_domains> first and confirm
   the current CNAME target. **Heads-up:** that page was unreachable from
   the environment this guide was written in (their CDN blocks
   cloud-datacenter IPs), so verify rather than trust this guide — the
   documented target has been `mw-lb.wikitide.net` (older docs:
   `mw-lb.miraheze.org`).
2. Squarespace: **Settings → Domains → lecommons.org → DNS settings →
   Add record**: type `CNAME`, host `lebok`, value = the target from
   step 1.
3. Submit the custom-domain/SSL request via the link on that same
   Custom domains page (currently a ticket on their issue tracker). Their
   volunteer SRE team issues the Let's Encrypt certificate — usually a few
   days.
4. When `https://lebok.lecommons.org` loads, you're done.

## 8. Keep it alive, keep it backed up

- **Dormancy policy**: Miraheze flags wikis with no edits for ~45–60 days
  and may close them around 6 months idle. Either of these handles it:
  ongoing standards-work edits (likely anyway), or request an inactivity
  exemption from the Stewards once the wiki has real content — reference
  wikis routinely get one.
- **Backups / exit ramp**: `Special:DataDump` → generate an XML dump every
  month or so → commit it to the `wrgr/lebok` GitHub repo. That dump plus
  `Special:Export` is everything needed to re-home LEBOK on a self-hosted
  MediaWiki later; the move is an import plus a DNS change.

## 9. Flip the Commons links

The Commons site currently points its LEBOK links at
`github.com/wrgr/lebok` as a placeholder. Once the wiki is live (either
URL), tell Claude in a session on this repo and it will flip the NavBar,
footer, homepage card, about page, and READMEs to the wiki URL in one pass.
