CREATE TABLE IF NOT EXISTS `networks` (
  `id` int(11) NOT NULL DEFAULT '0',
  `name` varchar(64) DEFAULT NULL,
  `action` varchar(48) DEFAULT NULL,
  `domains` varchar(4096) DEFAULT NULL,
  `internalip` varchar(15) DEFAULT NULL,
  `externalip` varchar(15) DEFAULT NULL,
  `uuid` varchar(48) NOT NULL DEFAULT '',
  `status` varchar(48) DEFAULT NULL,
  `domainnames` varchar(4096) DEFAULT NULL,
  `user` varchar(256) DEFAULT NULL,
  `nextid` int(11) DEFAULT NULL,
  `type` varchar(16) DEFAULT NULL,
  `ports` varchar(256) DEFAULT NULL,
  `systems` varchar(256) DEFAULT NULL,
  `systemnames` varchar(256) DEFAULT NULL,
  PRIMARY KEY (`uuid`),
  KEY `networks-index` (`id`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8;

insert into networks (id,name,uuid,status,user,type) values (0,'Qemu NAT','0','up','common','gateway');
insert into networks (id,name,uuid,status,user,type) values (1,'Libvirt NAT','1','up','common','gateway');
