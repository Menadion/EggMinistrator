-- Adds temporary-password enforcement without recreating or deleting `users`.
-- Existing users receive safe defaults: no forced change, no expiry, zero failed attempts.

USE `eggministrator`;

ALTER TABLE `users`
    ADD COLUMN `must_change_password` TINYINT(1) NOT NULL DEFAULT 0 AFTER `is_active`,
    ADD COLUMN `password_changed_at` DATETIME NULL AFTER `last_login_at`,
    ADD COLUMN `temporary_password_expires_at` DATETIME NULL AFTER `password_changed_at`,
    ADD COLUMN `failed_login_attempts` INT NOT NULL DEFAULT 0 AFTER `temporary_password_expires_at`,
    ADD COLUMN `locked_until` DATETIME NULL AFTER `failed_login_attempts`;

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
