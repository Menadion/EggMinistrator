-- Audit item 1 (docs/projman/R-Audit.md): `staff_overrides` could not record a
-- `no_egg` correction.
--
-- `egg_inspections.ai_disposition` and `final_disposition` have carried four
-- values since Decision G landed ('accepted', 'rejected', 'review', 'no_egg'),
-- but the override log still carried three. An inspector correcting a wrong
-- `no_egg` verdict had no legal value for the state being corrected away from,
-- so the row could not insert.
--
-- Both columns are widened, not just `previous_disposition`: a staff member may
-- also need to mark a capture as containing no egg when the model got it the
-- other way round.
--
-- Widening an ENUM by appending a member does not rewrite existing rows or
-- invalidate stored values.

USE `eggministrator`;

ALTER TABLE `staff_overrides`
    MODIFY COLUMN `previous_disposition` ENUM('accepted', 'rejected', 'review', 'no_egg') NOT NULL,
    MODIFY COLUMN `new_disposition`      ENUM('accepted', 'rejected', 'review', 'no_egg') NOT NULL;
