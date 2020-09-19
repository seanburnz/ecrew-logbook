"""
Function that takes an eCrew Pilot logbook report as an input and returns
a tuple containing a dictionary of flights and a dictionary of sims
"""

import datetime

def process_ecrew_logbook_report(inFileName):

    #constants

    page_start_key = '<a'
    logbook_end_key = 'Totals'
    num_page_header_divs = 37
    num_flights_per_page = 38
    num_info_per_flight = 18 #update Sep 2019
    info_div_key = 'font-family' #divs with useful data in them, not just style boxes

    #open input files
    print 'Opening: ' + inFileName
    logbookFile = open(inFileName)

    #
    flight_list = []
    sim_list = []

    #cycle through pages of entries
    while True :
        
        # read through the header lines until the start of logbook entries
        while True :
            line = logbookFile.readline()
            if page_start_key.lower() in line.lower():
                break

        #read through page header
        div_count = 0
        while div_count < num_page_header_divs:
            line = logbookFile.readline()
            if '<div' in line.lower():
                div_count += 1

        # cycle through flights in grouping
        flight_count = 0
        while flight_count < num_flights_per_page:
            entry_number = 0
            flight = []
            while entry_number < num_info_per_flight :
                #read in an entire <div></div> and extract useful text
                while '</div>' not in line:
                    line += logbookFile.readline() #append lines until <div..>..</div> complete
                if logbook_end_key.lower() in line.lower():
                    break
                if info_div_key in line:
                    start = line.index('>') + 1
                    end = line.lower().index('</div>')
                    text_data = line[start:end]
                    text_data = text_data.replace("&nbsp;"," ")
                    text_data = text_data.strip()
                    flight.append(text_data)
                    entry_number += 1
                line = logbookFile.readline()

            if logbook_end_key.lower() in line.lower():
                    break
            flight_list.append(flight)
            flight_count += 1
        if logbook_end_key.lower() in line.lower():
                    break
     
    logbookFile.close()

    #process flight_list into dictionaries of flights and sims
    flight_dict=[]
    sim_dict=[]
    for entry in flight_list:
        if entry[6]!='':
            #entry is a flight; index 0:dep_date, 1:dep_place, 2:dep_time, 3:arr_place, 4:arr_time, 6:registration, 8:name_pic
            flightdate = ecrewdate_to_date(entry[0])
            dep_time = datetime.datetime.combine(ecrewtime_to_time(entry[2],flightdate)[1],ecrewtime_to_time(entry[2],flightdate)[0])
            arr_time = datetime.datetime.combine(ecrewtime_to_time(entry[4],flightdate)[1],ecrewtime_to_time(entry[4],flightdate)[0])
            arr_time = add_arrival_days(dep_time, arr_time)
            instr = 0
            if entry[13] <> "": instr = 1 #Instructor time

            flight={ 'dep_time':dep_time,
                     'dep_place':entry[1],
                     'arr_time':arr_time,
                     'arr_place':entry[3],
                     'reg':entry[6],
                     'name_pic':entry[8].title(),
                     'instr':instr}
            flight_dict.append(flight)
        else:
            #entry is a sim
            simdate = ecrewdate_to_date(entry[0])
            dep_time = datetime.datetime.combine(ecrewtime_to_time(entry[2],simdate)[1],ecrewtime_to_time(entry[2],simdate)[0])
            arr_time = datetime.datetime.combine(ecrewtime_to_time(entry[4],simdate)[1],ecrewtime_to_time(entry[4],simdate)[0])
            arr_time = add_arrival_days(dep_time, arr_time)
            sim={  'sim_place':entry[1],
                   'dep_time':dep_time,
                   'arr_time':arr_time,
                   'training_type':entry[15]}
            sim_dict.append(sim)
                
    logbookFile.close()
    print "Finished"                   
    return (flight_dict,sim_dict)

"""
Helper functions to convert eCrew dates and times to datetime objects
"""

def ecrewdate_to_date(ecrewdate):
    strday = ecrewdate[:2]
    strmonth = ecrewdate[3:5]
    stryear = '20'+ ecrewdate[6:]
    
    newdate = datetime.date(int(stryear),int(strmonth),int(strday))
    
    return newdate

def ecrewtime_to_time(ecrewtime, ecrewdate):
    newtime_hour = int(ecrewtime[:ecrewtime.index(':')])

    #account for ecrew hour times > 24 when flight departs on day after scheduled
    newdate = ecrewdate + datetime.timedelta(newtime_hour / 24)
    newtime_hour = newtime_hour % 24
    
    newtime_min = int(ecrewtime[ecrewtime.index(':')+1:])

    newtime = datetime.time(newtime_hour,newtime_min)
    
    return (newtime, newdate)

def add_arrival_days(dep_time, arr_time):
    while arr_time < dep_time:
        try:
            arr_time = arr_time.replace(day=arr_time.day + 1)

        except ValueError:
            # flight spans a month changeover
            arr_time = arr_time.replace(day=1)
            arr_time = arr_time.replace(month=arr_time.month + 1)

    return arr_time