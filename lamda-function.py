import time
import os
import logging
import json
import boto3
from boto3.dynamodb.conditions import Key, Attr
import uuid
import dateutil.parser
import datetime
import re
import math

# Logger
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

# Establish credentials
# DynamoDB tables, read lambda function environment variables or initialize with defaults if they not exist.
session_var = boto3.session.Session()
credentials = session_var.get_credentials()

# Init DynamoDB params
MOVIE_TABLE = os.getenv('MOVIE_TABLE', default='DummyMovie')
ORDER_TABLE = os.getenv('ORDER_TABLE', default='DummyOrder')

# Init DynamoDB Client
dynamodb = boto3.client("dynamodb")
sns = boto3.client('sns')

##############################################################################################
# Functions

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

def safe_ex(func):
    """
    Call passed in function in try block. If KeyError is encountered return None.
    This function is intended to be used to safely access dictionary.

    Note that this function would have negative impact on performance.
    """

    try:
        return func()
    except KeyError:
        return None


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


def isvalid_date(date):
    """
    Called to check date arg is in valid format
    """
    try:
        dateutil.parser.parse(date)
        return True
    except ValueError:
        return False


def isvalid_mobile(mobile):
    """
    Called to check mobile arg is in valid format
    """
    rule = re.compile(r'(^[+0-9]{1,3})*([0-9]{10,11}$)')
    return True if rule.match(mobile) else False


""" --- Functions that interact with other services (backend functions) --- """


def get_movie_names() -> list:
    """
    Called to get a list of available movie.
    """

    # Getting the Movie.  In a real application, this would likely involve a call to a backend service.
    return [name.lower() for name in ['Clarie', 'Wanda Vision']]


def get_movie_id(movie_name: str, theater_name: str):
    """
    Called to read the movieId from DynamoDB refering to a specific flavor of a movie.
    """
    movie_details = dynamodb.query(
        TableName=MOVIE_TABLE,
        IndexName='movieName-theaterName-index',
        KeyConditionExpression='movieName = :mName AND theaterName = :tName',
        ExpressionAttributeValues={
            ':mName': {
                "S": movie_name
            },
            ':tName': {
                "S": theater_name
            }
        }
    )
    if len(movie_details['Items']) != 0:
        return parse_int(movie_details['Items'][0]['movieId']['N'])

    return None


def get_theater_names(movie_name: str) -> list:
    """
    Called to get a list of theater names for a specific movie.
    """
    theater_details = dynamodb.query(
        TableName=MOVIE_TABLE,
        IndexName='movieName-theaterName-index',
        KeyConditionExpression='movieName = :mName',
        ExpressionAttributeValues={
            ':mName': {
                "S": movie_name
            }
        }
    )
    logger.debug(f'Available {movie_name} in: {json.dumps(theater_details)}')
    theater_names = [str(detail['theaterName']['S']).lower()
                     for detail in theater_details['Items']]
    return theater_names


""" --- Functions that validate input --- """


def validate_movie(movie):
    """
    Called to validate the MovieName slot.
    """
    if movie is not None:
        movies = get_movie_names()

        if movie.lower() not in movies:
            movie_names = ltostr(movies)
            return build_validation_result(
                False,
                'MovieName',
                f'Showtime for the {movie} is not available. You can choose currently available movies {movie_names}.'
            )

    return build_validation_result(True, None, None)


def validate_theater(movie, theater):
    """
    Called to validate the TheaterName slot.
    """
    if theater is not None:
        theaters = get_theater_names(movie)

        if theater.lower() not in theaters:
            theater_names = ltostr(theaters)
            return build_validation_result(
                False,
                'TheaterName',
                f'Showtime in theater {theater} is not available. You can choose one from {theater_names}.'
            )
    return build_validation_result(True, None, None)


def validate_tickets_quantity(book_quantity):
    """
    Called to validate the TicketCount slot.
    """
    logger.debug(f'Quantity {book_quantity}')
    if book_quantity is not None:
        if parse_int(book_quantity) < 0:
            return build_validation_result(
                False,
                'TicketCount',
                'Sorry, you should book at least one ticket. How many tickets would you like to book?'
            )
        elif parse_int(book_quantity) > 10:
            return build_validation_result(
                False,
                'TicketCount',
                'Sorry but the maximum order quantity for online tickets is 10. Please contact us directly for larger quantity orders. How many tickets would you like to order instead?'
            )

    return build_validation_result(True, None, None)


def validate_date(date):
    """
    Called to validate the MovieDate slot.
    """
    if date is not None:
        if not isvalid_date(date):
            return build_validation_result(False, 'MovieDate', 'I did not understand date.  When would you like to watch your movie?')
        if datetime.datetime.strptime(date, '%Y-%m-%d').date() < datetime.date.today():
            return build_validation_result(False, 'MovieDate', 'Booking must be scheduled at least one day in advance.  Can you try a different date?')
        if datetime.datetime.strptime(date, '%Y-%m-%d').date() >= datetime.date.today()+datetime.timedelta(days=30):
            return build_validation_result(False, 'MovieDate', 'I can book only upto 1 month in advance. Can you try a date between {} and {}?'.format(datetime.date.today(), datetime.date.today()+datetime.timedelta(days=30)))
    return build_validation_result(True, None, None)


def validate_mobile(mobile):
    if mobile is not None and not isvalid_mobile(mobile):
        return build_validation_result(
            False,
            'Mobile',
            f'{mobile} is not a valid mobile number. Please provide a valid mobile number?'
        )

    return build_validation_result(True, None, None)


def gen_validate_res(data):
    """
    Called to get the list validate slots with all meet-up conditions.
    """
    yield validate_movie(data['MovieName'])
    yield validate_theater(data['MovieName'], data['TheaterName'])
    yield validate_date(data['MovieDate'])
    yield validate_tickets_quantity(data['TicketCount'])
    yield validate_mobile(data['Mobile'])


def validate_book(data):
    """
    Called to validate the slots in BookTickets intent.
    """
    if data is not None:
        return next((violated for violated
                     in gen_validate_res(data)
                     if not violated['isValid']), build_validation_result(True, None, None))

    return build_validation_result(True, None, None)


def place_ticket(user_id, movie_id, ticket_count):
    """
    Called when the user confirms to place an order within the BookTickets intent.
    """
    # Generate order id
    order_id = uuid.uuid4()

    logger.debug('orderId: {}, userId: {}, movieId: {}, ticketQuantity: {}'.format(
        order_id, user_id, movie_id, ticket_count))

    # Put order in DynamoDB
    dynamodb.put_item(
        TableName=ORDER_TABLE,
        Item={
            'orderId': {
                'S': str(order_id)
            },
            'userId': {
                'S': str(user_id)
            },
            'movieId': {
                'N': str(movie_id)
            },
            'ticketCount': {
                'N': str(ticket_count)
            }
        },
    )

    return order_id


def send_sns(movie_name, theater_name, movie_date, movie_time, ticket_count, mobile):
    """
    Called when the user's order is confirmed to sent a confirmation sns .
    """
    msg = 'Your booking is confirmed.\n' \
        'Summary of tickets:\n'\
        'Movie: ' + movie_name + ' ' \
        '\nTheater:' + theater_name + ' ' \
        '\nDate: ' + str(movie_date) + ' '+str(movie_time) + ' ' \
        '\nTotal ticket: ' + str(ticket_count) + ' ' \
        '\n\nThank you for booking with chatbot. '
    mobile_str = str(mobile)
    if not mobile_str.startswith('+1'):
        pass
    sns.publish(
        PhoneNumber=mobile_str,
        Message=msg
    )


""" --- Functions that control the bot's behavior (bot intent handler) --- """


def i_book_ticket(intent_request):
    """
    Called when the user triggers the BookTickets intent.
    """
    source = intent_request['invocationSource']
    slots = get_slots(intent_request)
    user_id = intent_request['userId'] if intent_request['userId'] is not None else '0'

    # Validation
    if source == 'DialogCodeHook':
        check_res = validate_book(slots)
        if not check_res['isValid']:
            slots[check_res['violatedSlot']] = None
            return elicit_slot(
                intent_request['sessionAttributes'],
                intent_request['currentIntent']['name'],
                slots,
                check_res['violatedSlot'],
                check_res['message']
            )
        output_session_attributes = intent_request['sessionAttributes'] if intent_request['sessionAttributes'] is not None else {
        }
        return delegate(output_session_attributes, get_slots(intent_request))

    # Intent fulfillment
    # get productId from DynamoDB product table
    movie_id = get_movie_id(slots['MovieName'], slots['TheaterName'])
    if movie_id is None:
        return close(
            intent_request['sessionAttributes'],
            'Fulfilled',
            {
                'contentType': 'PlainText',
                'content': f"Sorry your book of {slots['TicketCount']} tickets of {slots['TheaterName']} {slots['MovieName']} has not been placed due to a system error. "
                "Please try it again later or contact us via win@blah.com"
            }
        )

    # place order into DynamoDB order table and receive orderId in exchange
    order_id = place_ticket(user_id, movie_id, slots['TicketCount'])
    # send a confirmation sns
    send_sns(slots['MovieName'], slots['TheaterName'], slots['MovieDate'],
             slots['MovieTime'], slots['TicketCount'], slots['Mobile'])

    return close(
        intent_request['sessionAttributes'],
        'Fulfilled',
        {
            'contentType': 'PlainText',
            'content': "Thank you for ordering through our bot. "
            f"You book of {slots['TicketCount']} tickets of {slots['TheaterName']} {slots['MovieName']} has been placed and will be processed "
            f"immediately (Order ID: {order_id}). Can I help you with anything else?"
        }
    )


def i_movie_theater(intent_request):
    """
    Called when the user triggers the GetMovieTheater intent.
    """
    source = intent_request['invocationSource']
    slots = get_slots(intent_request)

    # Validation
    if source == 'DialogCodeHook':
        movieVal = validate_movie(slots['MovieName'])
        if not movieVal['isValid']:
            slots[movieVal['violatedSlot']] = None
            return elicit_slot(
                intent_request['sessionAttributes'],
                intent_request['currentIntent']['name'],
                slots,
                movieVal['violatedSlot'],
                movieVal['message']
            )
        # Otherwise, let native DM rules determine how to elicit for slots and prompt for confirmation.  Pass price
        # back in sessionAttributes once it can be calculated; otherwise clear any setting from sessionAttributes.
        output_session_attributes = intent_request['sessionAttributes'] if intent_request['sessionAttributes'] is not None else {
        }
        return delegate(output_session_attributes, get_slots(intent_request))

    # fulfillment
    theater_str = ltostr([tName.capitalize()
                          for tName in get_theater_names(slots['MovieName'])])
    return close(
        intent_request['sessionAttributes'],
        'Fulfilled',
        {
            'contentType': 'PlainText',
            'content': f'Movie {slots["MovieName"]} is offering consists of the following theater: {theater_str}.'
        }
    )


def i_help(intent_request):
    """
    Called when the user triggers the Help intent.
    """

    # Intent fulfillment
    return close(intent_request['sessionAttributes'],
                 'Fulfilled',
                 {'contentType': 'PlainText',
                  'content': "Hi this is lex, your personal assistant. "
                             "- Would you like to book movie tickets? "
                             "- or should I show you a list of available movies for "
                             "one of the theater?"})


""" --- Dispatch intents --- """


def dispatch(intent_request):
    """
    Called when the user specifies an intent for this bot.
    """

    logger.debug('dispatch userId={}, intentName={}'.format(
        intent_request['userId'], intent_request['currentIntent']['name']))

    intent_name = intent_request['currentIntent']['name']

    # Dispatch to your bot's intent handlers
    if intent_name == 'BookTickets':
        return i_book_ticket(intent_request)
    elif intent_name == 'GetMovieTheater':
        return i_movie_theater(intent_request)
    elif intent_name == 'Help':
        return i_help(intent_request)

    raise Exception('Intent with name ' + intent_name + ' not supported')


""" --- Main handler --- """


def lambda_handler(event, context):
    """
    Route the incoming request based on intent.
    The JSON body of the request is provided in the event slot.
    """
    # By default, treat the user request as coming from the Pacific timezone.
    os.environ['TZ'] = 'America/Los_Angeles'
    time.tzset()
    logger.info(f'Received event: {event} from {event["bot"]["name"]}')

    return dispatch(event)
