drop table if exists users;
drop table if exists groups;
drop table if exists profiles;
drop table if exists points;
drop table if exists activities;


create table users (
  id integer primary key autoincrement,
  username string not null,
  password string not null
);

create table groups (
  id integer primary key autoincrement,
  groupname string not null,
  desc string not null,
  size integer
);

create table profiles (
  isready string,
  email string not null,
  username string not null,
  firstname string not null,
  lastname string not null,
  age string,
  sex string,
  department string not null,
  groupname string not null,
  userealname string null
);

create table points (
  username string not null,
  point integer,
  level integer,
  year integer,
  month integer,
  day integer
);

create table activities (
  id integer primary key autoincrement,
  username string not null,
  year integer,
  month integer,
  day integer,
  activity string not null,
  ppl integer,
  low integer,
  moderate integer,
  high integer,
  newpoints integer,
  isthisweek integer,
  note string not null,
  rate integer,
  happiness integer,
  activeness integer,
  hour integer,
  minute integer, 
  second integer
);

drop table if exists login;

create table login (
  year integer,
  month integer,
  day integer
);

insert into login (year, month, day) values (2012, 12, 31)