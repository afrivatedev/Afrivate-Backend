"""
Test custom Django management commands.
"""

from unittest.mock import patch  # this is the decorator that would
# enable us mock.

from psycopg2 import OperationalError as psycopg2Error

# importing various errors that would make us simulate
# various connection errors when trying to connect to DB
from django.core.management import call_command
from django.db.utils import OperationalError
from django.test import SimpleTestCase


@patch('database.management.commands.wait_for_db.Command.check')
class CommandTest(SimpleTestCase):
    """Test commands"""

    def test_wait_for_db_ready(self, patched_check):
        """Test waiting for database and mocks the situation
        where the db is ready immediately"""
        patched_check.return_value = True

        call_command('wait_for_db')

        patched_check.assert_called_once_with(databases=['default'])

    @patch('time.sleep')
    def test_wait_for_db_delay(self, patched_sleep, patched_check):
        """Test waiting for the database when getting OperationalError
        and mocks when it throwing errors"""
        patched_check.side_effect = [psycopg2Error] * 2 + \
                                    [OperationalError] * 3 + [True]

        call_command('wait_for_db')

        self.assertEqual(patched_check.call_count, 6)
        patched_check.assert_called_with(databases=['default'])
