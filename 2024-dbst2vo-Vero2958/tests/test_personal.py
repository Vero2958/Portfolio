import datetime

from traits.implementation import TraitsUtility
import pytest
from neo4j import GraphDatabase
import mysql.connector
from traits.implementation import TraitsUtility

import unittest
from unittest.mock import Mock, patch
import mysql.connector
from neo4j import GraphDatabase
from traits.interface import TraitsKey, SortingCriteria, TrainStatus
from traits.implementation import Traits, TraitsUtility
from traits.interface import BASE_USER_PASS, ADMIN_USER_PASS, BASE_USER_NAME, ADMIN_USER_NAME


def test_add_user_get_all_users_delete_user():
    rdbms_connection = mysql.connector.connect(
        host="localhost",
        user="user1",
        password="password",
        database="traits_db"
    )
    rdms_admin_connection = mysql.connector.connect(
        host="localhost",
        user='traits-admin',
        password='traits-admin-pass',
        database='traits_db'
    )

    neo4j_driver = GraphDatabase.driver("bolt://localhost:7687", auth=None)

    try:
        traits_utility = TraitsUtility(rdbms_connection, rdms_admin_connection, neo4j_driver)
        traits = Traits(rdbms_connection, rdms_admin_connection, neo4j_driver)
        users = traits_utility.get_all_users()

        if users:
            for user in users:
                print(user)

        length = len(users)
        traits.add_user('Veronica@example.com', ['Veronica', 'ADMIN'])
        rdbms_connection.commit()

        users2 = traits_utility.get_all_users()

        len2 = len(users2)

        if users2:
            for user in users2:
                print(user)

        traits.delete_user('Veronica@example.com')
        rdbms_connection.commit()

        users3 = traits_utility.get_all_users()
        len3 = len(users3)

        assert length > 0
        assert len(users2) == length + 1
        assert len3 == len2-1

    except mysql.connector.Error as e:
        print(f"Database connection error: {e}")

def test_get_all_schedules_add_schedule():
    rdbms_connection = mysql.connector.connect(
        host="localhost",
        user="root",
        password="root-pass",
        database="traits_db"
    )
    rdms_admin_connection = mysql.connector.connect(
        host="localhost",
        user='traits-admin',
        password='traits-admin-pass',
        database='traits_db'
    )

    neo4j_driver = GraphDatabase.driver("bolt://localhost:7687", auth=None)
    try:
        traits_utility = TraitsUtility(rdbms_connection, rdms_admin_connection, neo4j_driver)
        traits = Traits(rdbms_connection, rdms_admin_connection, neo4j_driver)
        traits.add_train(12, 124, 'OPERATIONAL')
        traits.add_schedule(3, [(3, 5), (2, 10)], 20, 8, 2024, 15, 12, 2024)

        rdbms_connection.commit()
        rdms_admin_connection.commit()

        schedules = traits_utility.get_all_schedules()
        assert len(schedules) > 0

        traits.delete_train(12)
        traits.rdbms_connection.commit()

    except mysql.connector.Error as e:
        print(f"Database connection error: {e}")



def test_add_train_station_add_train_connect_train_station_add_schedule_delete_train_update_train_details_get_train_current_status_search_connection():
    rdbms_connection = mysql.connector.connect(
        host="localhost",
        user="root",
        password="root-pass",
        database="traits_db"
    )
    rdms_admin_connection = mysql.connector.connect(
        host="localhost",
        user='traits-admin',
        password='traits-admin-pass',
        database='traits_db'
    )

    neo4j_driver = GraphDatabase.driver("bolt://localhost:7687", auth=None)
    try:
        traits = Traits(rdbms_connection, rdms_admin_connection, neo4j_driver)
        cursor = traits.rdbms_connection.cursor(dictionary=True)
        id1 = traits.add_train_station('Test_Station_1')
        id2 = traits.add_train_station('Test_Station_2')
        traits.rdbms_connection.commit()

        assert id1 is not None
        assert id2 is not None

        traits.connect_train_stations(id1, id2, 20, 10)

        connection = traits.search_connections(id1, id2)
        assert len(connection) == 1
        print(connection)
        assert set(connection[0][1]['station_id']) == {id1, id2}
        train_id = traits.add_train(20, 200, 'OPERATIONAL')

        query1 = 'SELECT train_id FROM Train WHERE train_id = %s'
        cursor.execute(query1, (train_id, ))
        train_id = cursor.fetchone()
        print(train_id)
        train_id = train_id['train_id']

        assert train_id is not None

        traits.add_schedule(train_id, [(id1, 3), (id2, 10)], 20, 8, 2024, 15, 12, 2024)
        traits.rdbms_connection.commit()
        status = traits.get_train_current_status(train_id)
        assert status[0] == 'OPERATIONAL'

        traits.update_train_details(train_id, None, 'BROKEN')
        traits.rdbms_connection.commit()
        status2 = traits.get_train_current_status(train_id)
        assert status2[0] == 'BROKEN'

        traits.delete_train(train_id)
        traits.rdbms_connection.commit()

        cursor.execute(query1, (train_id, ))
        train_id = cursor.fetchone()
        assert train_id is None

        query2 = 'DELETE FROM Station WHERE station_id = %s OR station_id = %s;'
        cursor.execute(query2, (id1, id2))
        traits.rdbms_connection.commit()

    except mysql.connector.Error as e:
        print(f"Database connection error: {e}")


def test_buy_ticket_get_purchase_history():
    rdbms_connection = mysql.connector.connect(
        host="localhost",
        user="root",
        password="root-pass",
        database="traits_db"
    )
    rdms_admin_connection = mysql.connector.connect(
        host="localhost",
        user='traits-admin',
        password='traits-admin-pass',
        database='traits_db'
    )

    neo4j_driver = GraphDatabase.driver("bolt://localhost:7687", auth=None)
    try:
        traits = Traits(rdbms_connection, rdms_admin_connection, neo4j_driver)
        cursor = traits.rdbms_connection.cursor(dictionary=True)

        traits.add_user('Veronica@example.com', ['Veronica', 'ADMIN'])
        rdbms_connection.commit()
        traits.buy_ticket('Veronica@example.com', {2: {'departure_date': datetime.date(2020, 11, 20), 'waiting times': [5], 'travel_times': [8], 'total waiting time': 5, 'total travel time': 8, 'station_id': [3, 2], 'number_of_intermediate_stops': 0, 'total_price': 4.0}})
        purchase_hist = traits.get_purchase_history('Veronica@example.com')

        assert purchase_hist is not None
        assert len(purchase_hist) == 1
        print(purchase_hist)
        traits.delete_user('Veronica@example.com')
        rdbms_connection.commit()

    except mysql.connector.Error as e:
        print(f"Database connection error: {e}")

if __name__ == "__main__":
    import pytest

    pytest.main()






