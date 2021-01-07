<?php
/*	$jwk: wp_disable_plugins.php,v 1.5 2011/04/29 02:57:09 jwk Exp $ */

/*
 * wp_disable_plugins.php
 *
 * CLI helper script for WordPress that disables plugins. Run without 
 * any arguments to display list of plugins. Specify plugins to disable 
 * as arguments to the script. Run it from your WordPress directory so 
 * it can pick up your wp-config.php file.
 *
 *
 *
 * Joel Knight
 * www.packetmischief.ca
 * 2011.04.18
 */

@include "wp-config.php";

if (!defined('DB_NAME'))
	die("ERROR: DB_NAME not defined. Are you in the 'wordpress' directory?\n");

$dbh = mysql_connect(DB_HOST, DB_USER, DB_PASSWORD);
if (!$dbh)
	die("Could not connect to database: " . mysql_error());
if (mysql_select_db(DB_NAME) == FALSE)
	die("Could not select database '" . DB_NAME . "': " . mysql_error());

$sql = "SELECT option_value
	FROM " . $table_prefix . "options
	WHERE option_name = 'active_plugins'
	";

$disable_plugins = $argv;
array_shift($disable_plugins); /* pull the script filename off */

$result = mysql_query($sql);
if ($result == false)
	die("Query failed: " . mysql_error() . "\n");

$row = mysql_fetch_assoc($result);

$plugins = unserialize($row["option_value"]);

if (sizeof($disable_plugins) == 0) {
	printf("Active plugins:\n");
	foreach ($plugins as $pkey => $pval) {
		printf("- %s\n", $pval);
	}
	printf("\nSpecify plugin name(s) from above on the command line to disable them.\n");
} else {
	$cnt = 0;
	foreach ($plugins as $pkey => $pval) {
		foreach ($disable_plugins as $dkey => $dval) {
			if ($pval == $dval) {
				unset($plugins[$pkey]);
				$cnt++;
			}
		}
	}

	$sql = "UPDATE " . $table_prefix . "options
		SET option_value = '" . serialize($plugins) . "'
		WHERE option_name = 'active_plugins'
		";
	$result = mysql_query($sql);
	if ($result == false)
		die("Query failed: " . mysql_error() . "\n");

	printf("Disabled %d/%d plugins.\n", $cnt, sizeof($disable_plugins));
}

