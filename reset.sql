drop table if exists login;

create table login (
  year integer,
  month integer,
  day integer
);

insert into login (year, month, day) values (2012, 12, 31)