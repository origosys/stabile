CREATE TABLE IF NOT EXISTS `billing_domains` (
  `usernodetime` varchar(256) NOT NULL,
  `vcpu` int(12) DEFAULT NULL,
  `memory` int(12) DEFAULT NULL,
  `event` text,
  `timestamp` varchar(48) DEFAULT NULL,
  `vcpuavg` float(12,6) DEFAULT NULL,
  `memoryavg` float(12,6) DEFAULT NULL,
  `inc` int(12) DEFAULT NULL,
  `starttimestamp` varchar(48) DEFAULT NULL,
  `startvcpuavg` float(12,6) DEFAULT NULL,
  `startmemoryavg` float(12,6) DEFAULT NULL,
  PRIMARY KEY (`usernodetime`),
  KEY `billing_domains-index` (`usernodetime`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8;
