-- Optional development data for EggMinistrator.
-- Import schema.sql first, then import this file into the eggministrator database.

USE `eggministrator`;

INSERT INTO `users` (`full_name`, `username`, `password_hash`, `role`)
VALUES
    ('System Administrator', 'admin', '$2y$10$92IXUNpkjO0rOQ5byMi.Ye4oKoEa3Ro9llC/.og/at2uheWG/igi', 'admin'),
    ('Sample Inspector', 'inspector', '$2y$10$92IXUNpkjO0rOQ5byMi.Ye4oKoEa3Ro9llC/.og/at2uheWG/igi', 'inspector');

-- PNS/BAFS 321:2021 weight bands: lower bound inclusive, upper bound exclusive.
INSERT INTO `size_grades` (`code`, `label`, `minimum_weight_g`, `maximum_weight_g`, `display_order`)
VALUES
    ('PEWEE',       'Pewee',        0.00, 45.00, 1),
    ('SMALL',       'Small',       45.00, 55.00, 2),
    ('MEDIUM',      'Medium',      55.00, 60.00, 3),
    ('LARGE',       'Large',       60.00, 65.00, 4),
    ('EXTRA_LARGE', 'Extra Large', 65.00, 70.00, 5),
    ('JUMBO',       'Jumbo',       70.00,  NULL, 6);

INSERT INTO `inspection_batches` (`batch_code`, `source_name`, `notes`, `started_at`, `created_by_user_id`)
VALUES
    ('DEMO-20260725-A', 'Demo Farm', 'Sample records only; safe to delete.', '2026-07-25 08:00:00', 2);

INSERT INTO `egg_inspections` (
    `inspection_code`, `batch_id`, `sequence_number`, `captured_at`, `weight_g`,
    `size_grade_id`, `ai_disposition`, `final_disposition`, `final_grade`
)
VALUES
    ('7e37003d-8c59-4ea7-bf9f-efcdaeb3cc01', 1, 1, '2026-07-25 08:05:00', 58.20, 3, 'accepted', 'accepted', 'Medium'),
    ('7e37003d-8c59-4ea7-bf9f-efcdaeb3cc02', 1, 2, '2026-07-25 08:06:00', 62.40, 4, 'rejected', 'rejected', 'Large'),
    ('7e37003d-8c59-4ea7-bf9f-efcdaeb3cc03', 1, 3, '2026-07-25 08:07:00', 50.80, 2, 'review', 'accepted', 'Small'),
    ('7e37003d-8c59-4ea7-bf9f-efcdaeb3cc04', 1, 4, '2026-07-25 08:08:00', NULL, NULL, 'no_egg', 'no_egg', NULL);

INSERT INTO `ai_assessments` (
    `inspection_id`, `assessment_type`, `result_label`, `confidence_score`,
    `is_defect_detected`, `model_name`, `model_version`, `inference_time_ms`, `assessed_at`
)
VALUES
    (1, 'candling', 'good', 0.9760, 0, 'candling-classifier', '0.2.0', 196, '2026-07-25 08:05:05'),
    (2, 'candling', 'defective', 0.9910, 1, 'candling-classifier', '0.2.0', 203, '2026-07-25 08:06:03'),
    (3, 'candling', 'good', 0.6830, 0, 'candling-classifier', '0.2.0', 204, '2026-07-25 08:07:03'),
    (4, 'candling', 'not_an_egg', 0.9990, 0, 'candling-classifier', '0.2.0', 105, '2026-07-25 08:08:03');

INSERT INTO `staff_overrides` (
    `inspection_id`, `user_id`, `previous_disposition`, `new_disposition`,
    `previous_grade`, `new_grade`, `reason`, `created_at`
)
VALUES
    (3, 2, 'review', 'accepted', NULL, 'Small', 'Visual check confirmed minor, non-defective shell variation.', '2026-07-25 08:09:00');

UPDATE `egg_inspections`
SET `is_overridden` = 1
WHERE `id` = 3;
