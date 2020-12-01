CREATE TABLE IF NOT EXISTS `billing_networks` (
  `useridtime` varchar(256) NOT NULL,
  `externalip` int(12) DEFAULT NULL,
  `event` text,
  `timestamp` varchar(48) DEFAULT NULL,
  `externalipavg` float(12,6) DEFAULT NULL,
  `inc` int(12) DEFAULT NULL,
  `starttimestamp` varchar(48) DEFAULT NULL,
  `startexternalipavg` float(12,6) DEFAULT NULL,
  `rx` bigint(20) DEFAULT NULL,
  `tx` bigint(20) DEFAULT NULL,
  PRIMARY KEY (`useridtime`),
  KEY `billing_networks-index` (`useridtime`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8;
