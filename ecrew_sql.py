"""
Function that takes an eCrew Pilot logbook report as an input and returns
an sql file for importing into a logbook database
Input file should be an ecrew logbook report that has been opened in a new window then saved as .htm
"""

import ecrew_pilot_log, sunrisesunset
import mysql.connector, ecrew_sql_settings

#logbook format for datetime objects
dform = '%Y-%m-%d %H:%M'

print "Processing ecrew logbook report"

file_name = raw_input("Enter the input file name (e.g flights.htm): ")
result = ecrew_pilot_log.process_ecrew_logbook_report(file_name)

flight_dict = result[0]
sim_dict = result[1]

print str(len(flight_dict)) + " flights were successfully read"

print "Opening database connection"
cnx = mysql.connector.connect(user=ecrew_sql_settings.DB_USER,
                              password=ecrew_sql_settings.DB_PWD,
                              host=ecrew_sql_settings.DB_HOST,
                              port=ecrew_sql_settings.DB_PORT,
                              database=ecrew_sql_settings.DB_DB)
cursor = cnx.cursor(raw=True)

#Check that airports have already been entered into database
missing_airports = set()

for flight in flight_dict:
    query = ("SELECT ICAO_code FROM logbook_airports WHERE IATA_code = %s")
    data = (flight['dep_place'],)
#    print query, data
    cursor.execute(query, data)
    dep_info = cursor.fetchone()
#    print dep_info
    if not dep_info:
        missing_airports.add(flight['dep_place'])
        continue

for flight in flight_dict:
    query = ("SELECT ICAO_code FROM logbook_airports WHERE IATA_code = %s")
    data = (flight['arr_place'],)
    cursor.execute(query, data)
    dep_info = cursor.fetchone()
    if not dep_info:
        missing_airports.add(flight['arr_place'])
        continue

if len(missing_airports) > 0:
    print "Following airports missing from database: (" + ", ".join(missing_airports) + ")"

#Check that aircraft have already been entered into database
missing_aircraft = set()

for flight in flight_dict:
    query = ("SELECT ID FROM logbook_aircraft WHERE Registration = %s")
    flight['reg'] = flight['reg'].translate(None,'-') #Strip - from registration
    data = (flight['reg'],)
    cursor.execute(query,data)
    ac_info = cursor.fetchone()
    if not ac_info :
        missing_aircraft.add(flight['reg'])
        continue

if len(missing_aircraft) > 0:
    print "Following aircraft missing from database: (" + ", ".join(missing_aircraft) + ")"


if len(missing_aircraft) > 0 or len(missing_airports) > 0: exit()

#Database is good to go!

# self_pic = raw_input("Were you PIC for the flights? (Y/n)")
#
# if self_pic == 'n' or self_pic == 'N':
#     self_pic = False
# else:
#     self_pic = True

auto_pf = False
## Might need modifying
# PIC = ""
# P1 = 0
# ##

# num_missing = 0
copilot_name = ""
for flight in flight_dict :
    query = ("SELECT ICAO_code, Latitude, Longitude FROM logbook_airports WHERE IATA_code = %s")
    
    #get departure airport information
    data = (flight['dep_place'],)
    cursor.execute(query,data)
    dep_info = cursor.fetchone() #tuple of (ICAO, lat, lon)
    
    #get arrival airport information
    data = (flight['arr_place'],)
    cursor.execute(query,data)
    arr_info = cursor.fetchone() #tuple of (ICAO, lat, lon)
    
    #include night_time field  
    night_time = sunrisesunset.nightCalc(flight['dep_time'],float(dep_info[1]),float(dep_info[2]),
                                          flight['arr_time'],float(arr_info[1]),float(arr_info[2]),
                                         'civil')
    
    flight['night_time'] = night_time[1]
    flight['total_time'] = flight['arr_time']-flight['dep_time']

    #include ICAO code
    flight['dep_ICAO'] = str(dep_info[0])
    flight['arr_ICAO'] = str(arr_info[0])

    #look up aircraft number
    query = ("SELECT ID FROM logbook_aircraft WHERE Registration = %s")
    data = (flight['reg'],)
    cursor.execute(query,data)
    ac_info = cursor.fetchone()
    flight["aircraft"] = int(ac_info[0])

    #random PF - this method is broken now than name_pic is always Self
    # if auto_pf :
    #     if flight['name_pic'] != PIC :
    #         #new series of flights
    #         P1 = random.choice((1,1,1,0,0)) #60% chance I fly first
    #         PIC = flight['name_pic']
    #     else :
    #         #flying with the same Capt so alternate PF/PM duties
    #         P1 = abs(P1-1) #switch between 1 and 0
    #
    # else:
    prompt = flight['dep_ICAO'] + " " + flight['arr_ICAO'] + " " + flight['dep_time'].strftime(dform) + " " + flight['arr_time'].strftime(dform) + " " + flight['name_pic'] + " - PF? y(es)/n(o)> "
    PF = ""
    while (PF <> "y" and PF <> "n"): PF = raw_input(prompt)
        # if PF == 'a':
        #     P1 = abs(P1-1) #PF for this sector is opposite of last
        #     PIC = flight['name_pic']
        #     auto_pf = True #switch to automatic PF assignment
        # else:
    if PF == 'y':
        P1 = 1
    else:
        P1 = 0

    #Check for a new copilot name or use last entered
    if flight["name_pic"] == "Self":
        prompt = "Copilot Name: (" + copilot_name + ") "
        new_copilot_name = raw_input(prompt)
        if new_copilot_name <> "": copilot_name = new_copilot_name
    else :
        copilot_name = 'Self'

    #Check for comments
    # prompt = "Comments: (-) "
    # comments = raw_input(prompt)
    # if comments == '': comments = '-'
    flight['comments'] = '-' #comments

    flight['name_copilot'] = copilot_name
    flight['PF'] = P1
    flight['ldg_day'] = 0
    flight['ldg_ngt'] = 0
    if P1:
        if night_time[2] : #night arrival
            flight['ldg_ngt'] = 1
        else:
            flight['ldg_day'] = 1

prompt = "Would you like to automatically insert " + str(len(flight_dict)) + " new records? (y/N)"
response = raw_input(prompt)
insert_records = (response == 'y' or response == 'Y')


output_file_name = "new_flights.sql"
output_file = open(output_file_name, mode='w')

new_records = 0
failures = 0
# columns = ("Dep_Place", "Arr_Place", "Dep_Time", "Arr_Time", "Aircraft", "PF", "Name_PIC", "Name_Copilot", "Night_Time", "IFR_Time", "Copilot_Time", "Function", "Ldg_Day", "Ldg_Night", "Comments")
#
# #change for self_pic
# if self_pic:
#     columns = ("Dep_Place", "Arr_Place", "Dep_Time", "Arr_Time", "Aircraft", "PF", "Name_PIC", "Name_Copilot", "Night_Time", "Can_P1_XC_Night", "IFR_Time", "PIC_Time", "Can_P1", "Can_P1_XC", "Function", "Ldg_Day", "Ldg_Night", "Comments")


for flight in flight_dict:

    #Create database sql insert statement
    if flight["name_pic"] == "Self":
        columns = (
        "Dep_Place", "Arr_Place", "Dep_Time", "Arr_Time", "Aircraft", "PF", "Name_PIC", "Name_Copilot", "Night_Time",
        "Can_P1_XC_Night", "IFR_Time", "PIC_Time", "Can_P1", "Can_P1_XC", "Function", "Ldg_Day", "Ldg_Night",
        "Comments")

        values = (
        flight['dep_ICAO'], flight['arr_ICAO'], flight['dep_time'].strftime(dform), flight['arr_time'].strftime(dform),
        flight['aircraft'], flight['PF'], flight['name_pic'], flight['name_copilot'], str(flight['night_time']),
        str(flight['night_time']), str(flight['total_time']), str(flight['total_time']), str(flight['total_time']),
        str(flight['total_time']), "P1", flight['ldg_day'], flight['ldg_ngt'], flight['comments'])

        if flight['instr']: #Instructor time
            columns += ("Instr_Time",)
            values += (str(flight['total_time']),)

    else:
        columns = (
        "Dep_Place", "Arr_Place", "Dep_Time", "Arr_Time", "Aircraft", "PF", "Name_PIC", "Name_Copilot", "Night_Time",
        "IFR_Time", "Copilot_Time", "Function", "Ldg_Day", "Ldg_Night", "Comments")

        values = (
        flight['dep_ICAO'], flight['arr_ICAO'], flight['dep_time'].strftime(dform), flight['arr_time'].strftime(dform),
        flight['aircraft'], flight['PF'], flight['name_pic'], flight['name_copilot'], str(flight['night_time']),
        str(flight['total_time']), str(flight['total_time']), "FO", flight['ldg_day'], flight['ldg_ngt'],
        flight['comments'])

    qry_txt = "INSERT INTO logbook_flights ("
    for col in columns:
        qry_txt += '`' + col + '`, '
    qry_txt = qry_txt[:-2]

    qry_txt += ") VALUES "
    # values = (flight['dep_ICAO'], flight['arr_ICAO'], flight['dep_time'].strftime(dform), flight['arr_time'].strftime(dform), flight['aircraft'], flight['PF'], flight['name_pic'], flight['name_copilot'], str(flight['night_time']), str(flight['total_time']), str(flight['total_time']), "FO", flight['ldg_day'], flight['ldg_ngt'], flight['comments'])
    #
    # #change for PIC
    # if self_pic:
    #         values = (flight['dep_ICAO'], flight['arr_ICAO'], flight['dep_time'].strftime(dform), flight['arr_time'].strftime(dform), flight['aircraft'], flight['PF'], flight['name_pic'], flight['name_copilot'], str(flight['night_time']), str(flight['night_time']), str(flight['total_time']), str(flight['total_time']), str(flight['total_time']), str(flight['total_time']), "P1", flight['ldg_day'], flight['ldg_ngt'], flight['comments'])


    qry_txt += str(values)

    query = (qry_txt)

    if insert_records:
        try:
            cursor.execute(query)
            cnx.commit()
            new_records += 1
        except:
            failures += 1

    output_file.write(qry_txt + ";\n")

if insert_records:
    print "Successfully inserted " + str(new_records) + " records with " + str(failures) + " failures"

output_file.close()
print "SQL file successfully saved as " + output_file_name

print "Closing database connection"
cnx.close()