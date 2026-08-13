-- Adds a full simulated inspection day after the original small July 25 sample.
-- Safe to run once; it creates a separate batch only when it does not already exist.

USE `eggministrator`;

DROP PROCEDURE IF EXISTS `extend_demo_data_through_july_25`;

DELIMITER //

CREATE PROCEDURE `extend_demo_data_through_july_25`()
BEGIN
    DECLARE batch_id_value BIGINT UNSIGNED;
    DECLARE inspection_id_value BIGINT UNSIGNED;
    DECLARE sequence_value INT UNSIGNED DEFAULT 1;
    DECLARE size_grade_id_value TINYINT UNSIGNED;
    DECLARE weight_value DECIMAL(6,2);
    DECLARE grade_label_value VARCHAR(50);
    DECLARE result_label_value VARCHAR(20);
    DECLARE captured_at_value DATETIME;

    IF NOT EXISTS (SELECT 1 FROM `inspection_batches` WHERE `batch_code` = 'DEMO-20260725-B') THEN
        INSERT INTO `inspection_batches` (`batch_code`, `source_name`, `notes`, `started_at`, `created_by_user_id`)
        VALUES (
            'DEMO-20260725-B',
            'Demo Farm',
            'Full generated day added after the initial July 25 sample.',
            '2026-07-25 08:10:00',
            (SELECT `id` FROM `users` WHERE `username` = 'admin' LIMIT 1)
        );

        SET batch_id_value = LAST_INSERT_ID();

        WHILE sequence_value <= 32 DO
            SET size_grade_id_value = CASE
                WHEN MOD(sequence_value * 17 + batch_id_value * 31, 100) < 8 THEN 1
                WHEN MOD(sequence_value * 17 + batch_id_value * 31, 100) < 25 THEN 2
                WHEN MOD(sequence_value * 17 + batch_id_value * 31, 100) < 51 THEN 3
                WHEN MOD(sequence_value * 17 + batch_id_value * 31, 100) < 79 THEN 4
                WHEN MOD(sequence_value * 17 + batch_id_value * 31, 100) < 94 THEN 5
                ELSE 6
            END;
            SET weight_value = CASE size_grade_id_value
                WHEN 1 THEN 39.00 + MOD(sequence_value, 55) / 10
                WHEN 2 THEN 45.20 + MOD(sequence_value, 95) / 10
                WHEN 3 THEN 55.10 + MOD(sequence_value, 44) / 10
                WHEN 4 THEN 60.10 + MOD(sequence_value, 44) / 10
                WHEN 5 THEN 65.10 + MOD(sequence_value, 44) / 10
                ELSE 70.00 + MOD(sequence_value, 130) / 10
            END;
            SELECT `label` INTO grade_label_value FROM `size_grades` WHERE `id` = size_grade_id_value;
            SET result_label_value = IF(MOD(sequence_value, 8) = 0, 'defective', 'good');
            SET captured_at_value = TIMESTAMP('2026-07-25', MAKETIME(8 + MOD(sequence_value, 9), MOD(sequence_value * 7, 60), MOD(sequence_value * 11, 60)));

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
                'candling-classifier', '0.2.0-demo', 145 + MOD(sequence_value, 75),
                DATE_ADD(captured_at_value, INTERVAL 2 SECOND)
            );

            SET sequence_value = sequence_value + 1;
        END WHILE;
    END IF;
END//

DELIMITER ;

CALL `extend_demo_data_through_july_25`();
DROP PROCEDURE `extend_demo_data_through_july_25`;
