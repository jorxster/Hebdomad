#!/usr/bin/env python
from pylab import *
from matplotlib.dates import  DateFormatter, WeekdayLocator, HourLocator, DayLocator, MONDAY
import numpy as np
import os, sys, argparse
from pprint import pprint

from collections import namedtuple, OrderedDict
from datetime import datetime, timedelta

from download import Downloader, convert_to_python

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

#sort_by_list(ordereddict, key_list)

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
    for timestamp, entry in D.slice(100000).items():
        last_entry = None
        try:
            candles.append(Candle(datetime.fromtimestamp(convert_to_python(timestamp)),
                                *[fld for fld in entry[:5]]
                                ))
            last_entry = entry
        except:
            print(entry)
            print(last_entry)
            import pdb;pdb.set_trace()


    print(len(candles))

    # Pseudocode.
    # Average intra-daily movements to get average per day movement?
    # Then plot on a weekly graph (for every week, or all combined)

    if 'volume' in args.get('what'):
        # Let's find the average volume across the week

        volumes_by_weekday = {key: list() for key in ISO_WEEKDAYS}
        sum_by_weekday = {key: 0.0 for key in ISO_WEEKDAYS}

        volumes_by_week = OrderedDict()
        sum_by_week_sec = OrderedDict()
        average_by_week_sec = OrderedDict()

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

            volumes_by_week[num_weeks][week_secs] = candle.volume
            sum_by_week_sec[week_secs] += candle.volume


        average_by_day = OrderedDict()
        for day in volumes_by_weekday:
            average_by_day[day] = average(volumes_by_weekday[day])

        # sort first
        sort_by_list(sum_by_week_sec, sorted(list(sum_by_week_sec.keys())))
        for week_secs in sum_by_week_sec:
            average_by_week_sec[week_secs] = float(sum_by_week_sec[week_secs]) / weeks
        # order
        # ordered_keys = sorted(list(average_by_week_sec.keys()))
        # sort_by_list(average_by_week_sec, ordered_keys)

        print('length of average_by_week_sec: {}'.format(len(average_by_week_sec)))

        normalized_week_seconds = [(x / LEN_WEEK * 7.0) for x in list(average_by_week_sec.keys())]

        hex_colour = '%0.2X' % (min(180, 255))

        # averaged weekly values
        ax.plot(normalized_week_seconds,
                list(average_by_week_sec.values()),
                '#{}{}{}'.format(hex_colour, hex_colour, hex_colour))

        # # summed weeks values together
        # ax.plot(normalized_week_seconds,
        #         list(sum_by_week_sec.values()),
        #         '#{}{}{}'.format(hex_colour, hex_colour, hex_colour))

        # sum by week day of volume
        #import pdb;pdb.set_trace()
        ax.plot([i + 0.5 for i, x in enumerate(REORDER_ISO)],
                [average_by_day[d] for d in REORDER_ISO],
                '#FF8866')

        for x in range(8):
            ax.plot([x, x],
                    [0, 700],
                    '#AAEEFF')

        ax.set_xlabel("Days of week from Sunday Morning 0AM")
        if args.get('what') == 'volume':
            ax.set_ylabel("Volume")

        plt.show()

        print('done')
        sys.exit(0)




    else:

        prev_date = None
        # all the completed orders buy and sell averaged together
        daily_averaged = {}

        # multiplier based on previous day, * 100 = percentage
        daily_change = {}

        daily_values = []
        one_day = timedelta(days=1)

        for i, quote in enumerate(quotes):
            d = quote.date
            var = quote.price

            # for very first iteration only
            if prev_date is None:
                prev_date = d.date()

            if d.date() != prev_date:

                daily_averaged[prev_date] = average(daily_values)
                print('Averaged price of {} is {}'.format(
                      (prev_date, daily_averaged[prev_date])))

                # calculate change
                second_prev_day = prev_date - one_day
                if second_prev_day in daily_averaged:

                    prev_average = daily_averaged[second_prev_day]
                    move = daily_averaged[prev_date] - prev_average
                    if move and prev_average:
                        daily_change[prev_date] = move / prev_average
                    else:
                        daily_change[prev_date] = 0.0
                    print('\tmovement : {.3f} %%'.format(daily_change[prev_date] * 100))

                prev_date = d.date()
                daily_values = []

            else:
                daily_values.append(var)

        daily_averaged[d.date()] = average(daily_values)
        print('Averaged price of {} is {}'.format(
              (d.date(), daily_averaged[d.date()]))
            )

        prev_date = d.date() - one_day
        if prev_date in daily_averaged:
            prev_average = daily_averaged[prev_date]
            move = daily_averaged[d.date()] - prev_average
            if move and prev_average:
                daily_change[d.date()] = move / prev_average
            else:
                daily_change[d.date()] = 0.0



        days = daily_averaged.keys()
        days.sort()
        #days.reverse()
        print(days[0:15])

        week = []
        movements_by_weekday = dict((x, []) for x in range(1, 8))

        colour = 50
        for day in days:
            if not day in daily_change:
                print('SKIPPING {}' % day)
                continue

            print(day.isoweekday())
            if day.isoweekday() == 7:
                print('WEEK : {}' % week)
                colour += 4
                hex_colour = '%0.2X' % (min(colour, 255))
                ax.plot(range(len(week)), week, '#' + '{}{}{}' % (hex_colour, hex_colour, hex_colour))

                week = [daily_change[day]]

            movements_by_weekday[day.isoweekday()].append(daily_change[day])
            week = [daily_change[day]] + week

        weekday_averaged = {}
        weekday_volatility = {}
        for day_index in movements_by_weekday:
            weekday_averaged[day_index] = average(movements_by_weekday[day_index])
            weekday_volatility[day_index] = average(movements_by_weekday[day_index], abso=True)

        ax.plot(range(len(movements_by_weekday)), weekday_volatility.values(), '#FF7744')
        ax.plot(range(len(movements_by_weekday)), weekday_averaged.values(), '#4477FF')

        plt.show()


if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Graph weekly averages')
    parser.add_argument('-w', '--what', help='What to graph', required=False)
    args = vars(parser.parse_args())
    # Todo: add time slicing ability

    main(args=args)
