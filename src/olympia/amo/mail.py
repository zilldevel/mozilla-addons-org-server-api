from django.core import mail
from django.core.mail.backends.base import BaseEmailBackend

import olympia.core.logger
from olympia.amo.models import FakeEmail
from olympia.users.models import UserProfile


log = olympia.core.logger.getLogger('z.amo.mail')


class DevEmailBackend(BaseEmailBackend):
    """Log emails in the database, send allowed addresses for real though.

    Used for development environments when we don't want to send out
    real emails. This gets swapped in as the email backend when
    `settings.SEND_REAL_EMAIL` is disabled.

    BUT even if `settings.SEND_REAL_EMAIL` is disabled, if the targeted
    email address is in `dev_email` group users, the email will be sent.
    """

    force_send_mail_group = 'Force Send Mail'

    def send_messages(self, messages):
        """Save a `FakeEmail` object viewable within the admin.

        If one of the target email addresses is in
        group named `Group.force_send_mail_group`, it send a real email message.
        """
        log.info('Sending dev mail messages.')
        qa_messages = []
        force_send_emails = UserProfile.objects.filter(
            groups__name=self.force_send_mail_group
        ).values_list('email', flat=True)

        for msg in messages:
            FakeEmail.objects.create(message=msg.message().as_string())
            qa_emails = set(msg.to).intersection(force_send_emails)
            if qa_emails:
                if len(msg.to) != len(qa_emails):
                    # We need to replace the recipients with the QA
                    # emails only prior to send the message for real.
                    # We don't want to send real emails to people if
                    # they happen to also be in the recipients together
                    # with white-listed emails
                    msg.to = list(qa_emails)
                qa_messages.append(msg)
        if qa_messages:
            log.info('Sending real mail messages to QA.')
            connection = mail.get_connection()
            connection.send_messages(qa_messages)
        return len(messages)
