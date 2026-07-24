<?php
/**
 * EggMinistrator — database config TEMPLATE.
 *
 * Copy this file to `config.php` and fill in your local values.
 * `config.php` is gitignored — NEVER commit real credentials.
 */

define('DB_HOST', 'localhost');
define('DB_NAME', 'eggministrator');
define('DB_USER', 'root');
define('DB_PASS', '');            // XAMPP's default is empty; set your own in config.php
define('DB_CHARSET', 'utf8mb4');

// Optional: where the Python inference script writes results, if the dashboard reads them.
// define('INFERENCE_RESULTS_DIR', __DIR__ . '/../ai/inference/results');
