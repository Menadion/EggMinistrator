-- Development-only MariaDB seed data for a realistic five-month dashboard demo.
-- Import schema.sql and sample-data.sql first. This script is idempotent: it runs once per database.

USE `eggministrator`;

DROP PROCEDURE IF EXISTS `seed_five_month_demo_data`;

DELIMITER //

CREATE PROCEDURE `seed_five_month_demo_data`()
BEGIN
    DECLARE current_date_value DATE DEFAULT '2026-03-01';
    DECLARE end_date_value DATE DEFAULT '2026-07-25';
    DECLARE batch_code_value VARCHAR(50);
    DECLARE batch_id_value BIGINT UNSIGNED;
    DECLARE inspection_id_value BIGINT UNSIGNED;
    DECLARE sequence_value INT UNSIGNED DEFAULT 0;
    DECLARE day_offset INT DEFAULT 0;
    DECLARE egg_index INT DEFAULT 0;
    DECLARE daily_total INT DEFAULT 0;
    DECLARE generated_number INT DEFAULT 0;
    DECLARE size_grade_id_value TINYINT UNSIGNED;
    DECLARE weight_value DECIMAL(6,2);
    DECLARE grade_label_value VARCHAR(50);
    DECLARE result_label_value VARCHAR(20);
    DECLARE captured_at_value DATETIME;

    IF NOT EXISTS (
        SELECT 1 FROM `inspection_batches` WHERE `batch_code` = 'DEMO-202603-A'
    ) THEN
        WHILE current_date_value <= end_date_value DO
            IF DAY(current_date_value) = 1 THEN
                SET batch_code_value = CONCAT('DEMO-', DATE_FORMAT(current_date_value, '%Y%m'), '-A');

                INSERT INTO `inspection_batches` (`batch_code`, `source_name`, `notes`, `started_at`, `created_by_user_id`)
                VALUES (
                    batch_code_value,
                    'Demo Farm',
                    'Five-month generated development dataset; safe to delete.',
                    current_date_value,
                    (SELECT `id` FROM `users` WHERE `username` = 'admin' LIMIT 1)
                );

                SELECT `id` INTO batch_id_value
                FROM `inspection_batches`
                WHERE `batch_code` = batch_code_value;

                SET sequence_value = 0;
            END IF;

            SET daily_total = 28 + MOD(day_offset * 7, 17);
            SET egg_index = 1;

            WHILE egg_index <= daily_total DO
                SET sequence_value = sequence_value + 1;
                SET generated_number = day_offset * 50 + egg_index;
                SET captured_at_value = TIMESTAMP(
                    current_date_value,
                    MAKETIME(8 + MOD(egg_index, 9), MOD(egg_index * 7, 60), MOD(generated_number * 11, 60))
                );

                IF MOD(generated_number, 53) = 0 THEN
                    INSERT INTO `egg_inspections` (
                        `inspection_code`, `batch_id`, `sequence_number`, `station_name`, `captured_at`,
                        `weight_g`, `size_grade_id`, `ai_disposition`, `final_disposition`, `final_grade`
                    ) VALUES (
                        UUID(), batch_id_value, sequence_value, 'Station 1', captured_at_value,
                        NULL, NULL, 'no_egg', 'no_egg', NULL
                    );

                    SET inspection_id_value = LAST_INSERT_ID();

                    INSERT INTO `ai_assessments` (
                        `inspection_id`, `assessment_type`, `result_label`, `confidence_score`,
                        `is_defect_detected`, `model_name`, `model_version`, `inference_time_ms`, `assessed_at`
                    ) VALUES (
                        inspection_id_value, 'candling', 'not_an_egg', 0.9950,
                        0, 'candling-classifier', '0.2.0-demo', 92, DATE_ADD(captured_at_value, INTERVAL 2 SECOND)
                    );
                ELSE
                    SET size_grade_id_value = CASE
                        WHEN MOD(generated_number, 100) < 8 THEN 1
                        WHEN MOD(generated_number, 100) < 25 THEN 2
                        WHEN MOD(generated_number, 100) < 51 THEN 3
                        WHEN MOD(generated_number, 100) < 79 THEN 4
                        WHEN MOD(generated_number, 100) < 94 THEN 5
                        ELSE 6
                    END;
                    SET weight_value = CASE size_grade_id_value
                        WHEN 1 THEN 39.00 + MOD(generated_number, 55) / 10
                        WHEN 2 THEN 45.20 + MOD(generated_number, 95) / 10
                        WHEN 3 THEN 55.10 + MOD(generated_number, 44) / 10
                        WHEN 4 THEN 60.10 + MOD(generated_number, 44) / 10
                        WHEN 5 THEN 65.10 + MOD(generated_number, 44) / 10
                        ELSE 70.00 + MOD(generated_number, 130) / 10
                    END;

                    SELECT `label` INTO grade_label_value FROM `size_grades` WHERE `id` = size_grade_id_value;
                    SET result_label_value = IF(MOD(generated_number, 8) = 0, 'defective', 'good');

                    INSERT INTO `egg_inspections` (
                        `inspection_code`, `batch_id`, `sequence_number`, `station_name`, `captured_at`,
                        `weight_g`, `size_grade_id`, `ai_disposition`, `final_disposition`, `final_grade`
                    ) VALUES (
                        UUID(), batch_id_value, sequence_value, 'Station 1', captured_at_value,
                        weight_value, size_grade_id_value,
                        IF(result_label_value = 'defective', 'rejected', 'accepted'),
                        IF(result_label_value = 'defective', 'rejected', 'accepted'),
                        grade_label_value
                    );

                    SET inspection_id_value = LAST_INSERT_ID();

                    INSERT INTO `ai_assessments` (
                        `inspection_id`, `assessment_type`, `result_label`, `confidence_score`,
                        `is_defect_detected`, `model_name`, `model_version`, `inference_time_ms`, `assessed_at`
                    ) VALUES (
                        inspection_id_value, 'candling', result_label_value,
                        IF(result_label_value = 'defective', 0.9280, 0.8730),
                        IF(result_label_value = 'defective', 1, 0),
                        'candling-classifier', '0.2.0-demo', 145 + MOD(generated_number, 75),
                        DATE_ADD(captured_at_value, INTERVAL 2 SECOND)
                    );
                END IF;

                SET egg_index = egg_index + 1;
            END WHILE;

            SET current_date_value = DATE_ADD(current_date_value, INTERVAL 1 DAY);
            SET day_offset = day_offset + 1;
        END WHILE;
    END IF;
END//

DELIMITER ;

CALL `seed_five_month_demo_data`();
DROP PROCEDURE `seed_five_month_demo_data`;
