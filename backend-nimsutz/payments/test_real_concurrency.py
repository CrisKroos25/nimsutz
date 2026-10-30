"""Los tres escenarios de concurrencia usando el motor comercial real."""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from django.db import connections
from subscriptions import services
from subscriptions.errors import SubscriptionError
from . import test_concurrency as fixtures
from .errors import PaymentError
from .services import execute_checkout


class RealConcurrentCheckoutTests(fixtures.ConcurrentCheckoutTests):
    def setUp(self):
        super().setUp()
        self.version = services.get_current_version('basic')
        quote = services.prepare_quote(user=self.user, operation='contract', plan_version_id=self.version.pk)
        self.quote_id = quote.pk

    def run_concurrent(self, users, keys):
        barrier = Barrier(2)
        quotes = {self.user.pk: self.quote_id}
        for user in users:
            if user.pk not in quotes:
                quotes[user.pk] = services.prepare_quote(user=user, operation='contract', plan_version_id=self.version.pk).pk
        def execute(args):
            user, key = args
            try:
                barrier.wait(timeout=10)
                return execute_checkout(user=user, quote_id=quotes[user.pk], operation_key=key, card_data=self.card_data)
            except (PaymentError, SubscriptionError) as error:
                return error.code
            finally:
                connections.close_all()
        with ThreadPoolExecutor(max_workers=2) as executor:
            return list(executor.map(execute, zip(users, keys)))
