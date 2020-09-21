
from __future__ import absolute_import
from __future__ import print_function
import datetime, mysql.connector, ecrew_sql_settings, night_calc

print("Opening database connection")
cnx = mysql.connector.connect(user=ecrew_sql_settings.DB_USER,
                              password=ecrew_sql_settings.DB_PWD,
                              host=ecrew_sql_settings.DB_HOST,
                              port=ecrew_sql_settings.DB_PORT,
                              database=ecrew_sql_settings.DB_DB)
cursor = cnx.cursor(buffered=True)

#Turbine flights where no night hours entered
query = "SELECT F.ID, F.Dep_Time, D.Latitude, D.Longitude, F.Arr_Time, A.Latitude, A.Longitude, F.Night_Time, LT.Type, LT.Turbine \
FROM logbook_flights F, logbook_aircraft LA, logbook_aircraft_type LT,  \
(SELECT ICAO_Code, Latitude, Longitude FROM logbook_airports) D, \
(SELECT ICAO_Code, Latitude, Longitude FROM logbook_airports) A \
WHERE D.ICAO_Code = F.Dep_Place AND A.ICAO_Code = F.Arr_Place AND LA.ID = F.Aircraft AND LT.ID = LA.Type \
AND LT.Turbine = 1"# AND Night_Time = 0"

cursor.execute(query)

# cursor2 = cnx.cursor(raw=False)
updates = 0

for flight in cursor:
    nightHours = night_calc.nightCalc(flight[1],flight[2],flight[3],flight[4],flight[5],flight[6],'civil')
    if nightHours[1] > datetime.timedelta(minutes=2): #3 minutes minimum
        # query2 = "UPDATE logbook_flights SET Night_Time = %s WHERE ID = %s"
        # data2 = (nightHours[1],flight[0])
        updates += 1
        # cursor2.execute(query2,data2)
        print(flight[0], night_calc.td_hhmm(flight[7]), night_calc.td_hhmm(nightHours[1]), night_calc.td_hhmm(abs(nightHours[1]-flight[7])), flight[8], flight[9])
# cnx.commit()
print(str(updates) + " flights updated")
print("Closing database connection")
cnx.close()