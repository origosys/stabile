CREATE TABLE IF NOT EXISTS `domainxml` (
  `uuid` varchar(48) NOT NULL DEFAULT '',
  `xml` mediumtext,
  PRIMARY KEY (`uuid`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8;
