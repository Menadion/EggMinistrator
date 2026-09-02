-- Fan-out (spec docs/superpowers/specs/2026-09-02-software-fanout-design.md, section 3).
--
-- One lid-close of the 2x3 tray is one `tray_cycles` row. The k eggs that come
-- out of it are ordinary `egg_inspections` rows that point back at the cycle
-- and carry the slot they were loaded into. v1 rows keep both columns NULL
-- forever. The unique key on (cycle_id, tray_slot) is the attribution
-- constraint: one egg per slot per cycle, enforced by the database.
--
-- Additive: no existing row changes. Safe to run once on a live database.

USE `eggministrator`;

CREATE TABLE `tray_cycles` (
    `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    `station_name` VARCHAR(100) NOT NULL DEFAULT 'Station 1',
    `status` ENUM('pending','done','rejected') NOT NULL DEFAULT 'pending',
    `frame_path` VARCHAR(500) NULL,
    `raw_weights` LONGTEXT NULL,
    `rejected_reason` VARCHAR(200) NULL,
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `completed_at` DATETIME NULL,
    PRIMARY KEY (`id`),
    KEY `idx_tray_cycles_status_created` (`status`, `created_at`)
) ENGINE=InnoDB;

ALTER TABLE `egg_inspections`
    ADD COLUMN `cycle_id` BIGINT UNSIGNED NULL,
    ADD COLUMN `tray_slot` TINYINT UNSIGNED NULL,
    ADD UNIQUE KEY `uq_egg_inspections_cycle_slot` (`cycle_id`, `tray_slot`),
    ADD CONSTRAINT `fk_inspections_cycle`
        FOREIGN KEY (`cycle_id`) REFERENCES `tray_cycles` (`id`)
        ON UPDATE CASCADE ON DELETE SET NULL;
