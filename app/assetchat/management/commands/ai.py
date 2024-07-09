from argparse import ArgumentParser

from assetchat.file_deletion import enumerate_stale_vectors
from django.contrib.auth import get_user_model
from django.core.management import BaseCommand

RESET_USAGE_LIMIT_ACTION = 0
ENUMERATE_STALE_VECTORS_ACTION = 1


class Command(BaseCommand):
    def add_arguments(self, parser: ArgumentParser):
        subparsers = parser.add_subparsers()

        reset_usage_limits_subparser = subparsers.add_parser(
            "reset_usage_limits",
            help="Reset usage limits for a specific user.",
        )
        reset_usage_limits_subparser.set_defaults(
            action=RESET_USAGE_LIMIT_ACTION
        )
        reset_usage_limits_subparser.add_argument(
            "user_id", type=int, metavar="N", help="The target user's ID."
        )

        enumerate_stale_vectors_subparser = subparsers.add_parser(
            "enumerate_stale_vectors",
            help="Find stale vectors and mark them for deletion.",
        )
        enumerate_stale_vectors_subparser.set_defaults(
            action=ENUMERATE_STALE_VECTORS_ACTION
        )

    def reset_usage_limits(self, user_id: int):
        user = get_user_model().objects.get(pk=user_id)
        user.ai_usage_limit.reset_limits()
        self.stdout.write(f"Limits for {user.email} has been reset.")

    def enumerate_stale_vectors(self):
        enumerate_stale_vectors()
        self.stdout.write("Stale vectors marked for deletion.")

    def handle(self, *args, **options):
        action = options["action"]

        if action == RESET_USAGE_LIMIT_ACTION:
            user_id = options["user_id"]
            self.reset_usage_limits(user_id)
        elif action == ENUMERATE_STALE_VECTORS_ACTION:
            pass
