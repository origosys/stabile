CREATE TABLE IF NOT EXISTS `images` (
  `uuid` varchar(48) DEFAULT NULL,
  `path` varchar(256) CHARACTER SET utf8 COLLATE utf8_bin NOT NULL DEFAULT '',
  `name` varchar(256) CHARACTER SET utf8 COLLATE utf8_bin DEFAULT NULL,
  `domains` varchar(4096) DEFAULT NULL,
  `status` varchar(48) DEFAULT NULL,
  `user` varchar(256) DEFAULT NULL,
  `type` varchar(8) DEFAULT NULL,
  `size` bigint(24) DEFAULT NULL,
  `realsize` bigint(24) DEFAULT NULL,
  `virtualsize` bigint(24) DEFAULT NULL,
  `snap1` varchar(48) DEFAULT NULL,
  `master` varchar(256) DEFAULT NULL,
  `backup` varchar(256) DEFAULT NULL,
  `bschedule` varchar(64) DEFAULT NULL,
  `domainnames` varchar(4096) DEFAULT NULL,
  `installable` varchar(16) DEFAULT NULL,
  `notes` text,
  `image2` varchar(256) DEFAULT NULL,
  `managementlink` varchar(256) DEFAULT NULL,
  `upgradelink` varchar(256) DEFAULT NULL,
  `terminallink` varchar(256) DEFAULT NULL,
  `storagepool` int(8) DEFAULT NULL,
  `mtime` bigint(20) DEFAULT NULL,
  `mac` varchar(17) DEFAULT NULL,
  `backupsize` bigint(24) DEFAULT NULL,
  `btime` varchar(48) DEFAULT NULL,
  `appid` varchar(48) DEFAULT NULL,
  `created` varchar(48) DEFAULT NULL,
  `version` varchar(48) DEFAULT NULL,
  PRIMARY KEY (`path`),
  KEY `images-index` (`uuid`,`path`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8;
