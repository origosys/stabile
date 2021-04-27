CREATE TABLE IF NOT EXISTS `nodes` (
  `mac` varchar(17) NOT NULL DEFAULT '',
  `identity` varchar(20) DEFAULT NULL,
  `cpuname` varchar(48) DEFAULT NULL,
  `timestamp` varchar(48) DEFAULT NULL,
  `ip` varchar(15) DEFAULT NULL,
  `cpucores` int(3) DEFAULT NULL,
  `cpucount` int(3) DEFAULT NULL,
  `cpuspeed` varchar(12) DEFAULT NULL,
  `cpufamily` varchar(4) DEFAULT NULL,
  `cpumodel` varchar(4) DEFAULT NULL,
  `memtotal` varchar(12) DEFAULT NULL,
  `memfree` varchar(12) DEFAULT NULL,
  `status` varchar(12) DEFAULT NULL,
  `action` varchar(48) DEFAULT NULL,
  `tasks` TEXT CHARACTER SET utf8 COLLATE utf8_bin DEFAULT NULL,
  `vms` int(11) DEFAULT '0',
  `cpuload` float(8,2) DEFAULT NULL,
  `name` varchar(256) DEFAULT NULL,
  `ipmiip` varchar(15) DEFAULT NULL,
  `vmvcpus` int(11) DEFAULT NULL,
  `stortotal` varchar(18) DEFAULT NULL,
  `storfree` varchar(18) DEFAULT NULL,
  `stor` varchar(18) DEFAULT NULL,
  `reservedvcpus` int(11) DEFAULT NULL,
  `vmuuids` TEXT DEFAULT NULL,
  `vmnames` TEXT DEFAULT NULL,
  `vmusers` TEXT DEFAULT NULL,
  `nfsroot` varchar(256) DEFAULT NULL,
  `kernel` varchar(64) DEFAULT NULL,
  `maintenance` int(4) DEFAULT NULL,
  `amtip` varchar(15) DEFAULT NULL,
  PRIMARY KEY (`mac`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8;
