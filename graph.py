#!/usr/bin/env python3
from pylab import *
from matplotlib.dates import  DateFormatter, WeekdayLocator, HourLocator, DayLocator, MONDAY
import numpy as np
import os, sys, argparse
from pprint import pprint

from collections import namedtuple, OrderedDict
from datetime import datetime, timedelta

from download import Downloader, convert_to_python, str_to_date

# week start time
# Sun Mar  4 00:00:00 1973
ORIGIN_WEEK = 100008000

# weekly interval in seconds (60 * 60 * 24 * 7)
LEN_WEEK = 604800

ISO_WEEKDAYS = {0: 'none',
                1: 'monday',
                2: 'tuesday',
                3: 'wednesday',
                4: 'thursday',
                5: 'friday',
                6: 'saturday',
                7: 'sunday'}
REORDER_ISO = [7, 1, 2, 3, 4, 5, 6]

def tail(f, n):
    stdin, stdout = os.popen2("tail -{} {}".format(n, f))
    stdin.close()
    lines = stdout.readlines();
    stdout.close()
    return lines


def average(arr, absolute=False):
    """
    :param absolute: (list) make negative values positive
    """
    cur_avg = float()
    if not absolute:
        for i, amount in enumerate(arr):
            cur_avg = cur_avg + (amount - cur_avg) / (i + 1)
    elif absolute:
        for i, amount in enumerate(arr):
            cur_avg = cur_avg + (abs(amount) - cur_avg) / (i + 1)
    return cur_avg


def count_weeks(t):
    num_weeks = math.floor((t - ORIGIN_WEEK) / LEN_WEEK)
    week_secs = (t - ORIGIN_WEEK) % LEN_WEEK
    return num_weeks, week_secs


def sort_by_list(dict_, list_):
    for key in list_:
        dict_.move_to_end(key)


def main(args={}):

    D = Downloader()
    D.read_from_file()
    D.order()

    fig = plt.figure()
    ax = fig.add_subplot(111, axisbg='#222222')

    # CSV in integer time stamp, price traded, amount traded
    candles=[]

    # [ MTS, OPEN, CLOSE, HIGH, LOW, VOLUME ]
    Candle = namedtuple('Candle', ['date', 'open', 'close', 'high', 'low', 'volume'])

    # Slice for quicker test iteration
    # 96 candles = 1 day
    # 672 candles = 1 week
    #for timestamp, entry in D.slice(20000).items():
    for timestamp, entry in D.slice(start=args.get('start'),
                                    end=args.get('end')).items():
        last_entry = None
        try:
            candles.append(Candle(datetime.fromtimestamp(convert_to_python(timestamp)),
                                *[fld for fld in entry[:5]]
                                ))
            last_entry = entry
        except Exception:
            print(entry)
            print(last_entry)
            import pdb;pdb.set_trace()

    print("Working with slice of {} candles.".format(len(candles)))

    # ----------------------------------------------------------------------------------------------------------------
    # ----------------------------------------------------------------------------------------------------------------

    if 'volume' in args.get('what'):
        # Let's find the average volume across the week

        volumes_by_weekday = {key: list() for key in ISO_WEEKDAYS}
        sum_by_weekday = {key: 0.0 for key in ISO_WEEKDAYS}

        # NOT USED
        volumes_by_week = OrderedDict()
        sum_by_week_sec = OrderedDict()

        weeks = 0
        for candle in candles:
            volumes_by_weekday[candle.date.isoweekday()].append(candle.volume)
            sum_by_weekday[candle.date.isoweekday()] += candle.volume

            num_weeks, week_secs = count_weeks(candle.date.timestamp())
            if not num_weeks in volumes_by_week:
                weeks += 1
                volumes_by_week[num_weeks] = {}

            if not week_secs in sum_by_week_sec:
                sum_by_week_sec[week_secs] = 0.0

            # NOT USED
            volumes_by_week[num_weeks][week_secs] = candle.volume
            sum_by_week_sec[week_secs] += candle.volume

        # digest (average together all weeks together)
        average_by_day = OrderedDict()
        for day in volumes_by_weekday:
            average_by_day[day] = average(volumes_by_weekday[day])

        # sort first
        sort_by_list(sum_by_week_sec, sorted(list(sum_by_week_sec.keys())))

        average_by_week_sec = OrderedDict()
        for week_secs in sum_by_week_sec:
            average_by_week_sec[week_secs] = float(sum_by_week_sec[week_secs]) / weeks

        # order
        print('Len of average_by_week_sec: {}'.format(len(average_by_week_sec)))
        normalized_week_seconds = [(x / LEN_WEEK * 7.0) for x in list(average_by_week_sec.keys())]

        hex_colour = '%0.2X' % (min(180, 255))

        # averaged weekly values
        ax.plot(normalized_week_seconds,
                list(average_by_week_sec.values()),
                '#{}{}{}'.format(hex_colour, hex_colour, hex_colour))

        # sum by week day of volume, daily summary
        ax.plot([i + 0.5 for i, x in enumerate(REORDER_ISO)],
                [average_by_day[d] for d in REORDER_ISO],
                '#FF8866')

        max_value = max(list(average_by_week_sec.values()))
        min_value = min(list(average_by_week_sec.values()))

    # ----------------------------------------------------------------------------------------------------------------
    # ----------------------------------------------------------------------------------------------------------------

    elif 'move' in args.get('what') or 'range' in args.get('what'):
        # Let's find the average open-close diff across the week

        wick = False
        if 'range' in args.get('what'):
            wick = True

        diff_by_weekday = {key: list() for key in ISO_WEEKDAYS}
        sum_by_weekday = {key: 0.0 for key in ISO_WEEKDAYS}

        diff_by_sec = OrderedDict()
        sum_by_sec = OrderedDict()

        # -------------------------------------------------------
        # Iterate through candles
        weeks = 0
        for candle in candles:
            # movement factor
            movement = (candle.close - candle.open) / candle.open
            if wick:
                if candle.close < candle.open:
                    movement = (candle.low - candle.high) / candle.open
                else:
                    movement = (candle.high - candle.low) / candle.open

            # doesn't matter if list of movements is unordered, this gets averaged
            diff_by_weekday[candle.date.isoweekday()].append(movement)

            # NOT USED
            sum_by_weekday[candle.date.isoweekday()] += movement

            num_weeks, week_secs = count_weeks(candle.date.timestamp())
            if not num_weeks in diff_by_sec:
                weeks += 1
                diff_by_sec[num_weeks] = {}

            if not week_secs in sum_by_sec:
                sum_by_sec[week_secs] = 0.0

            sum_by_sec[week_secs] += movement
            diff_by_sec[num_weeks][week_secs] = movement

        # digest (average together all weeks together)
        average_by_day = OrderedDict()
        for day in diff_by_weekday:
            # TIMES TWENTY FOR VISIBILITY
            average_by_day[day] = average(diff_by_weekday[day]) * 200

        # sort first
        sort_by_list(sum_by_sec, sorted(list(sum_by_sec.keys())))
        sort_by_list(diff_by_sec, sorted(list(diff_by_sec.keys())))

        # -------------------------------------------------------
        # Iterate through candles ONCE for ALL average
        average_by_week_sec = OrderedDict()
        prev_value = 0.0
        for week_secs in sum_by_sec:
            # get averaged value
            averaged_move = float(sum_by_sec[week_secs]) / weeks
            # offset by previous amount
            averaged_move += prev_value
            prev_value = averaged_move

            average_by_week_sec[week_secs] = averaged_move

        # -------------------------------------------------------
        # ECHO

        i = 0
        sum_inc = OrderedDict()
        for week_num, array in diff_by_sec.items():
            i += 1
            chartable = OrderedDict()
            prev_value = 0.0

            for week_secs in sorted(list(array.keys())):
                # get averaged value
                averaged_move = float(array[week_secs]) / i
                # offset by previous amount

                if not week_secs in sum_inc:
                    sum_inc[week_secs] = 0.0
                sum_inc[week_secs] += averaged_move

                chartable[week_secs] = averaged_move + prev_value
                prev_value = chartable[week_secs]

            # order
            print('Len of average_by_week_sec: {}'.format(len(chartable)))
            sort_by_list(chartable, sorted(list(chartable.keys())))
            normalized_week_seconds = [(x / LEN_WEEK * 7.0) for x in list(chartable.keys())]

            c = 35 + int((100 / len(diff_by_sec) * i))
            hex_colour = '%0.2X' % c

            # averaged weekly values
            ax.plot(normalized_week_seconds,
                    list(chartable.values()),
                    '#{}{}{}'.format(hex_colour, hex_colour, hex_colour))

        # order
        print('Len of average_by_week_sec: {}'.format(len(average_by_week_sec)))
        normalized_week_seconds = [(x / LEN_WEEK * 7.0) for x in list(average_by_week_sec.keys())]

        # averaged weekly values
        ax.plot(normalized_week_seconds,
                list(average_by_week_sec.values()),
                '#FFAA00',)#'#{}{}{}'.format(hex_colour, hex_colour, hex_colour))

        # sum by week day of volume, daily summary
        ax.plot([i + 0.5 for i, x in enumerate(REORDER_ISO)],
                [average_by_day[d] for d in REORDER_ISO],
                '#99EEFF')

        max_value = max(list(average_by_week_sec.values()))
        min_value = min(list(average_by_week_sec.values()))

    # day dividers
    for x in range(8):
        ax.plot([x, x],
                [min_value, max_value],
                '#3366BB')
    # day dividers
        ax.plot([0, 8],
                [0, 0],
                '#3366BB')

    xlabel = "Days of week from Sunday Morning 0 AM"
    if args.get('start'):
        xlabel += '\nFrom {}'.format(str_to_date(args.get('start')))
    if args.get('end'):
        xlabel += '\nTo {}'.format(str_to_date(args.get('end')))

    ax.set_xlabel(xlabel)
    if args.get('what') == 'volume':
        ax.set_ylabel("Volume")

    plt.show()

    print('done')
    sys.exit(0)


if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Graph weekly averages')
    parser.add_argument('-w', '--what', help='What to graph (move, volume, range)', required=True)
    parser.add_argument('-st', '--start', help='Start time to slice, YYYYMMDD', required=False)
    parser.add_argument('-et', '--end', help='End time to slice, YYYYMMDD', required=False)
    parser.add_argument('-sh', '--shadow', help='Fade previous weeks', required=False)

    args = vars(parser.parse_args())
    # Todo: add time slicing ability

    main(args=args)
