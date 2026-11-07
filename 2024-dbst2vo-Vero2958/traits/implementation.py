import re
import datetime
from itertools import product
from typing import List, Optional, Tuple, Dict
import mysql.connector
# Import all the necessary classes from the public submodule:
from traits.interface import TraitsInterface, TraitsUtilityInterface, TraitsKey, TrainStatus, SortingCriteria
from neo4j import GraphDatabase, exceptions
# Import all the necessary default configurations
from traits.interface import BASE_USER_NAME, BASE_USER_PASS, ADMIN_USER_NAME, ADMIN_USER_PASS


# Implement the utility class. Add any additional method that you need
class TraitsUtility(TraitsUtilityInterface):

    def __init__(self, rdbms_connection, rdbms_admin_connection, neo4j_driver) -> None:
        self.rdbms_connection = rdbms_connection
        self.rdbms_admin_connection = rdbms_admin_connection
        self.neo4j_driver = neo4j_driver

    @staticmethod
    def generate_sql_initialization_code() -> List[str]:
        # Note: this code ensures that users are recreated as needed. You need to add the proper permissions.
        # Also add here the statements to setup the database.
        return [
            f"DROP USER IF EXISTS '{ADMIN_USER_NAME}'@'%';"
            f"DROP USER IF EXISTS '{BASE_USER_NAME}'@'%';"
            f"CREATE USER '{ADMIN_USER_NAME}'@'%' IDENTIFIED BY '{ADMIN_USER_PASS}';",
            f"CREATE USER '{BASE_USER_NAME}'@'%' IDENTIFIED BY '{BASE_USER_PASS}';",
            f"GRANT ALL PRIVILEGES ON *.* TO '{ADMIN_USER_NAME}'@'%' WITH GRANT OPTION;",
            f"GRANT SELECT, INSERT, UPDATE, DELETE ON *.* TO '{BASE_USER_NAME}'@'%';",
            f"FLUSH PRIVILEGES;",
            '''CREATE TABLE User(
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) PRIMARY KEY,
    user_status ENUM('BASIC', 'REGISTERED', 'ADMIN') NOT NULL
);

-- Create Station Table
CREATE TABLE Station(
    station_id INT PRIMARY KEY AUTO_INCREMENT,
    station_name VARCHAR(255) NOT NULL
);

-- Create Train Table
CREATE TABLE Train(
    train_id INT PRIMARY KEY AUTO_INCREMENT,
    capacity INT NOT NULL,
    train_status ENUM('OPERATIONAL', 'DELAYED', 'BROKEN') NOT NULL
);

-- Create TrainInfo Table
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

-- Create Schedule Table
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

-- Create Bookings Table
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

-- Create Seat_reservation Table
CREATE TABLE Seat_reservation(
    booking_id INT NOT NULL,
    train_id INT NOT NULL,
    seat_reservation ENUM('YES', 'NO') NOT NULL,
    PRIMARY KEY (booking_id, train_id),
    FOREIGN KEY (booking_id) REFERENCES Bookings(booking_id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY (train_id) REFERENCES Train(train_id)
        ON DELETE CASCADE ON UPDATE CASCADE
);'''
        ]

    def get_all_users(self) -> List:
        """
        Get all users in the DB
        :return: List of Users
        """
        try:
            connection = self.rdbms_connection
            cursor = connection.cursor(dictionary=True)

            query = "SELECT * FROM User;"
            cursor.execute(query)
            users = cursor.fetchall()

            return users

        except mysql.connector.Error as e:
            print(f"Error fetching users: {e}")
            return []

    def get_all_schedules(self) -> List:
        """
        Return all the schedules stored in the database
        """
        try:
            connection = self.rdbms_connection
            cursor = connection.cursor(dictionary=True)
            query_1 = 'SELECT DISTINCT train_id FROM Train'
            cursor.execute(query_1)
            ids = cursor.fetchall()
            schedules = []
            for n in ids:
                n = n['train_id']
                query = "SELECT station_id FROM Schedule WHERE train_id = %s"
                cursor.execute(query, (n, ))
                result = cursor.fetchall()
                schedules.append(result)
            return schedules

        except mysql.connector.Error as e:
            print(f"Error fetching schedules: {e}")
            return []


# Implement the main class that you need to implement
class Traits(TraitsInterface):

    def __init__(self, rdbms_connection, rdbms_admin_connection, neo4j_driver) -> None:
        self.rdbms_connection = rdbms_connection
        self.rdbms_admin_connection = rdbms_admin_connection
        self.neo4j_driver = neo4j_driver

    def search_connections(self, starting_station_key: TraitsKey, ending_station_key: TraitsKey,
                           travel_time_day: int = None, travel_time_month : int = None, travel_time_year : int = None,
                           is_departure_time=True,
                           sort_by: SortingCriteria = SortingCriteria.OVERALL_TRAVEL_TIME, is_ascending : bool =True,
                           limit: int = 5) -> List:
        """
        Search Train Connections (between two stations).
        Sorting criteria can be one of the following:overall travel time, number of train changes, waiting time, and estimated price

        Return the connections from a starting and ending stations, possibly including changes at interchanging stations.
        Returns an empty list if no connections are possible
        Raise a ValueError in case of errors and if the starting or ending stations are the same
        """
        if starting_station_key == ending_station_key:
            raise ValueError("Starting and ending stations cannot be the same.")

        travel_date = datetime.date(travel_time_year, travel_time_month, travel_time_day) if travel_time_day and travel_time_month and travel_time_year else None

        mariaDb = self.rdbms_admin_connection
        neo4j = self.neo4j_driver

        stations_trains = []
        with neo4j.session() as session:
            def find_connection(tx, starting_station_key, ending_station_key):
                query = """
                        MATCH (start:Station {Station_id: $starting_station_id}), (end:Station {Station_id: $ending_station_id})
                        MATCH path = ALL((start)-[r:CONNECTED_TO*]->(end))
                        RETURN path, r
                        """
                result = tx.run(query, starting_station_id=starting_station_key, ending_station_id=ending_station_key)
                records = list(result)
                if not records:
                    raise ValueError('No connection between the stations')
                return records

            result = session.execute_write(find_connection, starting_station_key, ending_station_key)
            print(result)

            i = 1
            record = []
            for path in result:
                path = path['path']
                waiting_times = []
                travel_times = []
                stations_ids = []
                changes_count = 0
                for relationship in path.relationships:
                    waiting_times.append(relationship['waiting_time'])
                    travel_times.append(relationship['travel_time_in_minutes'])
                for node in path.nodes:
                    stations_ids.append(node['Station_id'])
                    changes_count += 1
                record.append({i: {'departure_date': travel_date, 'waiting times': waiting_times, 'travel_times': travel_times, 'total waiting time': sum(waiting_times), 'total travel time': sum(travel_times),'station_id': stations_ids, 'number_of_intermediate_stops': changes_count-2, 'total_price': sum(travel_times)/2}})
                i += 1


            if sort_by == SortingCriteria.OVERALL_TRAVEL_TIME:
                key_func = lambda x: list(x.values())[0]['total travel time']
            elif sort_by == SortingCriteria.NUMBER_OF_TRAIN_CHANGES:
                key_func = lambda x: list(x.values())[0]['number_of_intermediate_stops']
            elif sort_by == SortingCriteria.OVERALL_WAITING_TIME:
                key_func = lambda x: list(x.values())[0]['total waiting time']
            elif sort_by == SortingCriteria.ESTIMATED_PRICE:
                key_func = lambda x: list(x.values())[0]['total_price']
            else:
                key_func = lambda x: list(x.values())[0]['total travel time']

            connections = sorted(record, key=key_func, reverse=not is_ascending)[:limit]

            print(record)

        return connections

    def get_train_current_status(self, train_key: TraitsKey) -> Optional[TrainStatus]:
        """
        Check the status of a train. If the train does not exist returns None
        """
        connection = self.rdbms_connection
        cursor = connection.cursor()
        query = 'SELECT train_status FROM Train WHERE train_id = %s'
        cursor.execute(query, (train_key, ))
        status = cursor.fetchone()
        return status

    def buy_ticket(self, user_email: str, connection: dict, also_reserve_seats=True):
        """
        Given a train connection instance (e.g., on a given date/time), registered users can book tickets and optionally reserve seats. When the user decides to reserve seats, the system will try to reserve all the available seats automatically.
        We make the following assumptions:
            - There is always a place on the trains, so tickets can be always bought
            - The train seats are not numbered, so the system must handle only the number of passengers booked on a train and not each single seat.
            - The system grants only those seats that are effectively available at the moment of request; thus, overbooking on reserved seats is not possible.
            - Seats reservation cannot be done after booking a ticket.
            - A user can only reserve one seat in each train at the given time.

        If the user does not exist, the method must raise a ValueError
        """
        mariadb = self.rdbms_admin_connection
        cursor = mariadb.cursor()
        query0 = 'SELECT user_status FROM User WHERE email = %s;'
        cursor.execute(query0, (user_email, ))
        status = cursor.fetchone()
        if not status:
            raise ValueError('invalid email')
        if status == 'BASIC':
            raise ValueError('not registered users cannot book tickets')

        query1 = 'INSERT INTO Bookings(user_email, total_price, dep_date, from_station, to_station) VALUES (%s, %s, %s, %s, %s)'
        keys = connection.keys()  # we know we only have 1 key because it's only 1 connection
        for key in keys:
            total_price = connection[key]['total_price']
            stops = connection[key]['station_id']
            dep_date = connection[key]['departure_date']
        from_station = stops[0]
        to_station = stops[1]

        stations_trains = []
        query = 'SELECT train_id FROM Schedule WHERE station_id = %s;'
        for s_id in stops:
            station_id = s_id
            cursor.execute(query, (station_id,))
            trains = [train[0] for train in cursor.fetchall()]  # Extract train IDs from the fetched tuples
            stations_trains.append({station_id: trains})
        print(stations_trains)

        common_elements = []
        for i in range(len(stations_trains) - 1):
            set1 = set(stations_trains[i][list(stations_trains[i].keys())[0]])
            set2 = set(stations_trains[i + 1][list(stations_trains[i + 1].keys())[0]])
            common_trains = list(set1 & set2)
            if not common_trains:
                raise ValueError('At the moment the station is unreachable from there')
            common_elements.append(common_trains)
        print(common_elements)


        chosen_trains = []
        if len(common_elements) == 1:
            set_n = common_elements[0]
            if len(set_n) == 1:
                chosen_trains.append(set_n[0])
            else:
                if common_elements.index(set_n) != 1 and common_elements.index(set_n) != len(common_elements)-1:
                    common_element_previous = set(set_n)&set(common_elements[i-1])
                    common_element_successive = set(set_n)&set(common_elements[i+1])
                    if common_element_previous:
                        chosen_trains.append(list(common_element_previous)[0])
                    else:
                        if common_element_successive:
                            chosen_trains.append(list(common_element_successive)[0])
                        else:
                            chosen_trains.append(set_n[0])
                elif common_elements.index(set_n) == 1:
                    common_element_successive = set(set_n) & set(common_elements[i + 1])
                    if common_element_successive:
                        chosen_trains.append(list(common_element_successive)[0])
                    else:
                        chosen_trains.append(set_n[0])
                else:
                    common_element_previous = set(set_n) & set(common_elements[i - 1])
                    if common_element_previous:
                        chosen_trains.append(list(common_element_previous)[0])
                    else:
                        chosen_trains.append(set_n[0])
        else:
            for i in range(0, len(common_elements)-1):
                print(i)
                set_n = common_elements[i]
                print(set_n)
                if len(set_n) == 1:
                    chosen_trains.append(set_n[0])
                else:
                    if common_elements.index(set_n) != 1 and common_elements.index(set_n) != len(common_elements)-1:
                        common_element_previous = set(set_n)&set(common_elements[i-1])
                        common_element_successive = set(set_n)&set(common_elements[i+1])
                        if common_element_previous:
                            chosen_trains.append(list(common_element_previous)[0])
                        else:
                            if common_element_successive:
                                chosen_trains.append(list(common_element_successive)[0])
                            else:
                                chosen_trains.append(set_n[0])
                    elif common_elements.index(set_n) == 1:
                        common_element_successive = set(set_n) & set(common_elements[i + 1])
                        if common_element_successive:
                            chosen_trains.append(list(common_element_successive)[0])
                        else:
                            chosen_trains.append(set_n[0])
                    else:
                        common_element_previous = set(set_n) & set(common_elements[i - 1])
                        if common_element_previous:
                            chosen_trains.append(list(common_element_previous)[0])
                        else:
                            chosen_trains.append(set_n[0])

        seat_reservations = []
        if also_reserve_seats:
            query2 = 'SELECT capacity FROM Train WHERE train_id = %s;'
            for t_id in chosen_trains:
                cursor.execute(query2, (t_id,))
                capacity = cursor.fetchone()
                if capacity[0] > 0:
                    query3 = 'UPDATE Train SET capacity = capacity - 1 WHERE train_id = %s;'
                    cursor.execute(query3, (t_id,))
                    seat_reserved = 'YES'
                    seat_reservations.append(seat_reserved)
                else:
                    seat_reserved = 'NO'
                    seat_reservations.append(seat_reserved)
        else:
            for i in range(len(chosen_trains)):
                seat_reservations.append('NO')

        count = 0
        for element in seat_reservations:
            if element == 'YES':
                count += 1

        total_price += count*2

        cursor.execute(query1, (user_email, total_price, dep_date, from_station, to_station))

        query4 = 'SELECT booking_id FROM Bookings WHERE user_email = %s AND dep_date = %s AND from_station= %s AND to_station = %s'
        cursor.execute(query4, (user_email, dep_date, from_station, to_station))
        Booking_id = cursor.fetchall()[0][0]
        print(Booking_id)
        print(chosen_trains)
        query5 = 'INSERT INTO Seat_reservation(booking_id, train_id, seat_reservation) VALUES (%s, %s, %s)'

        i = 0
        for train_id in chosen_trains:
            seat_reservation = seat_reservations[i]
            cursor.execute(query5, (Booking_id, train_id, seat_reservation))
            print(Booking_id, train_id, seat_reservation)
            i += 1
        mariadb.commit()
        print('ticket was bought successfully')

    def get_purchase_history(self, user_email: str) -> List:
        """
        Access Purchase History

        Registered users can list the history of their past purchases, including the starting and ending stations, the day/time, total price, and for each connection, the price and whether they reserved a seat.
        The purchase history is always represented in descending starting time (at the top the most recent trips).

        If the user is not registered, the list is empty
        """
        connection = self.rdbms_connection
        cursor = connection.cursor(dictionary=True)
        #query1 = 'SELECT email FROM User WHERE email = %s'
        #cursor.execute(query1, (user_email, ))
        #u_email = cursor.fetchall()
        query_2 = 'SELECT * FROM Bookings JOIN Seat_reservation ON Bookings.Booking_id = Seat_reservation.Booking_id WHERE user_email = %s ORDER BY dep_date DESC;'
        cursor.execute(query_2, (user_email, ))
        records = cursor.fetchall()
        booking_history = []
        for record in records:
            booking_history.append(record)
        return booking_history

    ########################################################################
    # Admin Features:
    ########################################################################

    # Add and remove users
    def add_user(self, user_email: str, user_details) -> None:
        """
        Add a new user to the system with given email and details.
        Email format: <Recipient name>@<Domain name><top-level domain>
        See: https://knowledge.validity.com/s/articles/What-are-the-rules-for-email-address-syntax?language=en_US

        Raise a ValueError if the email has invalid format.
        Raise a ValueError if the user already exists
        """
        email_regex = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'

        if not re.match(email_regex, user_email):
            raise ValueError("Invalid email format")

        email = user_email
        name = user_details[0]
        user_status = user_details[1]
        connection = self.rdbms_admin_connection
        cursor = connection.cursor(dictionary=True)
        try:
            query = 'SELECT * FROM User WHERE email = %s'
            cursor.execute(query, (user_email,))
            existing_user = cursor.fetchone()

            if existing_user:
                raise ValueError("User already exists")

            query1 = 'INSERT INTO User(name, email, user_status) VALUES (%s, %s, %s);'
            cursor.execute(query1, (name, email, user_status))
            connection.commit()

        except mysql.connector.Error as e:
            # Rollback the transaction if any error occurs
            connection.rollback()
            print(f"Error adding user: {e}")



    def delete_user(self, user_email: str) -> None:
        """
        Delete the user from the db if the user exists.
        The method should also delete any data related to the user (past/future tickets and seat reservations)
        """
        email_regex = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'

        if not re.match(email_regex, user_email):
            raise ValueError("Invalid email format")

        connection = self.rdbms_admin_connection
        cursor = connection.cursor(dictionary=True)
        try:
            query = 'DELETE FROM User WHERE email = %s;'
            cursor.execute(query, (user_email,))
            connection.commit()

        except mysql.connector.Error as e:
            connection.rollback()
            print(f"Error deleting user: {e}")


    # Deleting a train should ensure consistency! Reservations are cancelled, schedules/trips are cancelled, etc.

    def add_train(self, train_id, train_capacity: int, train_status: str) -> TraitsKey:
        """
        Add new trains to the system with given code.

        Raise a ValueError if the train already exists
        """
        if train_status != 'OPERATIONAL' and train_status != 'DELAYED' and train_status != 'BROKEN':
            raise ValueError('status is not valid')
        connection = self.rdbms_admin_connection
        cursor = connection.cursor(dictionary=True)
        try:
            query = 'INSERT INTO Train(train_id ,capacity, train_status) VALUES (%s, %s, %s);'
            cursor.execute(query, (train_id, train_capacity, train_status))
            connection.commit()

            return train_id

        except mysql.connector.Error as e:
            connection.rollback()
            print(f"Error adding train: {e}")

    def update_train_details(self, train_key: TraitsKey, train_capacity: Optional[int] = None,
                             train_status: Optional[TrainStatus] = None) -> None:
        """
        Update the details of existing train if specified (i.e., not None), otherwise do nothing.
        """
        connection = self.rdbms_admin_connection
        cursor = connection.cursor(dictionary=True)

        query = 'SELECT * FROM Train WHERE train_id = %s;'
        cursor.execute(query, (train_key, ))
        train = cursor.fetchall()  # list
        print(type(train))
        if train is None:
            raise ValueError("invalid ID")

        try:
            if train_capacity is not None and train_status is None:
                query = 'UPDATE Train SET capacity = %s WHERE train_id = %s;'
                cursor.execute(query, (train_capacity, train_key))
            elif train_capacity is None and train_status is not None:
                query = 'UPDATE Train SET train_status = %s WHERE train_id = %s;'
                cursor.execute(query, (train_status, train_key))
            elif train_capacity is not None and train_status is not None:
                query = 'UPDATE Train SET capacity = %s, train_status = %s WHERE train_id = %s;'
                cursor.execute(query, (train_capacity, train_status, train_key))

            connection.commit()
        except mysql.connector.Error as e:
            connection.rollback()
            print(f"Error updating train: {e}")


    def delete_train(self, train_key: TraitsKey) -> None:
        """
        Drop the train from the system. Note that all its schedules, reservations, etc. must be also dropped.
        """
        connection = self.rdbms_admin_connection
        cursor = connection.cursor(dictionary=True)
        try:
            query = 'DELETE FROM Train WHERE train_id = %s;'
            cursor.execute(query, (train_key,))
            connection.commit()

        except mysql.connector.Error as e:
            connection.rollback()
            print(f"Error deleting train: {e}")

    def add_train_station(self, train_station_name: str) -> TraitsKey:
        """
        Add a train station
        Duplicated are not allowed, raise ValueError
        """
        connection = self.rdbms_admin_connection
        cursor = connection.cursor(dictionary=True)

        try:
            query = 'INSERT INTO Station(station_name) VALUES (%s);'
            cursor.execute(query, (train_station_name, ))
            connection.commit()
            query2 = 'SELECT station_id FROM Station WHERE station_name = %s;'
            cursor.execute(query2, (train_station_name, ))
            id = cursor.fetchone()
            id = id['station_id']
            with self.neo4j_driver.session() as session:
                def create_station(tx, id, train_station_name):
                    query1 = """
                        CREATE (s1:Station {Station_id: $id, Station_name: $train_station_name})"""

                    tx.run(query1, id=id, train_station_name=train_station_name)
                session.execute_write(create_station, id, train_station_name)

            return id

        except mysql.connector.Error as e:
            connection.rollback()
            print(f"Error adding station: {e}")


    def connect_train_stations(self, starting_train_station_key: TraitsKey, ending_train_station_key: TraitsKey,
                               travel_time_in_minutes: int, waiting_time_in_minutes: int) -> None:
        """
        Connect to train station so trains can travel on them
        Raise ValueError if any of the stations does not exist
        Raise ValueError for invalid travel_times
        """
        if travel_time_in_minutes <= 0:
            raise ValueError("Invalid travel time")

        if starting_train_station_key == ending_train_station_key:
            raise ValueError('cannot connect a station to itself')

        connection = self.rdbms_admin_connection
        cursor = connection.cursor(dictionary=True)

        try:
            query = 'SELECT * FROM Station WHERE station_id = %s'
            cursor.execute(query, (starting_train_station_key, ))
            s1 = cursor.fetchone()
            if s1 is None:
                raise ValueError(f"Starting station {starting_train_station_key} does not exist")

            cursor.execute(query, (ending_train_station_key, ))
            s2 = cursor.fetchone()
            if s2 is None:
                raise ValueError(f"Ending station {ending_train_station_key} does not exist")

            def check_if_connection_exist(tx, starting_train_station_key, ending_train_station_key):
                query0 = """
                    MATCH (s1:Station {Station_id: $starting_station_id})-[r:CONNECTED_TO*]->(s2:Station {Station_id: $ending_station_id})
                    RETURN r;
                """
                result = tx.run(query0, starting_station_id=starting_train_station_key,
                                ending_station_id=ending_train_station_key)
                relationships = list(result)
                if relationships:
                    raise ValueError('stations already connected')

            with self.neo4j_driver.session() as session:

                session.execute_write(check_if_connection_exist, starting_train_station_key, ending_train_station_key)
                def create_relationship(tx, starting_train_station_key, ending_train_station_key, travel_time_in_minutes, waiting_time_in_minutes):
                    query1 = """
                        MATCH (s1:Station {Station_id: $starting_station_id}),(s2:Station {Station_id: $ending_station_id})
                        CREATE (s1)-[:CONNECTED_TO {travel_time_in_minutes: $minutes, waiting_time: $minutes_w}]->(s2);"""

                    tx.run(query1, starting_station_id=starting_train_station_key, ending_station_id=ending_train_station_key,
                            minutes=travel_time_in_minutes, minutes_w=waiting_time_in_minutes)
                session.execute_write(create_relationship, starting_train_station_key, ending_train_station_key, travel_time_in_minutes, waiting_time_in_minutes)

        except mysql.connector.Error as e:
            connection.rollback()
            print(f"Error in RDBMS operation: {e}")
        except exceptions.Neo4jError as e:
            print(f"Error in Neo4j operation: {e}")
        finally:
            cursor.close()

    def add_schedule(self, train_key: TraitsKey,
                     stops: List[Tuple[TraitsKey, int]],  # [station_key, waiting_time]
                     valid_from_day: int, valid_from_month: int, valid_from_year: int,
                     valid_until_day: int, valid_until_month: int, valid_until_year: int) -> None:
        """
        Create a schedule for a give train.
        The schedule must have at least two stops, cannot connect the same station directly but can create "rings"
        Stops must correspond to existing stations
        Consecutive stops must be connected stations.
        starting hours and minutes defines when this schedule is active
        Validity dates must ensure that valid_from is in the past w.r.t. valid_until
        In case of error, raise ValueError
        """
        if len(stops) < 2:
            raise ValueError("A schedule must have at least two stops")

        if stops[-1][1] < 10:
            raise ValueError('The stop duration of the last stop has to be at least 10 minutes')
        # Check date validity
        from_date = datetime.date(valid_from_year, valid_from_month, valid_from_day)
        until_date = datetime.date(valid_until_year, valid_until_month, valid_until_day)
        if from_date > until_date:
            raise ValueError("valid_from date must be before valid_until date")

        connection = self.rdbms_admin_connection
        cursor = connection.cursor(dictionary=True)
        query = 'SELECT * FROM Train WHERE train_id = %s;'
        cursor.execute(query, (train_key, ))
        train = cursor.fetchall()
        if not train:
            raise ValueError("The train does not exist")

        station_query = 'SELECT * FROM Station WHERE station_id = %s;'
        for stop in stops:
            cursor.execute(station_query, (stop[0], ))
            station = cursor.fetchone()
            if not station:
                raise ValueError(f"Station with id {stop} does not exist")

        for i in range(len(stops) - 1):
            start_station = stops[i][0]
            end_station = stops[i + 1][0]
            if start_station == end_station:
                raise ValueError("Consecutive stops cannot be the same station")

            def check_if_connection_exist(tx, starting_train_station_key, ending_train_station_key):
                query0 = """
                    MATCH (s1:Station {Station_id: $starting_station_id})-[r:CONNECTED_TO*]->(s2:Station {Station_id: $ending_station_id})
                    RETURN r;
                """
                result = tx.run(query0, starting_station_id=starting_train_station_key,
                                ending_station_id=ending_train_station_key)
                relationships = list(result)
                return relationships

            with self.neo4j_driver.session() as session:
                result = session.execute_write(check_if_connection_exist, start_station, end_station)
                if result is None:
                    raise ValueError(f"Stations {start_station} and {end_station} are not connected")

        try:
            print(len(stops))
            for stop in stops:
                insert_query = """
                    INSERT INTO Schedule (station_id, train_id, stop_duration, valid_from, valid_untill)
                    VALUES (%s, %s, %s, %s, %s);
                    """
                cursor.execute(insert_query, (
                    stop[0],
                    train_key,
                    stop[1],
                    from_date,
                    until_date
                ))
            connection.commit()
        except Exception as e:
            connection.rollback()
            raise ValueError(f"Error inserting schedule: {e}")

        print("Schedule added successfully")


rdbms_connection = mysql.connector.connect(
        host="localhost",
        user="root",
        password="root-pass",
        database="traits_db"
    )
rdbms_admin_connection = mysql.connector.connect(
        host="localhost",
        user='traits-admin',
        password='traits-admin-pass',
        database='traits_db'
    )

neo4j_driver = GraphDatabase.driver("bolt://localhost:7687", auth=None)

traits = Traits(rdbms_connection, rdbms_admin_connection, neo4j_driver)
result = traits.get_train_current_status(19)
print(result)
result2 = traits.get_purchase_history('jhon@gmail.com')
print(result2)


'''try:
    traits.add_user('benedetta@gmail.com', ['Benedetta', 'REGISTERED'])
    print("User added successfully")
except ValueError as e:
    print(f"ValueError: {e}")
except mysql.connector.Error as e:
    print(f"Database error: {e}")

try:
    traits.delete_user('benedetta@gmail.com')
    print('user_deleted successfully')
except ValueError as e:
    print(f"ValueError: {e}")
except mysql.connector.Error as e:
    print(f"Database error: {e}")'''
'''
try:
    traits.add_train(123, 'OPERATIONAL')
    print('train_added successfully')
except ValueError as e:
    print(f"ValueError: {e}")
except mysql.connector.Error as e:
    print(f"Database error: {e}")
'''
'''
try:
    traits.update_train_details(1, 450)
    print('train_updated successfully')
    traits.update_train_details(5, 34, 'BROKEN')
except ValueError as e:
    print(f"ValueError: {e}")
except mysql.connector.Error as e:
    print(f"Database error: {e}")
'''

'''try:
    traits.delete_train(1)
    print('train_deleted successfully')
except ValueError as e:
    print(f"ValueError: {e}")
except mysql.connector.Error as e:
    print(f"Database error: {e}")'''

'''try:
    traits.add_train_station('Station G')
    print('station_added successfully')
    #traits.add_train_station('Station A')
except ValueError as e:
    print(f"ValueError: {e}")
except mysql.connector.Error as e:
    print(f"Database error: {e}")'''


'''try:
    traits.connect_train_stations(2, 3, 8, 5)
    print('station_added successfully')
except ValueError as e:
    print(f"ValueError: {e}")
except mysql.connector.Error as e:
    print(f"Database error: {e}")'''


'''try:
    traits.add_schedule(
        train_key=3,
        stops=[(3, 5), (2, 10)],
        valid_from_day=1, valid_from_month=1, valid_from_year=2023,
        valid_until_day=31, valid_until_month=12, valid_until_year=2023
    )
    print('Schedule added successfully')
except ValueError as e:
    print(f"ValueError: {e}")
except mysql.connector.Error as e:
    print(f"Database error: {e}")'''



'''try:
    connections = traits.search_connections(1, 2, 20, 11, 2020, is_departure_time=True, sort_by=SortingCriteria.OVERALL_TRAVEL_TIME, is_ascending=True, limit=5)
    for connection in connections:
        print(connection)
except ValueError as e:
    print(f"ValueError: {e}")
except Exception as e:
    print(f"Error: {e}")'''

'''
try:
    connections = traits.buy_ticket('alice@example.com', {'1 to 2': (2, datetime.date(2023, 1, 1), datetime.date(2023, 12, 31))})
    for connection in connections:
        print(connection)
except ValueError as e:
    print(f"ValueError: {e}")
except Exception as e:
    print(f"Error: {e}")'''

'''
try:
    traits.buy_ticket('alice@example.com', {2: {'departure_date': datetime.date(2020, 11, 20), 'waiting times': [5], 'travel_times': [8], 'total waiting time': 5, 'total travel time': 8, 'station_id': [1, 2], 'number_of_intermediate_stops': 0, 'total_price': 4.0}})
    print('ticket bought')
except ValueError as e:
    print(f"ValueError: {e}")
except Exception as e:
    print(f"Error: {e}")'''

'''try:
    traits_utility = TraitsUtility(rdbms_connection, rdbms_admin_connection, neo4j_driver)
    traits_utility.get_all_schedules()
except ValueError as e:
    print(f"ValueError: {e}")
except Exception as e:
    print(f"Error: {e}")'''