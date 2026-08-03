-- EggMinistrator canonical MySQL schema.
-- Compatible with MySQL 8.0+ and MariaDB 10.4+ (as included with modern XAMPP).

CREATE DATABASE IF NOT EXISTS `eggministrator`
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE `eggministrator`;

SET FOREIGN_KEY_CHECKS = 0;
DROP VIEW IF EXISTS `daily_inspection_summary`;
DROP TABLE IF EXISTS `password_change_tokens`;
DROP TABLE IF EXISTS `auth_sessions`;
DROP TABLE IF EXISTS `staff_overrides`;
DROP TABLE IF EXISTS `ai_assessments`;
DROP TABLE IF EXISTS `inspection_images`;
DROP TABLE IF EXISTS `egg_inspections`;
DROP TABLE IF EXISTS `inspection_batches`;
DROP TABLE IF EXISTS `size_grades`;
DROP TABLE IF EXISTS `users`;
SET FOREIGN_KEY_CHECKS = 1;

CREATE TABLE `users` (
    `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    `full_name` VARCHAR(100) NOT NULL,
    `first_name` VARCHAR(100) NULL,
    `middle_initial` CHAR(1) NULL,
    `last_name` VARCHAR(100) NULL,
    `username` VARCHAR(50) NOT NULL,
    `password_hash` VARCHAR(255) NOT NULL,
    `role` ENUM('admin', 'inspector') NOT NULL DEFAULT 'inspector',
    `is_active` TINYINT(1) NOT NULL DEFAULT 1,
    `must_change_password` TINYINT(1) NOT NULL DEFAULT 0,
    `last_login_at` DATETIME NULL,
    `password_changed_at` DATETIME NULL,
    `temporary_password_expires_at` DATETIME NULL,
    `failed_login_attempts` INT NOT NULL DEFAULT 0,
    `locked_until` DATETIME NULL,
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    UNIQUE KEY `uq_users_username` (`username`),
    KEY `idx_users_role_active` (`role`, `is_active`)
) ENGINE=InnoDB;

CREATE TABLE `size_grades` (
    `id` TINYINT UNSIGNED NOT NULL AUTO_INCREMENT,
    `code` VARCHAR(20) NOT NULL,
    `label` VARCHAR(50) NOT NULL,
    `minimum_weight_g` DECIMAL(6,2) NOT NULL,
    `maximum_weight_g` DECIMAL(6,2) NULL,
    `display_order` TINYINT UNSIGNED NOT NULL,
    `is_active` TINYINT(1) NOT NULL DEFAULT 1,
    PRIMARY KEY (`id`),
    UNIQUE KEY `uq_size_grades_code` (`code`),
    UNIQUE KEY `uq_size_grades_display_order` (`display_order`)
) ENGINE=InnoDB;

CREATE TABLE `inspection_batches` (
    `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    `batch_code` VARCHAR(50) NOT NULL,
    `source_name` VARCHAR(100) NULL,
    `notes` TEXT NULL,
    `started_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `completed_at` DATETIME NULL,
    `created_by_user_id` BIGINT UNSIGNED NULL,
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    UNIQUE KEY `uq_inspection_batches_code` (`batch_code`),
    KEY `idx_inspection_batches_started_at` (`started_at`),
    CONSTRAINT `fk_batches_created_by`
        FOREIGN KEY (`created_by_user_id`) REFERENCES `users` (`id`)
        ON UPDATE CASCADE ON DELETE SET NULL
) ENGINE=InnoDB;

CREATE TABLE `egg_inspections` (
    `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    `inspection_code` CHAR(36) NOT NULL,
    `batch_id` BIGINT UNSIGNED NULL,
    `sequence_number` INT UNSIGNED NULL,
    `station_name` VARCHAR(100) NOT NULL DEFAULT 'Station 1',
    `captured_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `weight_g` DECIMAL(6,2) NULL,
    `size_grade_id` TINYINT UNSIGNED NULL,
    `ai_disposition` ENUM('accepted', 'rejected', 'review', 'no_egg') NOT NULL DEFAULT 'review',
    `final_disposition` ENUM('accepted', 'rejected', 'review', 'no_egg') NOT NULL DEFAULT 'review',
    `final_grade` VARCHAR(50) NULL,
    `is_overridden` TINYINT(1) NOT NULL DEFAULT 0,
    `notes` TEXT NULL,
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    UNIQUE KEY `uq_egg_inspections_code` (`inspection_code`),
    UNIQUE KEY `uq_egg_inspections_batch_sequence` (`batch_id`, `sequence_number`),
    KEY `idx_egg_inspections_captured_at` (`captured_at`),
    KEY `idx_egg_inspections_final_disposition_captured` (`final_disposition`, `captured_at`),
    KEY `idx_egg_inspections_size_grade` (`size_grade_id`),
    CONSTRAINT `fk_inspections_batch`
        FOREIGN KEY (`batch_id`) REFERENCES `inspection_batches` (`id`)
        ON UPDATE CASCADE ON DELETE SET NULL,
    CONSTRAINT `fk_inspections_size_grade`
        FOREIGN KEY (`size_grade_id`) REFERENCES `size_grades` (`id`)
        ON UPDATE CASCADE ON DELETE SET NULL
) ENGINE=InnoDB;

CREATE TABLE `inspection_images` (
    `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    `inspection_id` BIGINT UNSIGNED NOT NULL,
    `image_type` ENUM('candling') NOT NULL DEFAULT 'candling',
    `file_path` VARCHAR(500) NOT NULL,
    `captured_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    UNIQUE KEY `uq_inspection_images_inspection` (`inspection_id`),
    CONSTRAINT `fk_images_inspection`
        FOREIGN KEY (`inspection_id`) REFERENCES `egg_inspections` (`id`)
        ON UPDATE CASCADE ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE `ai_assessments` (
    `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    `inspection_id` BIGINT UNSIGNED NOT NULL,
    `assessment_type` ENUM('candling') NOT NULL DEFAULT 'candling',
    `result_label` ENUM('good', 'defective', 'not_an_egg') NOT NULL,
    `confidence_score` DECIMAL(5,4) NULL,
    `is_defect_detected` TINYINT(1) NOT NULL DEFAULT 0,
    `model_name` VARCHAR(100) NULL,
    `model_version` VARCHAR(50) NOT NULL,
    `inference_time_ms` INT UNSIGNED NULL,
    `raw_result` LONGTEXT NULL,
    `assessed_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    UNIQUE KEY `uq_ai_assessments_inspection` (`inspection_id`),
    KEY `idx_ai_assessments_result_label` (`result_label`),
    KEY `idx_ai_assessments_assessed_at` (`assessed_at`),
    CONSTRAINT `fk_ai_assessments_inspection`
        FOREIGN KEY (`inspection_id`) REFERENCES `egg_inspections` (`id`)
        ON UPDATE CASCADE ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE `staff_overrides` (
    `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    `inspection_id` BIGINT UNSIGNED NOT NULL,
    `user_id` BIGINT UNSIGNED NOT NULL,
    `previous_disposition` ENUM('accepted', 'rejected', 'review') NOT NULL,
    `new_disposition` ENUM('accepted', 'rejected', 'review') NOT NULL,
    `previous_grade` VARCHAR(50) NULL,
    `new_grade` VARCHAR(50) NULL,
    `reason` VARCHAR(500) NOT NULL,
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    KEY `idx_staff_overrides_inspection` (`inspection_id`, `created_at`),
    KEY `idx_staff_overrides_user` (`user_id`, `created_at`),
    CONSTRAINT `fk_overrides_inspection`
        FOREIGN KEY (`inspection_id`) REFERENCES `egg_inspections` (`id`)
        ON UPDATE CASCADE ON DELETE CASCADE,
    CONSTRAINT `fk_overrides_user`
        FOREIGN KEY (`user_id`) REFERENCES `users` (`id`)
        ON UPDATE CASCADE ON DELETE RESTRICT
) ENGINE=InnoDB;

CREATE TABLE `auth_sessions` (
    `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    `user_id` BIGINT UNSIGNED NOT NULL,
    `token_hash` CHAR(64) NOT NULL,
    `expires_at` DATETIME NOT NULL,
    `invalidated_at` DATETIME NULL,
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    UNIQUE KEY `uq_auth_sessions_token_hash` (`token_hash`),
    KEY `idx_auth_sessions_user_active` (`user_id`, `invalidated_at`, `expires_at`),
    CONSTRAINT `fk_auth_sessions_user`
        FOREIGN KEY (`user_id`) REFERENCES `users` (`id`)
        ON UPDATE CASCADE ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE `password_change_tokens` (
    `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    `user_id` BIGINT UNSIGNED NOT NULL,
    `token_hash` CHAR(64) NOT NULL,
    `expires_at` DATETIME NOT NULL,
    `used_at` DATETIME NULL,
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    UNIQUE KEY `uq_password_change_tokens_token_hash` (`token_hash`),
    KEY `idx_password_change_tokens_user_active` (`user_id`, `used_at`, `expires_at`),
    CONSTRAINT `fk_password_change_tokens_user`
        FOREIGN KEY (`user_id`) REFERENCES `users` (`id`)
        ON UPDATE CASCADE ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE VIEW `daily_inspection_summary` AS
SELECT
    DATE(`captured_at`) AS `inspection_date`,
    COUNT(*) AS `total_inspected`,
    SUM(`final_disposition` = 'accepted') AS `accepted_count`,
    SUM(`final_disposition` = 'rejected') AS `rejected_count`,
    SUM(`final_disposition` = 'review') AS `review_count`,
    SUM(`is_overridden` = 1) AS `overridden_count`,
    ROUND(AVG(`weight_g`), 2) AS `average_weight_g`
FROM `egg_inspections`
WHERE `final_disposition` <> 'no_egg'
GROUP BY DATE(`captured_at`);
