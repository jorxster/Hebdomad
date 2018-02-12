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


def tail(f, n):
    stdin, stdout = os.popen2("tail -{} {}".format(n, f))
    stdin.close()
    lines = stdout.readlines();
    stdout.close()
    return lines


def average(arr, absolute=False):
    """
    :param absolute: make negative values positive
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
    week_pos = (t - ORIGIN_WEEK) % LEN_WEEK
    return num_weeks, week_pos


def main(args={}):

    D = Downloader()
    D.read_from_file()
    D.order()

    iso_weekdays = {0:'none',
                    1:'monday',
                    2:'tuesday',
                    3:'wednesday',
                    4:'thursday',
                    5:'friday',
                    6:'saturday',
                    7:'sunday'}

    fig = plt.figure()
    ax = fig.add_subplot(111, axisbg='#222222')

    # CSV in integer time stamp, price traded, amount traded
    candles=[]

    # [ MTS, OPEN, CLOSE, HIGH, LOW, VOLUME ]
    Candle = namedtuple('Candle', ['date', 'open', 'close', 'high', 'low', 'volume'])

    i = 0
    # Slice for quicker test iteration
    for timestamp, entry in D.slice(3000).items():
        candles.append(Candle(datetime.fromtimestamp(convert_to_python(timestamp)),
                            *[fld for fld in entry]
                            ))
    print(len(candles))

    # Pseudocode.
    # Average intra-daily movements to get average per day movement?
    # Then plot on a weekly graph (for every week, or all combined)

    if args.get('what') == 'volume':
        # Let's find the average volume across the week
        volumes_by_weekday = {key: list() for key in iso_weekdays}
        sum_by_weekday = {key: 0.0 for key in iso_weekdays}
        for candle in candles:
            volumes_by_weekday[candle.date.isoweekday()].append(candle.volume)
            sum_by_weekday[candle.date.isoweekday()] += candle.volume

        average_by_day = OrderedDict()
        for day in volumes_by_weekday:
            average_by_day[iso_weekdays[day]] = average(volumes_by_weekday[day])

        pprint(average_by_day)


        print(iso_weekdays.values())
        #import pdb;pdb.set_trace()
        #for day in iso_weekdays:

        hex_colour = '%0.2X' % (min(180, 255))
        ax.plot(range(len( list(iso_weekdays.values())[1:] )),
                list(sum_by_weekday.values())[1:],
                '#' + '{}{}{}'.format(hex_colour, hex_colour, hex_colour))
        ax.set_xlabel("Days of week from Sunday")
        if args.get('what') == 'volume':
            ax.set_ylabel("Volume")

        plt.show()

        print('done')
        sys.exit(0)







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

    #import pdb;pdb.set_trace()
    ax.plot(range(len(movements_by_weekday)), weekday_volatility.values(), '#FF7744')
    ax.plot(range(len(movements_by_weekday)), weekday_averaged.values(), '#4477FF')

    plt.show()

    #array=np.rec.array( quotes )



    # format the ticks
    #ax.xaxis.set_major_locator(years)
    #ax.xaxis.set_major_formatter(dayFormatter)
    #ax.xaxis.set_minor_locator(months)

    '''
    ax.plot(range(5), values[:5], '#FFFFFF')
    ax.plot(range(5), vol_values[:5], '#FF7744')
    '''
    #ax.plot([4,3,2,1], [4,3,4,5], '#CCBBAA')












    '''fig = figure()
    fig.subplots_adjust(bottom=0.2)
    ax = fig.add_subplot(111)
    ax.xaxis.set_major_locator(mondays)
    ax.xaxis.set_minor_locator(alldays)
    ax.xaxis.set_major_formatter(weekFormatter)
    #ax.xaxis.set_minor_formatter(dayFormatter)
    
    #plot_day_summary(ax, quotes, ticksize=3)
    candlestick(ax, quotes, width=0.6)
    
    ax.xaxis_date()
    ax.autoscale_view()
    setp( gca().get_xticklabels(), rotation=45, horizontalalignment='right')
    
    show()
    '''

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Graph weekly averages')
    parser.add_argument('-w', '--what', help='What to graph', required=False)
    args = vars(parser.parse_args())
    # Todo: add time slicing ability

    main(args=args)
