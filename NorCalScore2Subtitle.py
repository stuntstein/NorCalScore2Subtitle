"""
NorcalScore2Subtitle
"""

'''
20171115 Added heat name
20171114 Fix heat with more than 10 drivers.
20171110 Fix problem with Driver names. Fix for final print out. Clean up
20171212 Added Race Title. Moved generated files to output folder. Added race duration to subtitle.
'''

from HTMLParser import HTMLParser, HTMLParseError
from htmlentitydefs import name2codepoint
import re
import urllib
#import numpy as np
import sys
import os
import argparse

class _HTMLToText(HTMLParser):
    def __init__(self):
        HTMLParser.__init__(self)
        self.text = ''
        self._buf = []
        self.hide_output = True

    def handle_starttag(self, tag, attrs):
        if tag == 'pre':
            self.hide_output = False


    def handle_endtag(self, tag):
        if tag == 'pre':
            self.hide_output = True

    def handle_data(self, text):
        if text and not self.hide_output:
            self.text = text


    def get_text(self):
##        return re.sub(r' +', ' ', ''.join(self._buf))
##            print(self._buf)
        return self.text

def html_to_text(html):
    """
    Given a piece of HTML, return the plain text it contains.
    This handles entities and char refs, but not javascript and stylesheets.
    """
    parser = _HTMLToText()
    try:
        parser.feed(html)
        parser.close()
    except HTMLParseError:
        pass
    return parser.get_text()

 ## split into array of lines.
 ## remove empty lines

def stripText(text):
    lines = text.splitlines()
    newlines = []
    for line in lines:
        if line.rstrip():
            newlines.append(line)
    return newlines

# drivers must be 'name', lapCnt, lapTime
def addSub(subTime, drivers, raceTime = None, raceDuration = 0, heatName=None, raceName=None):
    addSub.count += 1
    if raceTime == None:
        endTime = subTime + 90
    else:
        endTime = subTime + 1

    s = format('%d\n%02d:%02d:%02d,%03d --> %02d:%02d:%02d,%03d\n' %
    (addSub.count,
    int(subTime/60/60),int(subTime/60),int(subTime%60),int((subTime*1000)%1000),
    int(endTime/60/60),int(endTime/60),int(endTime%60),int((endTime*1000)%1000)))

    if raceTime == None:
        if raceName != None:
            s += format('%s\n' % raceName)
        if heatName != None:
            s += format('%s\n' % heatName)
        s += format('%s' % ('Race Over'))
    else:
        if raceTime < 0:
            if raceName != None:
                s += format('%s\n' % raceName)
            if heatName != None:
                s += format('%s\n' % heatName)
            s += format('-%02d:%02d / %02d:%02d' % (int(abs(raceTime)/60),int(abs(raceTime)%60),int(raceDuration/60),int(raceDuration%60)))
        else:
            s += format('%02d:%02d / %02d:%02d' % (int(raceTime/60),int(raceTime%60),int(raceDuration/60),int(raceDuration%60)))

    idx = 0
    for driver in drivers:
        ## if raceTime is running but drivers lap == 0 filter him out
        if driver['name'] != '':        # only if list is not cleared
            if idx % 2 == 0:
                s += format('\n')
            idx += 1
            if driver['lapCnt'] == 0:   # show qual order if no lap count
                s += format('[%s] %-15s\t' %
                    (idx, driver['name']))
            else:
                s += format('[%s] %2d/%5.8s %-15s\t' %
                    (idx, driver['lapCnt'],
                    driver['lapTime'], driver['name']))

    s += format('\n\n')
    return s


def parseScore(text):
    heats = []

    # parse score data in done in 3 steps:
    # 1. get finishing order, sort it to get qualifing order
    # 2. run through lap data for each driver
    # 3. generate one sorted list by raceTime. Transverse though and generate subtitle

    iterText = iter(text)
    for line in iterText:
        if 'Scoring Software by' in line:
            line = iterText.next()  # Advance one line
            raceTitle = line.lstrip().rstrip()
        if 'Round' in line and 'Race' in line:
            # Get Heat name
            heatName = " ".join(line.translate(None,'#*,').split())
            if verbose:
                print '\tParse Heat %s' % heatName
            # Get Drivers
            line = iterText.next()  # Advance one line
            if all(x in line for x in ['Driver','Car','Laps']):  # Alright, we found the start of a heat
                qual_order = []
                main_result = []
                while True:
                    line = iterText.next() #n += 1
                    if '___1___' in line:    ## No more drivers
                        break
                    # clean up Name. Sometimes an '*' is added
                    line = line.replace(' *', '*')
                    last_name = line.split(',',1)
                    if len(last_name) < 2:
                        # sometimes last and first name is not separated by comma
                        last_name = line.lstrip().split(' ',1)

                    first_name = last_name[1].split('#',1)
                    line = first_name[1].split()
                    last_name = last_name[0].strip()
                    first_name = first_name[0].strip()
                    car = int(line[0])
                    totalLaps = int(line[1])
                    ## convert time to sec
                    if verbose:
                        print '\t\t car[%d] %s %s' % (car,first_name,last_name)

                    main_result.append({'name':first_name+' '+last_name, 'car':car, 'totalLaps': totalLaps, 'finishTime':line[2]})

            qual_order = sorted(main_result, key=lambda x:x['car']) ## Sort by car number = qualification order
            ## check that no cars are missing, fx car #1
            carCheck = 1
            for driver in qual_order:
                if driver['car'] != carCheck:    ## driver/car is missing. Add dummy
                    qual_order.insert(carCheck-1,{'name':'', 'car':carCheck, 'totalLaps': 0, 'finishTime':'0'})
                carCheck += 1

            driversLaps = dict()

            # Get lapData
            # problem: more than 10 driver are divided over multiple lines!
            tensOfDrivers = 1
            while tensOfDrivers < len(qual_order):  ## use qual_order to get the dummy entries
                startLine = '___%s' % str(tensOfDrivers)
                while len(startLine) < 7:
                    startLine += '_'

                while not startLine in line:   # next line till we find startLine
                    line = iterText.next()


                while True:     # parse each line for lap data
                    line = iterText.next()  # get laptime
                    if '-------' in line:   # if end of lap chunk break and look for next chunk
                        tensOfDrivers += 10
                        break

                    iterText.next()         # skip estimated result
                    strList = line[1:].rstrip().split(' ')

                    e = 0       # count 8 empty elements
                    drvIdx = 0 + (tensOfDrivers-1)

                    for idx in strList:
                        if '' == idx:       ## find empty entries in the lap results
                            e += 1
                            if e == 8:      ## Each column is 8 char wide
                                drvIdx += 1
                                e = 0
                        else:
                            driver = qual_order[drvIdx]['name']
                            lapData = idx.split('/')    # data from lap result
                            lapTime = float(lapData[1])
                            position = int(lapData[0])
                            if driversLaps.has_key(driver) == 0 : # first entry
                                driversLaps[driver] = [{'pos' : position, 'lap' : 1, 'lapTime' : lapTime, 'raceTime' : lapTime}]
                            else:
                                raceTime = lapTime + driversLaps[driver][len(driversLaps[driver])-1]['raceTime'] ## Calc new raceTime
                                lapCnt = driversLaps[driver][len(driversLaps[driver])-1]['lap'] + 1 # increment lap
                                driversLaps[driver].append({'pos':position,'lapTime':lapTime, 'raceTime':raceTime, 'lap':lapCnt})
                            drvIdx += 1
                            e = 0

            # find the race duration.
            # Look for max value of the finishTime.
            # Convert Time to seconds.
            # Truncate to lowest 60 sec.
            max = 0
            for n in main_result:
                if n['finishTime'] > max:
                    max = n['finishTime']
            raceDuration = map(int,re.split(r'[:.]',max))   # convert to min, second, 1/1000
            raceDuration = raceDuration[0]*60
            heats.append({'heatName': heatName, 'qual_order':qual_order, 'finish_order':main_result, 'raceData':driversLaps, 'raceDuration':raceDuration})
            ##break   ## set to limit to one heat

    print('Number of Heats: %d' % len(heats))

    ## transverse though list of Heats
    for heat in heats:
        print('Heat: %s' % heat['heatName'])
        print('  Number of drivers: %d' % len(heat['qual_order']))
        for driver in heat['qual_order']:
            print('    %d: %s' % (driver['car'], driver['name']))

        ## generate one sorted list by raceTime
        oneList = []
        for driver,lapData in heat['raceData'].items():
            for lap in lapData:
                oneList.append({'lapData':lap, 'driver': driver})
        oneList = sorted(oneList, key=lambda x:x['lapData']['raceTime'])

        ## generate subtitle
        fo = open(heat['heatName'] + '.srt','w')
        addSub.count = 0
        time = 0.

        ## Init drivers for subtitle text
        drivers = []
        for n in heat['qual_order']:
            drivers.append({'name':n['name'],'lapCnt':0,'lapTime':0})

        n = 0
        while True:
            if n >= len(oneList):
                break

            raceTime = time - heatTimeOffsets[heat['heatName']]['offset']

            while n < len(oneList) and oneList[n]['lapData']['raceTime'] < raceTime:
                # clear sub order when first driver passed the line
                if n == 0:
                    for d in drivers:   # clear list
                        d['name'] = ''
                        d['lapCnt'] = 0
                        d['lapTime'] = 0

                ## Swap 2 driver positions
                nextEntry = oneList[n]
                pos = nextEntry['lapData']['pos'] - 1   # Next entry. Get his position
                if pos >= len(drivers):         # Sometimes I see a position higher that the number of drivers!
                    pos -= 1                    # If only 1 too high trim it down.
                else:
                    if pos > len(drivers):      # Stop if pos is too high. Something is bad
                        print 'ERROR',pos,nextEntry
                        exit(1)
                tmp = drivers[pos]                    # Find the driver on that position
                if tmp['name'] != nextEntry['driver']:    # Check that it is not the same driver
                # swap position. Tmp goes to nextEntry's old position
                    nextEntrysOldPos = next((index for (index, d) in enumerate(drivers) if d['name'] == nextEntry['driver']),pos)
                    drivers[pos], drivers[nextEntrysOldPos] = drivers[nextEntrysOldPos], drivers[pos]
                drivers[pos]['name'] = nextEntry['driver']                # update entry
                drivers[pos]['lapCnt'] = nextEntry['lapData']['lap']      # update entry
                drivers[pos]['lapTime'] = nextEntry['lapData']['lapTime'] # update entry
                n += 1

                ## Check if driver is on last lap then update with finish_order data
                for finalDriver in heat['finish_order']:
                    if finalDriver['name'] == drivers[pos]['name']:
                        if finalDriver['totalLaps'] == drivers[pos]['lapCnt']:
                            drivers[pos]['lapTime'] = finalDriver['finishTime']

            s = addSub(time, drivers, raceTime, raceDuration=heat['raceDuration'], heatName=heat['heatName'],raceName=raceTitle)
            fo.write(s)
            time += 1

        ## break ## enable for debugging one heat

        ## we have no more in the sorted list
        s = addSub(time, drivers, heatName=heat['heatName'],raceName=raceTitle)
#        s = addSub(time, heat['finish_order'])
        fo.write(s)
        fo.close()

    return
## end parseScore(text)
def createFolder(text):
    ## find date and create folder
    for line in text:
        if 'Scoring Software' in line:
            path = line[line.find('M  '):]
            path = path[3:].split('/')
            path = 'output/' + path[2]+path[0]+path[1]
            if not os.path.exists(path):
                os.makedirs(path)
            os.chdir(path)
            print('Store files in % s.' % path)
            # To save to file for offline testing
            fo = open('score_from_web.txt','w')
            for n in text:
                fo.write(n+'\n')
            fo.close()
            break

def checkResult(text):
    timeOffsets = {}
    for line in text:
        if all(x in line for x in ['Round','Race']):
            # Get Heat name
            heatName = " ".join(line.translate(None,'#*,').split())
            timeOffsets[heatName] = {'offset':5}
    print('Found %d heats.' % len(timeOffsets))
    if args.debug == False:
        print('Please type the time ofset from when the race starts.')
        for heat in timeOffsets.iterkeys():
            offset = input('Time offset for %s :' % heat)
            timeOffsets[heat]['offset'] = offset
    return timeOffsets


### Main
if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='Fetch Race results from http://www.norcalhobbies.com/category/race-results/ and convert to a subtitle file to be loaded in youtube.')
    parser.add_argument('--url','-u', dest='url', metavar='<URL>',required=True,
                    help='Url to the page with the race result')

    parser.add_argument('--proxy','-p', dest='proxy')
    parser.add_argument('--verbose','-v', action='store_true')
    parser.add_argument('--debug','-d', action='store_true')

    args = parser.parse_args()
    url = args.url
    proxies = {}

    if args.url != '':
        # For fetching from internet
        if args.proxy != None:
            proxies['http'] = args.proxy
        htmltext = urllib.urlopen(url, proxies=proxies).read()
        text = html_to_text(htmltext)
        text = stripText(text)
        fo = open('html.txt','w')
        fo.write(htmltext)
        fo.close()

    else:
        ## For offline testing
        file = open('score_from_web.txt')    # instead of reading from web
        text = file.read()
        file.close
        text = stripText(text)

    print('Get data from %s ' % url)
    verbose = args.verbose
    createFolder(text)
    heatTimeOffsets = checkResult(text)
    parseScore(text)
    print "Done. Files generate in %s " % os.getcwd()
