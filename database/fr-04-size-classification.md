# FR-04: Weight-Based Size Classification

Spec for the egg size grading requirement and the database change it needs.

**Paper reference:** FR-04 in the Requirements table (§3.2.3), with the size class table added
directly beneath it. Also appears as an In Scope item ("Weight-based egg size classification") in
both §Scope and §3.2.6 Preliminary Scope Statement.

**Standard:** PNS/BAFS 321:2021, *Shell Eggs (Chicken and Duck) Product Standard: Classification
and Grading*, issued by the Bureau of Agriculture and Fisheries Standards.
[Official PDF](http://www.bafs.da.gov.ph/bafs_admin/admin_page/pns_file/PNS%20Shell%20Eggs%20(Chicken%20and%20Duck)%20-%20Product%20Standard%20-%20Classification%20and%20Grading.pdf)

> **Decision held, 2026-07-29.** A reference operation's grading list (8 tiers plus Dirty and
> Condemn) was reviewed against this and **PNS/BAFS 321:2021 stays as the cited standard.** Reasoning
> is in "The operator list, and why it did not win" below. This is settled; do not reopen it before
> the defense.

---

## Size classes

| Class | Weight |
|---|---|
| Pewee | Under 45 g |
| Small | 45 g to under 55 g |
| Medium | 55 g to under 60 g |
| Large | 60 g to under 65 g |
| Extra Large | 65 g to under 70 g |
| Jumbo | 70 g and above |

Phrased as "to under" rather than "45 to 54" so that every possible weight lands in exactly one
class. This is a restatement of the standard's bands for implementation, not a change to them.

---

## ⚠️ Verify before this ships

Two items, both cheap, both the kind of thing a panel can ask directly.

1. **Six classes or seven.** Sources disagree. Every source naming the classes lists the six above,
   but at least one states the standard defines seven. The seventh is most likely a duck egg class,
   since the standard covers chicken and duck. Confirm which table applies.
2. **Boundary treatment.** The standard is written in whole grams (extra large 65 to 69, jumbo 70
   and above), so a 69.4 g reading from the load cell falls in a gap between bands written that way.
   Implement continuous boundaries, as in the table above.

**Resolved:** the spelling question. A commercial operator's own category list uses **PEEWEE**, and
`dashboard/src/data/mockData.js` already had "Peewee." Both spellings appear in the field. Match the
PNS document's spelling in the paper, and keep whichever the code already uses consistent across the
schema and the dashboard.

---

## The operator list, and why it did not win

A commercial egg producer's Egg Grading Machine sorts into these categories, largest to smallest:

> JUMBO, XTRA LARGE, LARGE, MEDIUM, SMALL, PULLETS, PEEWEE, XTRA PEEWEE, plus **Dirty** and
> **Condemn**

Eight size tiers rather than six. PULLETS and XTRA PEEWEE have no PNS equivalent; both subdivide
what PNS lumps into "Pewee, under 45 g." The top five names match PNS exactly, which suggests the
operator's tiers are a PNS-derived scheme with the small end split further for their own trade.

**Why PNS is kept anyway:**

1. **The operator gave names, not gram ranges.** Eight labels with no boundaries cannot be
   implemented, and no further contact is planned. PNS is fully specified and already seeded.
2. **A national standard is the stronger defense answer.** "Classified per PNS/BAFS 321:2021" beats
   "an operator told us" when a panel asks where the numbers came from.
3. **It is already built.** The schema, the seed data, and the dashboard definitions are specified
   against these six. Rebuilding them against eight undefined tiers costs work and buys nothing.

**Use it as corroboration instead.** The overlap is a genuine strength worth one sentence: the
grading scheme adopted here matches the categories a commercial grading machine actually uses at
the top five tiers, so the system's output is compatible with existing trade practice.

**If asked "why not eight tiers?"** The three sub-45 g tiers separate product below the national
standard's smallest class. They are a commercial sorting distinction, not a quality one, and the
system grades to the national standard. Adding finer tiers is a seed-data change, not a design
change, since `size_grades` is a database table.

### One thing worth taking from the operator list

**Dirty and Condemn are not sizes.** They sit in the operator's list as dispositions, and their
reject handling confirms the split: some rejects are still sold, others are destroyed. An egg has a
size *and* a condition, and mixing the two into one lookup makes them mutually exclusive when they
are not. A dirty egg is still a Large egg.

> [!warning] **SUPERSEDED 2026-07-30. Do not implement the table below.**
> This proposal was written on the condition *"if a disposition field is not already in the
> schema."* **One already exists** — `schema.sql` has `ai_disposition` and `final_disposition`, both
> `ENUM('accepted','rejected','review')`. So the proposal was moot on arrival.
> It is also **unimplementable as written**: `DIRTY` cannot be assigned by the model, because the
> capture is transillumination and cannot show surface dirt (Decision G).
> **The live question is different** — see the `not_an_egg` mapping problem in the brief for
> Ricardo. Kept here only so the reasoning is not re-derived.

| Value | Meaning | Sellable |
|---|---|---|
| `ACCEPTED` | Passed inspection | yes |
| `DIRTY` | Soiled shell | yes, at a discount |
| `CONDEMN` | Destroyed | no |

This also gives **Gap 12** its missing vocabulary: the workflow can end at a recorded disposition
rather than at "result corrected." Flag it to Ricardo alongside the findings in `schema-review.md`.

---

## Database change

`database/schema.sql` already has a `size_grades` table with the right shape. Only the seed data
in `database/sample-data.sql` changes. It currently holds five grades with invented boundaries
(Small starting at 0.00, Jumbo uncapped, no Pewee tier).

Replace the existing `size_grades` insert with:

```sql
INSERT INTO `size_grades` (`code`, `label`, `minimum_weight_g`, `maximum_weight_g`, `display_order`)
VALUES
    ('PEWEE',       'Pewee',        0.00, 45.00, 1),
    ('SMALL',       'Small',       45.00, 55.00, 2),
    ('MEDIUM',      'Medium',      55.00, 60.00, 3),
    ('LARGE',       'Large',       60.00, 65.00, 4),
    ('EXTRA_LARGE', 'Extra Large', 65.00, 70.00, 5),
    ('JUMBO',       'Jumbo',       70.00,  NULL, 6);
```

`minimum_weight_g` is inclusive, `maximum_weight_g` is exclusive, and `NULL` means unbounded.
Grade lookup:

```sql
SELECT `id`, `label`
FROM `size_grades`
WHERE `is_active` = 1
  AND :weight_g >= `minimum_weight_g`
  AND (`maximum_weight_g` IS NULL OR :weight_g < `maximum_weight_g`);
```

## Dashboard change

`dashboard/src/data/mockData.js` declares its own `sizeDefinitions` array with six tiers whose
boundaries do not match the standard (Pewee 30 to 39, Jumbo 68 to 74). It has to carry the same
six values as the seed data above.

The underlying problem is that the grades are declared twice, once in SQL and once in JavaScript.
Once the dashboard reads from MySQL rather than mock data, it should pull `size_grades` from the
database so there is only one definition to keep correct.

---

## Why this exists

FR-04 previously read "assign a size class based on measured weight" with no table behind it.
Nothing defined what the classes were. Two people implemented against that gap independently and
produced different answers: five grades in the schema, six in the dashboard, no shared boundary.
Citing a published standard fixes both files and removes the question of where the numbers came
from.
