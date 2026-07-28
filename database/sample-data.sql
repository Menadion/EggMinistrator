-- Optional development data for EggMinistrator.
-- Import schema.sql first, then import this file into the eggministrator database.

USE `eggministrator`;

INSERT INTO `users` (`full_name`, `username`, `password_hash`, `role`)
VALUES
    ('System Administrator', 'admin', '$2y$10$92IXUNpkjO0rOQ5byMi.Ye4oKoEa3Ro9llC/.og/at2uheWG/igi', 'admin'),
    ('Sample Inspector', 'inspector', '$2y$10$92IXUNpkjO0rOQ5byMi.Ye4oKoEa3Ro9llC/.og/at2uheWG/igi', 'inspector');

-- Update these thresholds if LH Deli uses a different grading standard.
INSERT INTO `size_grades` (`code`, `label`, `minimum_weight_g`, `maximum_weight_g`, `display_order`)
VALUES
    ('SMALL', 'Small', 0.00, 46.99, 1),
    ('MEDIUM', 'Medium', 47.00, 53.99, 2),
    ('LARGE', 'Large', 54.00, 60.99, 3),
    ('EXTRA_LARGE', 'Extra Large', 61.00, 67.99, 4),
    ('JUMBO', 'Jumbo', 68.00, NULL, 5);

INSERT INTO `inspection_batches` (`batch_code`, `source_name`, `notes`, `started_at`, `created_by_user_id`)
VALUES
    ('DEMO-20260725-A', 'Demo Farm', 'Sample records only; safe to delete.', '2026-07-25 08:00:00', 2);

INSERT INTO `egg_inspections` (
    `inspection_code`, `batch_id`, `sequence_number`, `captured_at`, `weight_g`,
    `size_grade_id`, `ai_disposition`, `final_disposition`, `final_grade`
)
VALUES
    ('7e37003d-8c59-4ea7-bf9f-efcdaeb3cc01', 1, 1, '2026-07-25 08:05:00', 58.20, 3, 'accepted', 'accepted', 'Large'),
    ('7e37003d-8c59-4ea7-bf9f-efcdaeb3cc02', 1, 2, '2026-07-25 08:06:00', 62.40, 4, 'rejected', 'rejected', 'Extra Large'),
    ('7e37003d-8c59-4ea7-bf9f-efcdaeb3cc03', 1, 3, '2026-07-25 08:07:00', 50.80, 2, 'review', 'accepted', 'Medium');

INSERT INTO `ai_assessments` (
    `inspection_id`, `assessment_type`, `result_label`, `confidence_score`,
    `is_defect_detected`, `model_name`, `model_version`, `inference_time_ms`, `assessed_at`
)
VALUES
    (1, 'candling', 'normal', 0.9540, 0, 'candling-classifier', '0.1.0', 207, '2026-07-25 08:05:03'),
    (1, 'candling', 'normal', 0.9760, 0, 'candling-classifier', '0.2.0', 196, '2026-07-25 08:05:05'),
    (2, 'candling', 'large_crack', 0.9910, 1, 'candling-classifier', '0.2.0', 203, '2026-07-25 08:06:03'),
    (3, 'candling', 'normal', 0.6830, 0, 'candling-classifier', '0.2.0', 204, '2026-07-25 08:07:03');

INSERT INTO `staff_overrides` (
    `inspection_id`, `user_id`, `previous_disposition`, `new_disposition`,
    `previous_grade`, `new_grade`, `reason`, `created_at`
)
VALUES
    (3, 2, 'review', 'accepted', NULL, 'Medium', 'Visual check confirmed minor, non-defective shell variation.', '2026-07-25 08:08:00');

UPDATE `egg_inspections`
SET `is_overridden` = 1
WHERE `id` = 3;
