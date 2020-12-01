CREATE TABLE IF NOT EXISTS `nodeidentities` (
  `identity` varchar(32) DEFAULT NULL,
  `hypervisor` varchar(32) NOT NULL DEFAULT '',
  `dist` varchar(32) DEFAULT NULL,
  `formats` varchar(64) DEFAULT NULL,
  `name` varchar(256) NOT NULL DEFAULT '',
  `sleepafter` int(11) DEFAULT '0',
  `arch` varchar(64) DEFAULT NULL,
  `kernel` varchar(256) DEFAULT NULL,
  `path` varchar(256) DEFAULT NULL,
  PRIMARY KEY (`name`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8;

INSERT INTO `nodeidentities` VALUES ('default','kvm','bionic','img,qcow,qcow2','kvm-bionic-x64',0,'x86-64','4.15.0-112-generic','/mnt/stabile/tftp/bionic');
