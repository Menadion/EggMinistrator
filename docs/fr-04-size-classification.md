# FR-04: Weight-Based Size Classification

Spec for the egg size grading requirement and the database change it needs.

**Paper reference:** FR-04 in the Requirements table (§3.2.3), with the size class table added
directly beneath it. Also appears as an In Scope item ("Weight-based egg size classification") in
both §Scope and §3.2.6 Preliminary Scope Statement.

**Standard:** PNS/BAFS 321:2021, *Shell Eggs (Chicken and Duck) Product Standard: Classification
and Grading*, issued by the Bureau of Agriculture and Fisheries Standards.
[Official PDF](http://www.bafs.da.gov.ph/bafs_admin/admin_page/pns_file/PNS%20Shell%20Eggs%20(Chicken%20and%20Duck)%20-%20Product%20Standard%20-%20Classification%20and%20Grading.pdf)

---

## ⚠️ Verify before this ships

Three things are unconfirmed against the actual standard. All three are cheap to check and all
three are the kind of thing a panel can ask about directly.

1. **Six classes or seven.** Sources disagree. Every source that names the classes lists the six
   below, but at least one states the standard defines seven. The seventh is most likely a duck
   egg class, since the standard covers chicken and duck. Confirm which table applies to LH Deli's
   product.
2. **Spelling is "Pewee."** The standard uses Pewee. `dashboard/src/data/mockData.js` currently
   says "Peewee." Match the standard.
3. **Boundary treatment.** The standard is written in whole grams (for example, extra large as
   65 to 69, jumbo as 70 and above). The load cell reports decimals, so a 69.4 g egg falls in a
   gap between bands written that way. Implement continuous boundaries, see below.

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
six values as the seed data above, with the Pewee spelling corrected.

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
