create database hypnox;
create user hypnox with password '';
grant all privileges on database "hypnox" to hypnox;
create table stream_user (id serial primary key, created_at timestamp, text varchar, model varchar, intensity decimal, polarity decimal)
