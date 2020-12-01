CREATE TABLE IF NOT EXISTS `packages` (
  `id` varchar(256) NOT NULL,
  `app_name` varchar(256) NOT NULL DEFAULT '',
  `app_version` varchar(256) NOT NULL DEFAULT '',
  `app_display_name` varchar(256) DEFAULT NULL,
  `app_release` varchar(256) DEFAULT NULL,
  `app_publisher` varchar(256) DEFAULT NULL,
  `app_url` varchar(256) DEFAULT NULL,
  `user` varchar(256) DEFAULT NULL,
  `domuuid` varchar(48) DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8;
