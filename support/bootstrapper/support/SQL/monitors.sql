CREATE TABLE IF NOT EXISTS `monitors` (
  `id` varchar(256) NOT NULL,
  `savedstate` int(11) DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8;
