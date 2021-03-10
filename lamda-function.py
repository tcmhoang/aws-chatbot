import time
import os
import logging
import json
import boto3
import uuid
import dateutil.parser
import re
import math

# Logger
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

# Init DynamoDB params
MOVIE_TABLE = os.getenv('MOVIE_TABLE', default='DummyMovie')
ORDER_TABLE = os.getenv('ORDER_TABLE', default='DummyOrder')

# --- Helpers that build all of the responses ---


def elicit_slot(session_attributes, intent_name, slots, slot_to_elicit, message):
    return {
        'sessionAttributes': session_attributes,
        'dialogAction': {
            'type': 'ElicitSlot',
            'intentName': intent_name,
            'slots': slots,
            'slotToElicit': slot_to_elicit,
            'message': message
        }
    }


def confirm_intent(session_attributes, intent_name, slots, message):
    return {
        'sessionAttributes': session_attributes,
        'dialogAction': {
            'type': 'ConfirmIntent',
            'intentName': intent_name,
            'slots': slots,
            'message': message
        }
    }


def close(session_attributes, fulfillment_state, message):
    response = {
        'sessionAttributes': session_attributes,
        'dialogAction': {
            'type': 'Close',
            'fulfillmentState': fulfillment_state,
            'message': message
        }
    }

    return response


def delegate(session_attributes, slots):
    return {
        'sessionAttributes': session_attributes,
        'dialogAction': {
            'type': 'Delegate',
            'slots': slots
        }
    }


# --- Helper Functions ---

def rreplace(s: str, old: str, new: str, occ: int):
    return new.join(s.rsplit(old, occ))


def parse_int(n):
    try:
        return int(n)
    except ValueError:
        return math.nan


def ltostr(a: list):
    strList = ', '.join(map(str, a))
    strList = rreplace(strList, ', ', ' and ', 1)
    return strList


def get_slots(intent_request):
    return intent_request['currentIntent']['slots']


def build_validation_result(is_valid: bool, violated_slot: str, message_content: str):
    if message_content is None:
        return{
            "isValid": is_valid,
            "violatedSlot": violated_slot
        }
    return{
        "isValid": is_valid,
        "violatedSlot": violated_slot,
        "message":
        {
            "contentType": "PlainText",
            "content": message_content
        }
    }


""" --- Main handler --- """


def lambda_handler(event, context):
    """
    Route the incoming request based on intent.
    The JSON body of the request is provided in the event slot.
    """
    # By default, treat the user request as coming from the Pacific timezone.
    os.environ['TZ'] = 'America/Los_Angeles'
    time.tzset()
    logger.info(f'Received event: {event} from {event['bot']['name']}')

    return dispatch(event)
