CREATE TABLE IF NOT EXISTS `register` (
  `uuid` varchar(48) NOT NULL,
  `os` varchar(256) DEFAULT NULL,
  `system` varchar(48) DEFAULT NULL,
  `name` varchar(256) DEFAULT NULL,
  `hostname` varchar(256) DEFAULT NULL,
  `user` varchar(256) DEFAULT NULL,
  PRIMARY KEY (`uuid`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8;
