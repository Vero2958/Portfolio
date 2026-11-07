[![Review Assignment Due Date](https://classroom.github.com/assets/deadline-readme-button-24ddc0f5d75046c5622901739e7c5dd533143b0c8e959d652212380cedb1ea36.svg)](https://classroom.github.com/a/Da5EC248)
## TRAITS Implementation
Agnieszka Nowak & Veronica Scozzi

### Relational DB schema
CREATE TABLE User(
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) PRIMARY KEY,
    user_status ENUM('BASIC', 'REGISTERED', 'ADMIN') NOT NULL
);

CREATE TABLE Station(
    station_id INT PRIMARY KEY AUTO_INCREMENT,
    station_name VARCHAR(255) NOT NULL
);

CREATE TABLE Train(
    train_id INT PRIMARY KEY AUTO_INCREMENT,
    capacity INT NOT NULL,
    train_status ENUM('OPERATIONAL', 'DELAYED', 'BROKEN') NOT NULL
);

CREATE TABLE Schedule(
    station_id INT NOT NULL,
    train_id INT NOT NULL,
    stop_duration INT NOT NULL,
    valid_from DATE NOT NULL,
    valid_untill DATE NOT NULL,
    FOREIGN KEY (station_id) REFERENCES Station(station_id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY (train_id) REFERENCES Train(train_id)
        ON DELETE CASCADE ON UPDATE CASCADE
);

Note: we had doubt about what a schedule actually was, we intended it to be the path trains do every day from the date listed in valid_from to the date listed in valid_untill, and that get changed periodically fo each train, therefore the table schedule we came up with allows to find all the trains that pass through a station and all the station a train passes through by selecting based on the considered train id and or the considered station id. We didn't insert the time anywhere in this table, but it would have made sense to do so, this way we would have been able to easily find a train route just by using a SORT BY statement. We didn't because we didn't find the necessity for that info anywhere during the implementation, though most lickely this means the we are not storing some info that needed to be stored, like for example the departure hour in a booking, of which we are only storing the departure date.

CREATE TABLE Bookings(
    booking_id INT PRIMARY KEY AUTO_INCREMENT,
    user_email VARCHAR(255) NOT NULL,
    total_price DECIMAL(10, 2) NOT NULL,
    dep_date TIMESTAMP NOT NULL,
    to_station INT NOT NULL,
    from_station INT NOT NULL,
    FOREIGN KEY (from_station) REFERENCES Station(station_id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY (to_station) REFERENCES Station(station_id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY (user_email) REFERENCES User(email)
        ON DELETE CASCADE ON UPDATE CASCADE
);

CREATE TABLE Seat_reservation(
    booking_id INT NOT NULL,
    train_id INT NOT NULL,
    seat_reservation ENUM('YES', 'NO') NOT NULL,
    PRIMARY KEY (booking_id, train_id),
    FOREIGN KEY (booking_id) REFERENCES Bookings(booking_id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY (train_id) REFERENCES Train(train_id)
        ON DELETE CASCADE ON UPDATE CASCADE
);

This db structure was modified multiple times, we started designing the db by reading, listing down the requirements and trying to come up with an ER diagram that could allow us to fulfill them, at first we had a completely different structure, some tables were not normalized and therefore we had, for example a table booking that included the seat reservations, in which there was more than one entry for each booking based on how many trains the passenger had to take during that travel, later we decided to normalize it, creating a differnet table. Something similiar happened to the table Train, because at first we used to have in our implementation a table called "TrainInfo", which would store the infor about the train and its schedule, the problem was that this way a train didn't exest if it wasn't working, so we added the Table Train to store trains' ids, capacities and status, the other table was later delete because the info stored in it were useless for the implementation.

CREATE TABLE TrainInfo(
    train_id INT PRIMARY KEY,
    departure_station_id INT NOT NULL,
    arrival_station_id INT NOT NULL,
    departure_time TIMESTAMP NOT NULL,
    arrival_time TIMESTAMP NOT NULL,
    FOREIGN KEY (train_id) REFERENCES Train(train_id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY (departure_station_id) REFERENCES Station(station_id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY (arrival_station_id) REFERENCES Station(station_id)
        ON DELETE CASCADE ON UPDATE CASCADE
);

### NoSQL Database
we used it to store the informations about how stations were connected, waiting time of trains and travel time between the 2 stations, the following is the query we used to create the connection in the db: MATCH (s1:Station {Station_id: $starting_station_id}),(s2:Station {Station_id: $ending_station_id})
CREATE (s1)-[:CONNECTED_TO {travel_time_in_minutes: $minutes, waiting_time: $minutes_w}]->(s2); the waiting time refers to the time the train will wait at s2 before leaving again, this is because by doing so each station has a waiting time except the station the train departs from, which doesn't need one. 

### Implementation and some (IMPORTANT) issues
We implemented all the classes and methods that were in the interface.py file, during development we used easy test cases to ensure that at least the method was working as expected with the proper data and non (test cases are at the end of the implementation.py file in triple quotes), we had little time to write personal tests because of an issue we have with the public ones. 
!! IMPORTANT !!
During execution of the public tests, we have encountered an error we have never encountered before. The error is the following and it is not due the to false logic, even after trying to correct it, it kept on coming back: 
pymysql.err.ProgrammingError: (1064, "You have an error in your SQL syntax; check the manual that corresponds to your MariaDB server version for the right syntax to use near 'DROP USER IF EXISTS 'traits'@'%';CREATE USER 'traits-admin'@'%' IDENTIFIED BY...' at line 1")
we suspected it had something to do with the method TraitsUtility.generate_sql_initialization_code(), we duble checked the syntax but nothing seemed to be wrong with it, therefore we also asked for help to our colleagues, and that didb't work as well. Unfortunately this error didn't allow us to properly test using the public tests, and it also stole a lot of time from the amount we had scheduled for writing personal tests, therefore we ask for your leniency, the penalty to be waived and some feedbacks on how to deal with this issue, which we still are not able to solve in spite of trying in the past days, we also kindly ask you to consider as valid the new personal tests that will come in the few following days. 
