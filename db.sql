CREATE TABLE IF NOT EXISTS `users` (
  `id` int not null auto_increment,
  `uid` int not null unique,
  `cid` int not null unique,
  `uname` varchar(255) not null,
  `no_plus_one` BIT not null default 0,
  `is_active` BIT not null default 1,
  primary key(`id`)
);

CREATE TABLE IF NOT EXISTS `topics` (
  `id` int not null auto_increment,
  `cid` int not null,
  `cat_id` int not null,
  `topic` varchar(255) not null,
  primary key(id),
  foreign key(`cid`) references users(`cid`),
  unique `ident` (`cid`, `topic`, `cat_id`)
);

CREATE TABLE IF NOT EXISTS `aliases` (
  `id` int not null auto_increment,
  `cid` int not null,
  `alias` varchar(255) not null,
  foreign key(`cid`) references users(`cid`),
  primary key(`id`),
  unique `ident` (`cid`, `alias`)
);
