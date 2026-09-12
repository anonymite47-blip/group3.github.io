"""
SMS sending for phone verification.

By default (no SEMAPHORE_API_KEY set), this just prints the message to
the console/server log — useful for local development and for your
defense demo without needing to pay for real SMS credits.

To send real SMS messages (e.g. via Semaphore, a common PH SMS gateway:
https://semaphore.co), set the SEMAPHORE_API_KEY environment variable.
No other code changes are needed — send_sms() will automatically switch
to sending live once the key is present.
"""
import os
import random

SEMAPHORE_API_KEY = os.environ.get('SEMAPHORE_API_KEY')


def generate_otp():
    return f'{random.randint(0, 999999):06d}'


def send_sms(phone_number, message):
    """
    Returns True if an actual SMS was sent via a real gateway,
    False if it fell back to console logging (dev mode).
    """
    if SEMAPHORE_API_KEY:
        import requests
        try:
            requests.post(
                'https://api.semaphore.co/api/v4/messages',
                data={'apikey': SEMAPHORE_API_KEY, 'number': phone_number, 'message': message},
                timeout=10,
            )
            return True
        except Exception as e:
            print(f'[SMS SEND FAILED] {e} — falling back to console log.')

    print(f'[DEV SMS to {phone_number}]: {message}')
    return False


def is_dev_mode():
    return not bool(SEMAPHORE_API_KEY)
