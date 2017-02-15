CREATE TABLE IF NOT EXISTS `users` (
	id int not null auto_increment,
	uid int not null unique,
	cid int not null unique,
	uname varchar(255) not null,
	primary key(id)
);

DROP TABLE `topics`;
CREATE TABLE `topics` (
	id int not null auto_increment,
	cid int not null,
	topic varchar(255) not null,
	primary key(id),
	foreign key(cid) references users(cid),
	unique `ident` (`cid`, `topic`)
);
