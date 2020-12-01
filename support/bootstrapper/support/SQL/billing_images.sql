CREATE TABLE IF NOT EXISTS `billing_images` (
  `userstoragepooltime` varchar(256) NOT NULL,
  `virtualsize` bigint(24) DEFAULT NULL,
  `realsize` bigint(24) DEFAULT NULL,
  `backupsize` bigint(24) DEFAULT NULL,
  `event` text,
  `timestamp` varchar(48) DEFAULT NULL,
  `virtualsizeavg` double(24,6) DEFAULT NULL,
  `realsizeavg` double(24,6) DEFAULT NULL,
  `backupsizeavg` double(24,6) DEFAULT NULL,
  `inc` int(12) DEFAULT NULL,
  `starttimestamp` varchar(48) DEFAULT NULL,
  `startvirtualsizeavg` double(24,6) DEFAULT NULL,
  `startrealsizeavg` double(24,6) DEFAULT NULL,
  `startbackupsizeavg` double(24,6) DEFAULT NULL,
  PRIMARY KEY (`userstoragepooltime`),
  KEY `billing_images-index` (`userstoragepooltime`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8;
