CREATE TABLE IF NOT EXISTS `systems` (
  `uuid` varchar(48) NOT NULL DEFAULT '',
  `name` varchar(256) DEFAULT NULL,
  `user` varchar(256) DEFAULT NULL,
  `notes` text,
  `created` varchar(48) DEFAULT NULL,
  `opemail` varchar(256) DEFAULT NULL,
  `opfullname` varchar(256) DEFAULT NULL,
  `opphone` varchar(256) DEFAULT NULL,
  `email` varchar(256) DEFAULT NULL,
  `fullname` varchar(256) DEFAULT NULL,
  `phone` varchar(256) DEFAULT NULL,
  `services` varchar(256) DEFAULT NULL,
  `recovery` text,
  `alertemail` varchar(256) DEFAULT NULL,
  `image` varchar(256) DEFAULT NULL,
  `networkuuid1` varchar(48) DEFAULT NULL,
  `internalip` varchar(15) DEFAULT NULL,
  PRIMARY KEY (`uuid`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8;
