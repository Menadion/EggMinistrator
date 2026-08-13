-- Adds structured employee-name fields while retaining `full_name` for compatibility.
-- The role change is blocked if a viewer account exists, so no account is reassigned automatically.

DELIMITER //

CREATE PROCEDURE `apply_account_name_and_role_migration`()
BEGIN
    IF EXISTS (SELECT 1 FROM `users` WHERE `role` = 'viewer') THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Migration stopped: reassign viewer accounts to admin or inspector before restricting roles.';
    END IF;

    ALTER TABLE `users`
        ADD COLUMN `first_name` VARCHAR(100) NULL AFTER `full_name`,
        ADD COLUMN `middle_initial` CHAR(1) NULL AFTER `first_name`,
        ADD COLUMN `last_name` VARCHAR(100) NULL AFTER `middle_initial`,
        MODIFY COLUMN `role` ENUM('admin', 'inspector') NOT NULL DEFAULT 'inspector';
END//

CALL `apply_account_name_and_role_migration`()//
DROP PROCEDURE `apply_account_name_and_role_migration`//

DELIMITER ;
