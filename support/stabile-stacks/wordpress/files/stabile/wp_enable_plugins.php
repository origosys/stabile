<?php
/*	$jwk: wp_enable_plugins.php,v 1.2 2011/04/29 14:50:58 jwk Exp $ */

/*
 * wp_enable_plugins.php
 *
 * CLI helper script for WordPress that enables plugins. Run without 
 * any arguments to display list of plugins that exist in your 
 * wp-content/plugins/ directory. Specify plugins to enable as
 * arguments to the script. Note by default it does not enable plugins
 * network-wide (if you're running multi-site). Run it from your WordPress 
 * directory so it can pick up your wp-config.php file.
 *
 *
 *
 * Joel Knight
 * www.packetmischief.ca
 * 2011.04.29
 */

@include "wp-config.php";
@include_once "wp-includes/functions.php";
@include_once "wp-admin/includes/plugin.php";

if (!defined('DB_NAME'))
	die("ERROR: DB_NAME not defined. Are you in the 'wordpress' directory?\n");

$action_plugins = $argv;
array_shift($action_plugins); /* pull the script filename off */

if (sizeof($action_plugins) == 0) {
	$installed_plugins = get_plugins();
	printf("Inactive plugins:\n");
	foreach ($installed_plugins as $pkey => $pval) {
		if (!is_plugin_active($pkey))
			printf("- %s\n", $pkey);
	}
	printf("\nSpecify plugin name(s) from above on the command line to enable them.\n");
} else {
	$cnt = 0;
	foreach ($action_plugins as $akey => $aval) {
		if (activate_plugin($aval, '', /* network wide? */ false, /* silent? */ false) == null)
			$cnt++;
	}
	printf("Enabled %d/%d plugins.\n", $cnt, sizeof($action_plugins));
}

