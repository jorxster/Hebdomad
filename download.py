
#/usr/bin/python3
"""
Candle :

Fields 	Type 	Description
MTS 	int 	millisecond time stamp
OPEN 	float 	First execution during the time frame
CLOSE 	float 	Last execution during the time frame
HIGH 	float 	Highest execution during the time frame
LOW 	float 	Lowest execution during the timeframe
VOLUME 	float 	Quantity of symbol traded within the timeframe
"""
import inspect
import os
import pickle
import pprint
import requests
import time
import traceback

from collections import OrderedDict

# minutes in milliseconds
FIFTEEN_MIN = 900000

# when querying candles, maximum number allowed
MAX_ALLOWED_CANDLES = 120

DAT_FILE = os.path.dirname(__file__) + '_bitfinex_15m.dat'

class Downloader(object):

    def __init__(self, path=None):
        print('{}::{}'.format('>'*len(inspect.stack()), inspect.stack()[0][3]))
        # todo: numpy array?
        self.data = {}
        self.is_ordered = None

        if path:
            self.path = path
        else:
            self.path = DAT_FILE

    def query_time(self, start=1490472900000, end=1490465700000, scale='15m'):
        """
        Available values: '1m', '5m', '15m', '30m', '1h', '3h', '6h', '12h', '1D', '7D', '14D', '1M'
        """
        print('{}::{}'.format('>'*len(inspect.stack()), inspect.stack()[0][3]))
        attrs = {'SCALE': scale,
                 'START': start,
                 'END': end}
        query_url = 'https://api.bitfinex.com/v2/candles/trade:{SCALE}:tBTCUSD/hist?start={START}&end={END}'.format(**attrs)
        print(query_url)
        r = requests.get(query_url)
        try:
            print('Length of candles list returned from Bitfinex:{}'.format(len(r.json())))

            for candle in r.json():
                if not isinstance(candle[0], int):
                    print('!!! UNEXPECTED RESULT FROM BITFINEX :')
                    print('\tRAW:{}'.format(r.json()))
                    return

                self.data.update({candle[0]: candle[1:]})

        except Exception:
            raise RuntimeError('Unexpected Result : \n\t{}'.format(r.json()))


    def write_to_file(self, path=None):
        print('{}::{}'.format('>'*len(inspect.stack()), inspect.stack()[0][3]))
        if path:
            self.path = path
        pickle.dump(self.data, open(self.path, 'wb'))

    def update(self):
        print('{}::{}'.format('>'*len(inspect.stack()), inspect.stack()[0][3]))
        if not self.data:
            raise EnvironmentError('Not loaded! Read from file first')

        if not self.is_ordered:
            self.order()

        latest_time = list(self.data.keys())[-1]
        current_time = get_current_time()

        fetch_start = latest_time

        i = 0
        while True:

            fetch_end = latest_time + ((FIFTEEN_MIN * MAX_ALLOWED_CANDLES) * i)
            if fetch_end > current_time:
                fetch_end = current_time

            # try 10 times in event of error
            for j in range(100):
                error_count = 0
                try:
                    print('Running update() on time {} \n\t\t to {}'.format(fetch_start, fetch_end))
                    self.query_time(end=fetch_end,
                                    start=fetch_start)
                    time.sleep(1.5)
                    break

                except Exception:
                    error_count += 1
                    time.sleep(1.5)
                    if error_count > 90:
                        raise
                    else:
                        print('Ignoring error >>>>>>>>>>>>>>>')
                        print(traceback.format_exc())

                if i % 3 == 0:
                    self.write_to_file()

            if fetch_end == current_time:
                break

            fetch_start = fetch_end
            i += 1

        self.write_to_file()

    def read_from_file(self, path=None):
        print('{}::{}'.format('>'*len(inspect.stack()), inspect.stack()[0][3]))
        if path:
            self.path = path

        self.data = pickle.load(open(self.path, 'rb'))

    def nice_start(self):
        print('{}::{}'.format('>'*len(inspect.stack()), inspect.stack()[0][3]))
        return time.ctime(
            convert_to_python(
                list(self.data.keys())[0]
            )
        )

    def nice_end(self):
        print('{}::{}'.format('>'*len(inspect.stack()), inspect.stack()[0][3]))
        return time.ctime(
            convert_to_python(
                list(self.data.keys())[-1]
            )
        )

    def order(self):
        print('{}::{}'.format('>'*len(inspect.stack()), inspect.stack()[0][3]))

        # first attempt to fix if any keys (times) are not int (like, ('e', 'rror'))
        prev_time = list(self.data.keys())[0]

        for k in list(self.data.keys()):
            if not isinstance(k, int):
                print('WARNING, we have an unexpected result here!!!, after the last good time '
                      '{}'.format(time.ctime(convert_to_python(prev_time))))
                print(k.__class__)
                print('ATTEMPTING to fix...')
                print('POPPING: {}'.format(self.data.pop(k)))

                try:
                    self.query_time(start=prev_time,
                                    end=prev_time + ((FIFTEEN_MIN * 2)))
                except:
                    print('Potential supressed error here!!!')
                    pass
            prev_time = k

        sorted_list = sorted(self.data.items(), key=lambda x: x[0])
        self.data = OrderedDict(sorted_list)
        self.is_ordered = True

    def print_summary(self):
        print('{}::{}'.format('>'*len(inspect.stack()), inspect.stack()[0][3]))
        # print first 4 four
        print('\nprint_summary()')
        print(self.nice_start())
        pprint.pprint(list(self.data.keys())[0:4])
        print('...........')

        # print last four
        pprint.pprint(list(self.data.keys())[-4:])
        print(self.nice_end())
        print(len(self.data.keys()))
        print('')

    def print_ending(self, i):

        print('\nprint_ending({})'.format(i))
        keys = list(self.data.keys())[-i:]
        for k in keys:
            print(k)
            print(time.ctime(convert_to_python(k)))
            pprint.pprint(self.data[k])

    def slice(self, x):
        print('{}::{}'.format('>'*len(inspect.stack()), inspect.stack()[0][3]))
        keys = self.data.keys()
        length = len(keys)

        i = 0
        sliced = OrderedDict()
        for k in keys:
            i += 1
            if i > (length - x):
                sliced[k] = self.data[k]

        return sliced

def convert_to_python(time):
    #print('{}::{}'.format('>'*len(inspect.stack()), inspect.stack()[0][3]))
    return time / 1000


def convert_to_milliseconds(time):
    print('{}::{}'.format('>'*len(inspect.stack()), inspect.stack()[0][3]))
    return time * 1000


def get_current_time():
    """
    Returns current time in bitfinex format
    """
    print('{}::{}'.format('>'*len(inspect.stack()), inspect.stack()[0][3]))
    return convert_to_milliseconds(
        int(time.time())
    )


def download(iterations):
    print('{}::{}'.format('>'*len(inspect.stack()), inspect.stack()[0][3]))
    return True
    D = Downloader()
    for i in range(3000):

        # try 10 times in event of error
        for j in range(100):
            error_count = 0
            try:
                D.query_time(
                    end=get_current_time() - (FIFTEEN_MIN * MAX_ALLOWED_CANDLES * i),
                    start=get_current_time() - (FIFTEEN_MIN * MAX_ALLOWED_CANDLES * (i+1))
                )
                time.sleep(1.5)
                break
            except Exception:
                error_count +=1
                time.sleep(1.5)
                if error_count > 90:
                    raise
                else:
                    print('Ignoring error >>>>>>>>>>>>>>>')
                    print(traceback.format_exc())

            if i % 5 == 0:
                D.write_to_file()

    D.write_to_file()

    return D

def read():
    print('{}::{}'.format('>'*len(inspect.stack()), inspect.stack()[0][3]))
    D = Downloader()
    D.read_from_file()
    D.order()
    D.update()
    D.print_summary()
    return D

if __name__ == '__main__':
    try:
        read()
    except:
        print(traceback.format_exc())
