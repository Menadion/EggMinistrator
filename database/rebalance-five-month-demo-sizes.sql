-- Rebalances the existing five-month development dataset after it was seeded.
-- It updates only batches created by seed-five-month-demo-data.sql.

USE `eggministrator`;

UPDATE `egg_inspections` AS `inspections`
INNER JOIN `inspection_batches` AS `batches` ON `batches`.`id` = `inspections`.`batch_id`
SET `inspections`.`size_grade_id` = CASE
    WHEN MOD(`inspections`.`sequence_number` * 17 + `inspections`.`batch_id` * 31, 100) < 8 THEN 1
    WHEN MOD(`inspections`.`sequence_number` * 17 + `inspections`.`batch_id` * 31, 100) < 25 THEN 2
    WHEN MOD(`inspections`.`sequence_number` * 17 + `inspections`.`batch_id` * 31, 100) < 51 THEN 3
    WHEN MOD(`inspections`.`sequence_number` * 17 + `inspections`.`batch_id` * 31, 100) < 79 THEN 4
    WHEN MOD(`inspections`.`sequence_number` * 17 + `inspections`.`batch_id` * 31, 100) < 94 THEN 5
    ELSE 6
END
WHERE `batches`.`notes` = 'Five-month generated development dataset; safe to delete.'
  AND `inspections`.`final_disposition` <> 'no_egg';

UPDATE `egg_inspections` AS `inspections`
INNER JOIN `inspection_batches` AS `batches` ON `batches`.`id` = `inspections`.`batch_id`
SET `inspections`.`weight_g` = CASE `inspections`.`size_grade_id`
    WHEN 1 THEN 39.00 + MOD(`inspections`.`sequence_number`, 55) / 10
    WHEN 2 THEN 45.20 + MOD(`inspections`.`sequence_number`, 95) / 10
    WHEN 3 THEN 55.10 + MOD(`inspections`.`sequence_number`, 44) / 10
    WHEN 4 THEN 60.10 + MOD(`inspections`.`sequence_number`, 44) / 10
    WHEN 5 THEN 65.10 + MOD(`inspections`.`sequence_number`, 44) / 10
    ELSE 70.00 + MOD(`inspections`.`sequence_number`, 130) / 10
END
WHERE `batches`.`notes` = 'Five-month generated development dataset; safe to delete.'
  AND `inspections`.`final_disposition` <> 'no_egg';

UPDATE `egg_inspections` AS `inspections`
INNER JOIN `inspection_batches` AS `batches` ON `batches`.`id` = `inspections`.`batch_id`
INNER JOIN `size_grades` AS `grades` ON `grades`.`id` = `inspections`.`size_grade_id`
SET `inspections`.`final_grade` = `grades`.`label`
WHERE `batches`.`notes` = 'Five-month generated development dataset; safe to delete.'
  AND `inspections`.`final_disposition` <> 'no_egg';
